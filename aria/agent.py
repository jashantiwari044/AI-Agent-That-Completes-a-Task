"""
Core ReAct (Reasoning + Acting) Agent Loop for ARIA.
Executes multi-step tasks autonomously with tools, state tracking, and stop conditions.
"""

import json
import re
import time
from typing import Any, Dict, List, Optional, Tuple
from aria.llm import LLMClient
from aria.tools.base import BaseTool
from aria.logger import AgentLogger
from aria.prompts import REACT_SYSTEM_PROMPT, SYNTHESIS_SYSTEM_PROMPT
from aria.config import MAX_CONSECUTIVE_ERRORS


class AgentResponse:
    """Parsed output of an LLM turn."""

    def __init__(
        self,
        thought: str,
        action: Optional[str] = None,
        action_input: Optional[Dict[str, Any]] = None,
        final_answer: Optional[str] = None,
        raw_text: str = "",
    ):
        self.thought = thought
        self.action = action
        self.action_input = action_input or {}
        self.final_answer = final_answer
        self.raw_text = raw_text

    @property
    def is_final(self) -> bool:
        return bool(self.final_answer)


class ReActAgent:
    """
    Autonomous AI agent running a transparent ReAct reasoning loop.
    Decides -> Acts -> Observes -> Repeats until task completion or stop condition.
    """

    def __init__(
        self,
        llm: LLMClient,
        tools: Dict[str, BaseTool],
        logger: AgentLogger,
        max_steps: int = 15,
    ):
        self.llm = llm
        self.tools = tools
        self.logger = logger
        self.max_steps = max_steps
        self.messages: List[Dict[str, str]] = []
        self.consecutive_errors = 0

    def _build_system_prompt(self) -> str:
        """Construct system prompt with live tool descriptions."""
        descriptions = "\n".join(tool.to_schema_doc() for tool in self.tools.values())
        return REACT_SYSTEM_PROMPT.format(tool_descriptions=descriptions)

    def _parse_llm_output(self, text: str) -> AgentResponse:
        """
        Robust parser for agent reasoning output.
        Extracts Thought, Action, Action Input, or Final Answer.
        Supports standard ReAct syntax and JSON-embedded formats.
        """
        raw = text.strip()

        # Check for Final Answer
        final_match = re.search(r"Final Answer:\s*(.*)", raw, re.DOTALL | re.IGNORECASE)
        if final_match:
            thought_part = raw[:final_match.start()].strip()
            thought_match = re.search(r"Thought:\s*(.*?)(?=(?:Action:|Final Answer:|$))", thought_part, re.DOTALL | re.IGNORECASE)
            thought = thought_match.group(1).strip() if thought_match else "Concluding task."
            return AgentResponse(
                thought=thought,
                final_answer=final_match.group(1).strip(),
                raw_text=raw,
            )

        # Check for JSON-native output format (e.g., {"thought": ..., "action": ..., "action_input": ...})
        if raw.startswith("{") and raw.endswith("}"):
            try:
                data = json.loads(raw)
                if "final_answer" in data:
                    return AgentResponse(
                        thought=data.get("thought", "Concluded."),
                        final_answer=data["final_answer"],
                        raw_text=raw,
                    )
                if "action" in data:
                    return AgentResponse(
                        thought=data.get("thought", "Taking action."),
                        action=data["action"],
                        action_input=data.get("action_input", {}),
                        raw_text=raw,
                    )
            except Exception:
                pass

        # Parse standard ReAct tags: Thought, Action, Action Input
        thought_match = re.search(r"Thought:\s*(.*?)(?=(?:Action:|Final Answer:|$))", raw, re.DOTALL | re.IGNORECASE)
        thought = thought_match.group(1).strip() if thought_match else "Analyzing next step."

        action_match = re.search(r"Action:\s*([a-zA-Z0-9_\-]+)", raw, re.IGNORECASE)
        action = action_match.group(1).strip().lower() if action_match else None

        action_input = {}
        # Match Action Input non-greedily up to next Thought, Action, Final Answer, Observation, or end of string
        input_match = re.search(
            r"Action Input:\s*(.*?)(?=(?:\n\s*(?:Thought|Action|Final Answer|Observation):)|$)",
            raw,
            re.DOTALL | re.IGNORECASE,
        )
        if input_match:
            input_str = input_match.group(1).strip()
            
            # Clean possible markdown code fences ```json ... ```
            if "```" in input_str:
                code_match = re.search(r"```(?:json)?\s*(.*?)\s*```", input_str, re.DOTALL)
                if code_match:
                    input_str = code_match.group(1).strip()

            # Attempt JSON parse
            try:
                action_input = json.loads(input_str)
            except Exception:
                # Try finding outermost JSON object { ... }
                bracket_match = re.search(r"(\{.*\})", input_str, re.DOTALL)
                if bracket_match:
                    try:
                        action_input = json.loads(bracket_match.group(1))
                    except Exception:
                        action_input = {"query": input_str} if action == "web_search" else {"value": input_str}
                else:
                    action_input = {"query": input_str} if action == "web_search" else {"value": input_str}

        return AgentResponse(
            thought=thought,
            action=action,
            action_input=action_input,
            raw_text=raw,
        )

    def run(self, task: str) -> str:
        """
        Execute the complete autonomous agent reasoning loop.
        Returns the final synthesized answer or report.
        """
        self.logger.log_start()

        # Initialize conversation messages
        system_prompt = self._build_system_prompt()
        self.messages = [
            {"role": "system", "content": system_prompt},
            {
                "role": "user",
                "content": f"Please research and complete this task methodically:\nTask: {task}",
            },
        ]

        step = 1
        final_result = ""

        try:
            while step <= self.max_steps:
                step_start = time.time()

                # 1. THINK & DECIDE — LLM generates next action or final answer
                try:
                    response_text = self.llm.generate(self.messages, temperature=0.2)
                except Exception as e:
                    self.logger.log_error(f"LLM generation failed: {e}")
                    self.consecutive_errors += 1
                    if self.consecutive_errors >= MAX_CONSECUTIVE_ERRORS:
                        final_result = f"Terminated early due to repeated LLM generation errors: {e}"
                        self.logger.log_final(final_result, status="Failed (LLM Error)")
                        return final_result
                    time.sleep(1.0)
                    step += 1
                    continue

                parsed = self._parse_llm_output(response_text)

                # 2. CHECK STOP CONDITION A: Final Answer produced
                if parsed.is_final:
                    # Guardrail: If agent attempts Final Answer on step 1 without calling any tools, reject it
                    has_called_tools = any(s.action and s.action != "none" for s in self.logger.steps)
                    if step == 1 and not has_called_tools:
                        observation = (
                            "Observation: Premature Final Answer rejected. You have not executed any tools yet! "
                            "You must first use a tool (such as 'web_search', 'read_file', or 'notepad') to "
                            "gather real-world data or perform the action before completing the task."
                        )
                        duration = time.time() - step_start
                        self.logger.log_step(
                            step_number=step,
                            thought=parsed.thought + " (Attempted premature completion without tools)",
                            action="rejected_premature_exit",
                            action_input={},
                            observation=observation,
                            duration=duration,
                        )
                        self.messages.append({"role": "assistant", "content": response_text})
                        self.messages.append({"role": "user", "content": observation})
                        step += 1
                        continue

                    duration = time.time() - step_start
                    self.logger.log_step(
                        step_number=step,
                        thought=parsed.thought,
                        action=None,
                        action_input=None,
                        observation="Task marked complete by agent.",
                        duration=duration,
                        is_final=True,
                    )
                    final_result = parsed.final_answer or "Task completed."
                    self.logger.log_final(final_result, status="Completed Successfully")
                    return final_result

                # Check if no valid action was identified
                if not parsed.action:
                    # Provide feedback to the agent to stick to the protocol
                    observation = (
                        "Invalid response format: No valid 'Action:' or 'Final Answer:' found. "
                        "Please respond strictly with Thought, Action, and Action Input, or Final Answer."
                    )
                    duration = time.time() - step_start
                    self.logger.log_step(
                        step_number=step,
                        thought=parsed.thought,
                        action="none",
                        action_input={},
                        observation=observation,
                        duration=duration,
                    )
                    self.messages.append({"role": "assistant", "content": response_text})
                    self.messages.append({"role": "user", "content": f"Observation: {observation}"})
                    self.consecutive_errors += 1
                    step += 1
                    continue

                # 3. ACT — Execute the selected tool
                action_name = parsed.action
                action_input = parsed.action_input

                if action_name not in self.tools:
                    available = ", ".join(self.tools.keys())
                    observation = f"Error: Tool '{action_name}' is not recognized. Available tools: {available}."
                    self.consecutive_errors += 1
                else:
                    try:
                        tool = self.tools[action_name]
                        observation = tool.execute(**action_input)
                        self.consecutive_errors = 0  # reset on successful tool call
                    except Exception as e:
                        observation = f"Error executing tool '{action_name}': {str(e)}"
                        self.consecutive_errors += 1

                duration = time.time() - step_start

                # 4. OBSERVE — Record step in logger & feed observation back to LLM context
                self.logger.log_step(
                    step_number=step,
                    thought=parsed.thought,
                    action=action_name,
                    action_input=action_input,
                    observation=observation,
                    duration=duration,
                )

                # Append to conversation history for next reasoning iteration
                self.messages.append({"role": "assistant", "content": response_text})
                self.messages.append({"role": "user", "content": f"Observation: {observation}"})

                # Check consecutive error limit
                if self.consecutive_errors >= MAX_CONSECUTIVE_ERRORS:
                    final_result = (
                        f"Aborted: Agent encountered {MAX_CONSECUTIVE_ERRORS} consecutive tool errors."
                    )
                    self.logger.log_final(final_result, status="Failed (Consecutive Errors)")
                    return final_result

                step += 1

            # 5. CHECK STOP CONDITION B: Max Steps reached
            self.logger.log_error(f"Reached maximum limit of {self.max_steps} steps.")
            # Request final synthesis with available observations
            synthesis_prompt = (
                f"You have reached the maximum allowed step limit ({self.max_steps}). "
                "Synthesize everything you have discovered so far into your final response."
            )
            self.messages.append({"role": "user", "content": synthesis_prompt})
            try:
                final_synth = self.llm.generate(self.messages, temperature=0.3)
                final_result = final_synth
                
                # Check if final synthesis emitted an Action (e.g. write_file)
                parsed_final = self._parse_llm_output(final_synth)
                if parsed_final.action and parsed_final.action in self.tools:
                    self.tools[parsed_final.action].execute(**parsed_final.action_input)
                    if parsed_final.action_input.get("content"):
                        final_result = parsed_final.action_input["content"]
                elif "write_file" in self.tools:
                    # Auto-save report if task requested writing to a specific file
                    file_match = re.search(r"(?:to|in|file)\s+([a-zA-Z0-9_\-\.]+\.(?:md|txt|json))", task, re.IGNORECASE)
                    if file_match:
                        target_file = file_match.group(1).strip()
                        self.tools["write_file"].execute(file_path=target_file, content=final_synth)
            except Exception:
                final_result = "Reached max steps limit. Intermediate notes and trace saved."

            self.logger.log_final(final_result, status="Completed (Max Steps Reached)")
            return final_result

        except KeyboardInterrupt:
            final_result = "Agent execution interrupted by user (Ctrl+C). Current progress saved."
            self.logger.log_final(final_result, status="Interrupted")
            return final_result
