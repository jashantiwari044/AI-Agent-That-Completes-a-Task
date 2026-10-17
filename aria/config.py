"""
Configuration settings for ARIA (Autonomous Research & Intelligence Agent).
Loads settings from environment variables and provides sensible defaults.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

# Output and Log Directories
OUTPUT_DIR = BASE_DIR / "output"
LOGS_DIR = BASE_DIR / "logs"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
LOGS_DIR.mkdir(parents=True, exist_ok=True)

# Provider & API Configuration
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "groq").lower().strip()

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "").strip()
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile").strip()

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1").strip()
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama2-uncensored:7b").strip()

# Execution Limits
try:
    MAX_STEPS = int(os.getenv("MAX_STEPS", "15"))
except ValueError:
    MAX_STEPS = 15

try:
    TIMEOUT_SECONDS = int(os.getenv("TIMEOUT_SECONDS", "60"))
except ValueError:
    TIMEOUT_SECONDS = 60

# Max consecutive tool errors before pausing / failing gracefully
MAX_CONSECUTIVE_ERRORS = 3
