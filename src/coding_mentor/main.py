"""Command-line interface (CLI) and interactive REPL for AI Coding Mentor.

Provides an accessible, student-friendly terminal interface with progressive
mode switching, context management, and safe interactive approval prompts.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
from typing import Optional

from coding_mentor import __version__
from coding_mentor.assistant import CodingMentorAssistant
from coding_mentor.config import ConfigurationError, MentorConfig
from coding_mentor.logging_config import setup_logging
from coding_mentor.permissions import ActionType
from coding_mentor.providers.mock_provider import MockProvider

# Simple ANSI color codes for beginner-friendly terminal presentation
RESET = "\033[0m"
BOLD = "\033[1m"
GREEN = "\033[32m"
BLUE = "\033[34m"
CYAN = "\033[36m"
YELLOW = "\033[33m"
RED = "\033[31m"
MAGENTA = "\033[35m"


def cli_approval_callback(action: ActionType, description: str) -> bool:
    """Prompt the user in the terminal for explicit permission before dangerous actions."""
    print(f"\n{YELLOW}{BOLD}⚠️  [Security Confirmation Required]{RESET}")
    print(f"Action: {action.value}")
    print(f"Details: {description}")
    try:
        reply = input(f"{BOLD}Allow this operation? (y/N): {RESET}").strip().lower()
        return reply in ("y", "yes")
    except (KeyboardInterrupt, EOFError):
        return False


def print_banner() -> None:
    """Display welcome banner."""
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except Exception:
            pass
    print(f"{CYAN}{BOLD}")
    print("==================================================================")
    print("           AI CODING MENTOR - Python Agentic Assistant            ")
    print(f"                       Version {__version__}                      ")
    print("==================================================================")
    print(f"{RESET}")
    print("Welcome! I am your personal programming mentor, here to help you")
    print("learn concepts, structure projects, and debug independently.\n")
    print("Type your questions directly, or enter commands:")
    print(f"  {BOLD}hint{RESET}       - Switch to Hint Mode (clues without giving full answer)")
    print(f"  {BOLD}concept{RESET}    - Switch to Concept Mode (explanations & simple examples)")
    print(f"  {BOLD}pseudocode{RESET} - Switch to Pseudocode Mode (algorithmic steps)")
    print(f"  {BOLD}review{RESET}     - Review your code or a project file")
    print(f"  {BOLD}solution{RESET}   - Switch to Solution Mode (full working code & breakdown)")
    print(f"  {BOLD}debug{RESET}      - Dedicated debugging workflow for errors & tracebacks")
    print(f"  {BOLD}plan{RESET}       - Plan an MVP, folder structure, and milestones")
    print(f"  {BOLD}context{RESET}    - Inspect or set project directory")
    print(f"  {BOLD}tools{RESET}      - Inspect available tools & security boundaries")
    print(f"  {BOLD}clear{RESET}      - Start a fresh conversation session")
    print(f"  {BOLD}help{RESET}       - Show available commands")
    print(f"  {BOLD}quit{RESET}       - Exit the mentor\n")


def read_multiline_input(prompt_text: str) -> str:
    """Read multiple lines from terminal until user enters 'END' or double enter."""
    print(f"{CYAN}{prompt_text}{RESET}")
    print(f"{YELLOW}(Paste your code/traceback. Type 'END' on a new line or press Ctrl+D when done:){RESET}")
    lines: list[str] = []
    while True:
        try:
            line = input()
            if line.strip() == "END":
                break
            lines.append(line)
        except EOFError:
            break
        except KeyboardInterrupt:
            print("\nCancelled.")
            return ""
    return "\n".join(lines).strip()


def run_repl(assistant: CodingMentorAssistant) -> None:
    """Run the interactive Read-Eval-Print Loop."""
    print_banner()

    # Inform user about offline mode or active provider
    if isinstance(assistant.provider, MockProvider):
        print(f"{YELLOW}[Running in Offline / Mock Mode - No API Key needed]{RESET}\n")
    elif not assistant.config.api_key:
        print(f"{RED}[Warning]: No OPENAI_API_KEY detected. Use 'status' for help or run with --offline.{RESET}\n")

    while True:
        try:
            mode_badge = f"{MAGENTA}[Mode: {assistant.mode.upper()}]{RESET}"
            prompt = f"{BOLD}mentor{RESET} {mode_badge} > "
            user_input = input(prompt).strip()

            if not user_input:
                continue

            cmd_lower = user_input.lower()

            if cmd_lower in ("quit", "exit", ":q"):
                print(f"\n{GREEN}Goodbye! Happy coding and keep building!{RESET}")
                break

            if cmd_lower == "help":
                print_banner()
                continue

            if cmd_lower in ("hint", "concept", "pseudocode", "review", "solution"):
                assistant.set_mode(cmd_lower)
                print(f"{GREEN}Switched to {cmd_lower.upper()} mode.{RESET}")
                continue

            if cmd_lower.startswith("mode"):
                parts = user_input.split(maxsplit=1)
                if len(parts) > 1:
                    target_mode = parts[1].strip().lower()
                    if target_mode in ("hint", "concept", "pseudocode", "review", "solution", "debug", "plan"):
                        assistant.set_mode(target_mode)
                        print(f"{GREEN}Mode set to: {target_mode.upper()}{RESET}")
                    else:
                        print(f"{RED}Unknown mode '{target_mode}'. Valid: hint, concept, pseudocode, review, solution, debug, plan.{RESET}")
                else:
                    print(f"Current mode: {BOLD}{assistant.mode}{RESET}")
                continue

            if cmd_lower == "clear":
                assistant.clear_session()
                print(f"{GREEN}✓ Conversation memory cleared. Fresh session started.{RESET}")
                continue

            if cmd_lower == "debug":
                snippet = read_multiline_input("Enter code or error traceback to debug:")
                if snippet:
                    print(f"\n{CYAN}Analyzing error with debugging assistant...{RESET}\n")
                    response = assistant.debug(snippet)
                    print(f"\n{response}\n")
                continue

            if cmd_lower.startswith("review"):
                parts = user_input.split(maxsplit=1)
                file_target = parts[1].strip() if len(parts) > 1 else None
                if file_target:
                    # Review a file directly
                    target_path = Path(file_target)
                    if not target_path.is_absolute() and assistant.permissions.project_root:
                        target_path = assistant.permissions.project_root / target_path
                    if target_path.is_file():
                        code_content = target_path.read_text(encoding="utf-8", errors="replace")
                        print(f"\n{CYAN}Reviewing {target_path.name}...{RESET}\n")
                        response = assistant.review(code_content, file_path=target_path.name)
                        print(f"\n{response}\n")
                    else:
                        print(f"{RED}File not found: {file_target}{RESET}")
                else:
                    snippet = read_multiline_input("Enter code to review:")
                    if snippet:
                        print(f"\n{CYAN}Reviewing code...{RESET}\n")
                        response = assistant.review(snippet)
                        print(f"\n{response}\n")
                continue

            if cmd_lower.startswith("plan"):
                parts = user_input.split(maxsplit=1)
                idea = parts[1].strip() if len(parts) > 1 else ""
                if not idea:
                    idea = input(f"{BOLD}Enter project idea or requirements to plan: {RESET}").strip()
                if idea:
                    print(f"\n{CYAN}Generating project architecture & milestone plan...{RESET}\n")
                    response = assistant.plan(idea)
                    print(f"\n{response}\n")
                continue

            if cmd_lower.startswith("context"):
                parts = user_input.split(maxsplit=1)
                if len(parts) > 1:
                    new_path = parts[1].strip()
                    p = Path(new_path).resolve()
                    if p.exists() and p.is_dir():
                        assistant.set_project_path(p)
                        print(f"{GREEN}✓ Attached project workspace: {p}{RESET}")
                    else:
                        print(f"{RED}Invalid path: '{new_path}' is not an existing directory.{RESET}")
                else:
                    print(f"\n{CYAN}--- Active Project Context ---{RESET}")
                    print(assistant.context.get_context_summary())
                    print("------------------------------\n")
                continue

            if cmd_lower == "status":
                print(f"\n{CYAN}--- Mentor Status ---{RESET}")
                summary = assistant.config.masked_summary()
                for k, v in summary.items():
                    print(f"  {k:22s}: {v}")
                print(f"  {'active_mode':22s}: {assistant.mode}")
                print(f"  {'conversation_turns':22s}: {assistant.conversation.turn_count}")
                print("---------------------\n")
                continue

            if cmd_lower == "tools":
                print(f"\n{CYAN}--- Available Controlled Tools ---{RESET}")
                for tool in assistant.tools.list_tools():
                    print(f"  {BOLD}{tool.name}{RESET}: {tool.description}")
                print(f"Auto-approve reads: {assistant.permissions.auto_approve_reads}")
                print(f"Allow code execution: {assistant.permissions.allow_code_execution}")
                print("----------------------------------\n")
                continue

            # Standard conversational question
            print(f"\n{CYAN}Mentor is thinking...{RESET}\n")
            reply = assistant.ask(user_input)
            print(f"{reply}\n")

        except KeyboardInterrupt:
            print(f"\n{YELLOW}(Interrupted. Type 'quit' to exit.){RESET}")
        except EOFError:
            print(f"\n{GREEN}Exiting. Goodbye!{RESET}")
            break
        except Exception as e:
            print(f"{RED}Unexpected error: {e}{RESET}")


def main() -> int:
    """CLI Entry point."""
    parser = argparse.ArgumentParser(
        prog="coding-mentor",
        description="AI Coding Mentor - Personal Agentic Python Assistant for CS students & developers.",
    )
    parser.add_argument("--project", "-p", help="Path to project directory to attach as context.")
    parser.add_argument(
        "--mode",
        "-m",
        choices=["hint", "concept", "pseudocode", "review", "solution", "debug", "plan"],
        help="Initial assistance mode (default: hint).",
    )
    parser.add_argument("--offline", "--mock", action="store_true", help="Run with offline mock LLM provider.")
    parser.add_argument("--model", help="Override LLM model name (e.g. gpt-4o-mini).")
    parser.add_argument("--log-level", default="INFO", help="Logging level (DEBUG, INFO, WARNING, ERROR).")

    args = parser.parse_args()

    setup_logging(args.log_level)

    config = MentorConfig.from_env()

    if args.project:
        config.project_path = Path(args.project).resolve()
    if args.mode:
        config.default_mode = args.mode
    if args.model:
        config.llm_model = args.model
    if args.offline:
        config.llm_provider = "mock"

    provider = MockProvider(model=config.llm_model) if config.llm_provider == "mock" else None

    try:
        assistant = CodingMentorAssistant(
            config=config,
            provider=provider,
            approval_callback=cli_approval_callback,
        )
    except ConfigurationError as e:
        print(f"{RED}{BOLD}Configuration Error:{RESET}\n{e}")
        return 1

    run_repl(assistant)
    return 0


if __name__ == "__main__":
    sys.exit(main())
