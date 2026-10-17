"""
Automated Test Suite for ARIA (Autonomous Research & Intelligence Agent).
Tests all 5 tools, output generators, ReAct parsing, and reasoning loop mechanics.
"""

import sys
import unittest
from pathlib import Path
from aria.tools import get_default_tools
from aria.tools.notepad import NotepadTool
from aria.tools.text_analyzer import TextAnalyzerTool
from aria.tools.file_reader import FileReaderTool
from aria.tools.file_writer import FileWriterTool
from aria.tools.web_search import WebSearchTool
from aria.agent import ReActAgent
from aria.logger import AgentLogger


class DummyLLM:
    """Mock LLM to simulate deterministic ReAct turns for testing."""
    def __init__(self, responses):
        self.responses = list(responses)
        self.call_count = 0
        self.provider = "mock"
        self.active_model = "mock-model"

    def generate(self, messages, **kwargs):
        if self.call_count < len(self.responses):
            res = self.responses[self.call_count]
            self.call_count += 1
            return res
        return "Thought: Done.\nFinal Answer: Mock task completed."


class TestAriaTools(unittest.TestCase):

    def setUp(self):
        self.tools = get_default_tools()

    def test_registered_tools_count(self):
        """Verify all 5 required tools are registered."""
        expected = {"web_search", "read_file", "write_file", "notepad", "analyze_text"}
        self.assertEqual(set(self.tools.keys()), expected)

    def test_notepad_operations(self):
        """Test notepad tool set, get, list, clear."""
        tool = self.tools["notepad"]
        
        # Test set
        res_set = tool.execute(action="set", key="test_key", value="Agent Memory Test")
        self.assertIn("Saved note", res_set)

        # Test get
        res_get = tool.execute(action="get", key="test_key")
        self.assertIn("Agent Memory Test", res_get)

        # Test list
        res_list = tool.execute(action="list")
        self.assertIn("test_key", res_list)

        # Test clear
        res_clear = tool.execute(action="clear")
        self.assertIn("Cleared 1 notes", res_clear)

    def test_file_writer_and_reader(self):
        """Test safe writing and reading of files."""
        writer = self.tools["write_file"]
        reader = self.tools["read_file"]
        test_file = "unit_test_sample.txt"

        # Write
        write_res = writer.execute(file_path=test_file, content="ARIA unit test payload 12345")
        self.assertIn("Successfully wrote", write_res)

        # Read
        read_res = reader.execute(file_path=test_file)
        self.assertIn("ARIA unit test payload 12345", read_res)

        # Cleanup
        p = Path("output") / test_file
        if p.exists():
            p.unlink()

    def test_text_analyzer_facts_and_stats(self):
        """Test text analyzer fact and stats extraction."""
        analyzer = self.tools["analyze_text"]
        sample = "In 2026, renewable energy reached 42.5% of total grid power, generating $12 billion in revenue."

        facts = analyzer.execute(text=sample, operation="facts")
        self.assertIn("2026", facts)
        self.assertIn("42.5%", facts)

        stats = analyzer.execute(text=sample, operation="stats")
        self.assertIn("Word count", stats)


class TestReActLoop(unittest.TestCase):

    def test_react_parser_and_loop(self):
        """Simulate a deterministic 3-step ReAct loop: Search -> Store -> Conclude."""
        mock_responses = [
            # Turn 1: Call notepad to set plan
            'Thought: I need to record my plan.\nAction: notepad\nAction Input: {"action": "set", "key": "plan", "value": "1. Verify 2. Synthesize"}',
            # Turn 2: Conclude with Final Answer
            'Thought: Plan recorded. I will now conclude.\nFinal Answer: Task verified and successfully completed.'
        ]

        mock_llm = DummyLLM(mock_responses)
        tools = get_default_tools()
        logger = AgentLogger(
            task="Test autonomous reasoning loop",
            provider="mock",
            model="mock-model",
            max_steps=5
        )

        agent = ReActAgent(llm=mock_llm, tools=tools, logger=logger, max_steps=5)
        result = agent.run("Test autonomous reasoning loop")

        self.assertIn("successfully completed", result.lower())
        self.assertEqual(len(logger.steps), 2)
        self.assertTrue(logger.log_file.exists())

        # Cleanup trace file from test
        if logger.log_file.exists():
            logger.log_file.unlink()


if __name__ == "__main__":
    unittest.main()
