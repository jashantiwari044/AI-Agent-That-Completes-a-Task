"""
Text analyzer tool for extracting facts, statistics, entities, and summaries.
Runs locally and fast without external API calls.
"""

import re
from typing import List
from aria.tools.base import BaseTool


class TextAnalyzerTool(BaseTool):
    name = "analyze_text"
    description = (
        "Analyze a block of text to extract key insights. Supported operations: "
        "'summary' (extractive core summary), 'facts' (numbers, dates, metrics, entities), "
        "'keywords' (most important technical concepts), 'stats' (word count, sentence count, reading time)."
    )
    parameters = {
        "text": {
            "type": "string",
            "description": "The text content to analyze.",
        },
        "operation": {
            "type": "string",
            "description": "Operation to perform: 'summary', 'facts', 'keywords', or 'stats' (default: 'summary').",
        },
    }

    def execute(self, **kwargs) -> str:
        text = kwargs.get("text", "").strip()
        operation = kwargs.get("operation", "summary").lower().strip()

        if not text:
            return "Error: 'text' parameter is required for analyze_text."

        words = re.findall(r"\b[A-Za-z0-9_\-\.]+\b", text)
        sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", text) if len(s.strip()) > 15]

        if operation == "stats":
            word_count = len(words)
            char_count = len(text)
            sentence_count = max(len(sentences), 1)
            reading_time_min = round(word_count / 200, 1)
            return (
                f"=== Text Statistics ===\n"
                f"- Word count: {word_count}\n"
                f"- Character count: {char_count}\n"
                f"- Sentence count: {sentence_count}\n"
                f"- Estimated reading time: ~{reading_time_min} minute(s)"
            )

        elif operation == "facts":
            # Extract metrics: numbers with %, $, currencies, years, or quantitative units
            facts = []
            
            # Years (e.g. 2024, 2025, 2026)
            years = sorted(set(re.findall(r"\b(20[123][0-9])\b", text)))
            if years:
                facts.append(f"• Years/Dates referenced: {', '.join(years)}")

            # Percentages
            percentages = sorted(set(re.findall(r"\b\d+(?:\.\d+)?%", text)))
            if percentages:
                facts.append(f"• Percentages / Metrics: {', '.join(percentages[:8])}")

            # Currencies / Financials
            money = sorted(set(re.findall(r"[\$€£]\s?\d+(?:\.\d+)?(?:\s?(?:billion|million|trillion|k|m|b))?", text, re.IGNORECASE)))
            if money:
                facts.append(f"• Financial figures: {', '.join(money[:8])}")

            # Sentences containing numbers or key claims
            data_sentences = []
            for s in sentences:
                if any(char.isdigit() for char in s) and ("increased" in s.lower() or "achieved" in s.lower() or "announced" in s.lower() or "qubits" in s.lower() or "speed" in s.lower() or "model" in s.lower()):
                    data_sentences.append(f"• {s[:160]}...")
            
            if data_sentences:
                facts.append("• Key Quantified Statements:\n  " + "\n  ".join(data_sentences[:5]))

            if not facts:
                return "Analysis found general descriptive text without prominent numerical metrics or dates."

            return "=== Extracted Facts & Metrics ===\n" + "\n".join(facts)

        elif operation == "keywords":
            # Exclude common stop words
            stop_words = {
                "the", "and", "a", "an", "in", "to", "of", "for", "with", "is", "are",
                "on", "that", "this", "by", "as", "at", "from", "it", "be", "was",
                "or", "which", "were", "have", "has", "had", "not", "but", "their", "its"
            }
            freq = {}
            for w in words:
                w_lower = w.lower()
                if len(w_lower) > 3 and w_lower not in stop_words and not w_lower.isnumeric():
                    freq[w_lower] = freq.get(w_lower, 0) + 1

            sorted_kw = sorted(freq.items(), key=lambda x: x[1], reverse=True)[:10]
            kw_list = [f"• {k}: {v} mentions" for k, v in sorted_kw]
            return "=== Key Concepts & Frequencies ===\n" + "\n".join(kw_list)

        elif operation == "summary":
            if len(sentences) <= 3:
                return f"=== Summary ===\n{text}"
            
            # Pick first sentence, middle informative sentence, and last sentence
            selected = [sentences[0]]
            if len(sentences) > 4:
                selected.append(sentences[len(sentences) // 2])
            selected.append(sentences[-1])
            summary_text = "\n".join(f"• {s}" for s in selected)
            return f"=== Extractive Summary ({len(sentences)} sentences distilled to key takeaways) ===\n{summary_text}"

        else:
            return f"Error: Unknown operation '{operation}'. Use 'summary', 'facts', 'keywords', or 'stats'."
