"""Settings for ServiceDesk Simulator Automation.
Change speeds, target ticket categories, and execution preferences here.
"""
import time

# Timing delays (seconds)
STEP_DELAY = 3.5      # wait between major steps (login, select, assign, execute)
ACTION_DELAY = 1.5    # wait after each individual click or typing action

# Target ticket category to process:
# Options: "ALL", "ONBOARDING", "OFFBOARDING", "RESET_PASSWORD", "USER_AUTHENTICATION"
TARGET_CATEGORY = "ALL"

# Default temporary password used when creating users or resetting passwords
DEFAULT_TEMP_PASSWORD = "TempPassword2026!"

# Whether to automatically submit resolution notes and resolve the ticket
AUTO_RESOLVE = True

# Whether to continuously loop through all tickets in queue or process one by one
PROCESS_ALL_QUEUE = False

# AI settings (Ollama)
USE_OLLAMA_IF_AVAILABLE = True
OLLAMA_MODEL = "qwen2.5:7b"
OLLAMA_URL = "http://localhost:11434/api/chat"

def pause(seconds=None, why=""):
    seconds = STEP_DELAY if seconds is None else seconds
    if why:
        print(f"...waiting {seconds}s ({why})")
    time.sleep(seconds)
