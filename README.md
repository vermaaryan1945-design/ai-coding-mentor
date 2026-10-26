# AI Coding Mentor — A Personal Agentic Python Assistant

An agentic, beginner-friendly Python programming mentor designed to help computer science students (specifically BTech CSE AI & Data Science) and developers develop independent problem-solving, debugging, and software architecture skills.

Rather than acting as an automated code generator that replaces human thinking, the **AI Coding Mentor** utilizes a **Progressive Assistance System** (Hint → Concept → Pseudocode → Review → Solution) paired with a **strictly controlled, sandboxed tool system** to guide developers toward deep comprehension and self-reliance.

---

## 🌟 Key Features

### 1. Progressive Scaffolding & Pedagogical Modes
The mentor defaults to **Hint Mode** to encourage active reasoning, while allowing instantaneous mode switching at any time:
- 💡 **Hint Mode (`hint`):** Gives a targeted conceptual clue or guiding question without revealing full code.
- 📚 **Concept Mode (`concept`):** Explains theoretical concepts (e.g. hash tables, recursion, Big-O) with a minimal 3-5 line isolated example.
- 📝 **Pseudocode Mode (`pseudocode`):** Breaks the algorithmic logic into structured, numbered, language-agnostic steps.
- 🔍 **Review Mode (`review`):** Audits your code for edge cases, logical pitfalls, modularity, and readability without immediately overwriting it.
- ✨ **Solution Mode (`solution`):** Delivers a production-grade Python 3.11+ solution with line-by-line annotations and trade-off explanations.

### 2. Specialized Workflows
- 🐛 **Debugging Assistant (`debug`):** Accepts code snippets, tracebacks, or error messages. Explains *why* Python threw the error in plain language, identifies the line, and recommends the smallest reasonable fix first.
- 📋 **Project Planning Agent (`plan`):** Formulates realistic Minimum Viable Products (MVPs), folder structures, modular milestones, dependencies, and test strategies for student projects.

### 3. Agentic & Controlled Tool System
Enforces security and permission boundaries strictly in Python code, completely independent of the LLM's prompt:
- **Workspace Containment:** File reads and directory scans are restricted strictly within the canonical project root; directory traversal (`../`) attacks are rejected.
- **Secret Shielding:** Sensitive files (`.env*`, `*.pem`, `*.key`, `id_rsa`, `credentials.json`) are automatically filtered from file scans and blocked from tool reading.
- **AST Symbol Search:** Extracts top-level classes, functions, and docstrings without full-file overhead.
- **Syntax Diagnostics:** AST-based syntax and indentation checking with visual caret pointers (`^`).
- **Reviewable Patch Proposals:** Never silently overwrites files; generates unified diffs (`difflib`) for user inspection.
- **Sandboxed Execution Gates:** Running code (`run_python`) or pytest (`run_tests`) is disabled by default and requires explicit interactive terminal confirmation (`y/N`), with strict execution timeouts and output bounding.

---

## 🏗️ Architecture Overview

The system is organized into modular, testable layers:

```
ai_coding_mentor/
├── src/
│   └── coding_mentor/
│       ├── __init__.py           # Package exports & version
│       ├── main.py               # Interactive CLI REPL & command dispatcher
│       ├── config.py             # Environment configuration & secret masking
│       ├── assistant.py          # Central agent orchestrator & tool execution loop
│       ├── conversation.py       # Turn-bounded message history & mode management
│       ├── project_context.py    # Safe workspace scanner & AST symbol extractor
│       ├── prompts.py            # Progressive pedagogical prompts & instructions
│       ├── permissions.py        # Runtime security gates & path containment
│       ├── logging_config.py     # Redacted structured logging (scrubs API keys)
│       │
│       ├── providers/            # Pluggable LLM provider abstraction
│       │   ├── __init__.py
│       │   ├── base.py           # LLMProvider abstract interface & ChatMessage types
│       │   ├── openai_provider.py# Official OpenAI SDK & standard urllib HTTP fallback
│       │   └── mock_provider.py  # Deterministic offline mock for tests & demonstrations
│       │
│       └── tools/                # Controlled agentic tools
│           ├── __init__.py
│           ├── base.py           # Tool definition, ToolResult, & ToolRegistry
│           ├── file_reader.py    # ReadFileTool & ListFilesTool
│           ├── code_search.py    # SymbolSearchTool (AST) & CodeSearchTool (Regex)
│           ├── syntax_checker.py # SyntaxCheckerTool (AST syntax analysis)
│           ├── python_runner.py  # PythonRunnerTool & TestRunnerTool (subprocesses)
│           └── patch_tool.py     # ProposePatchTool (unified diffs)
│
├── tests/                        # 100% offline unit & integration test suite
│   ├── conftest.py               # Shared pytest fixtures & test workspace
│   ├── test_config.py            # Config validation & secret redaction tests
│   ├── test_permissions.py       # Path containment & security gate tests
│   ├── test_project_context.py   # Workspace scanning & symbol extraction tests
│   ├── test_tools.py             # Tool execution & safety tests
│   ├── test_conversation.py      # Conversation turn window & mode tests
│   └── test_assistant.py         # End-to-end agentic workflow & error handling tests
│
├── .env.example                  # Template configuration (no sensitive data)
├── .gitignore                    # Git rules excluding .venv, caches, and secrets
├── pyproject.toml                # Build configuration & dependencies
├── requirements.txt              # Pinned dependencies
└── README.md                     # Documentation
```

---

## 🚀 Getting Started

### 1. Prerequisites
- **Python:** 3.11 or newer (Python 3.14 compatible).
- **Virtual Environment Tool:** Python's built-in `venv`.

### 2. Setup Virtual Environment
In your terminal, navigate to the `ai_coding_mentor` directory:

```bash
# Windows (PowerShell)
cd d:\LinkedIn\ai_coding_mentor
python -m venv .venv
.\.venv\Scripts\activate

# Linux / macOS
cd ai_coding_mentor
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Install Dependencies
Install dependencies and install the package in editable mode:

```bash
pip install -r requirements.txt
pip install -e .
```

---

## ⚙️ Configuration & LLM Providers

The mentor supports official OpenAI models, local OpenAI-compatible models (Ollama, LM Studio, vLLM), OpenRouter, or an offline mock mode.

### Option A: Using OpenAI or an OpenAI-Compatible API
1. Copy `.env.example` to `.env`:
   ```bash
   cp .env.example .env
   ```
2. Open `.env` and set your API key:
   ```env
   MENTOR_LLM_PROVIDER=openai
   MENTOR_LLM_MODEL=gpt-4o-mini
   OPENAI_API_KEY=sk-your-actual-api-key-here
   ```

### Option B: Using a Local Model (Ollama / LM Studio)
Run fully offline with your local models without paying for API tokens:
```env
MENTOR_LLM_PROVIDER=openai-compatible
MENTOR_LLM_MODEL=llama3.2
MENTOR_LLM_BASE_URL=http://localhost:11434/v1
```

### Option C: Offline Mock Mode (Zero Setup / Instant Demo)
If you don't have an API key, you can run immediately using the built-in pedagogical mock provider:
```bash
coding-mentor --offline
```

---

## 💻 Running the Assistant

Run the CLI using either the installed entry point or Python module:

```bash
# Using the installed script
coding-mentor

# Or using python -m
python -m coding_mentor.main

# Launch in offline mock mode
coding-mentor --offline

# Launch with an initial assistance mode and project directory
coding-mentor --mode concept --project d:\LinkedIn\ai_coding_mentor
```

---

## 🕹️ Interactive CLI Commands

Once inside the interactive prompt, you can use the following commands:

| Command | Description | Example |
|---|---|---|
| `hint` | Switch to Hint Mode (default) | `hint` |
| `concept` | Switch to Concept Mode | `concept` |
| `pseudocode` | Switch to Pseudocode Mode | `pseudocode` |
| `review` | Paste code to review | `review` |
| `review <file>` | Directly review a project file | `review src/calculator.py` |
| `solution` | Switch to Solution Mode | `solution` |
| `debug` | Open multi-line debugger input for tracebacks | `debug` |
| `plan` | Plan project requirements, MVP, and milestones | `plan CLI Habit Tracker` |
| `context` | Inspect files and symbols in active project | `context` |
| `context <path>` | Attach a new project workspace directory | `context D:\MyProject` |
| `status` | View model, credentials status, and turn count | `status` |
| `tools` | Inspect registered tools and security settings | `tools` |
| `clear` | Reset conversation memory for a fresh session | `clear` |
| `help` | Display the commands banner | `help` |
| `quit` | Exit cleanly | `quit` |

---

## 🛡️ Security & Permission Architecture

The AI Coding Mentor treats all project files, inputs, and model outputs as untrusted data.

1. **Hard Path Containment:** Every file tool calls `PermissionManager.validate_path_containment()`. Any attempt to access files outside the project workspace raises a `PathSecurityError`.
2. **Secret Masking & Redaction:** Any file matching `.env*`, `*.pem`, `*.key`, `id_rsa*`, or `credentials.json` is blocked from reading and omitted from workspace summaries. Log records automatically redact detected API keys (`sk-...`, Bearer tokens).
3. **Interactive Confirmation Gates:**
   - Safe read operations (`read_file`, `list_files`, `search_symbols`) are auto-approved within the project boundary.
   - External execution (`run_python`, `run_tests`) and file modifications (`apply_patch`) are intercepted in Python code and prompt the user for interactive confirmation:
     ```text
     ⚠️  [Security Confirmation Required]
     Action: run_code
     Details: Execute Python script 'calculator.py'
     Allow this operation? (y/N): 
     ```
4. **No Command Injection:** Subprocess calls pass explicit argument lists without `shell=True`. Timeouts (default 15s) and bounded output buffers (max 4000 chars) prevent terminal hangs or resource exhaustion.

---

## 🧪 Running the Test Suite

The test suite runs 100% offline without requiring API keys or external services, utilizing `MockProvider` and `pytest`:

```bash
# Run all tests
pytest

# Run with verbose output
pytest -v

# Run with coverage report (if pytest-cov installed)
pytest --cov=coding_mentor
```

### Verified Test Categories:
- ✅ `test_config.py`: Environment variable loading, validation errors, secret masking.
- ✅ `test_permissions.py`: Path traversal attack rejection, secret shielding, confirmation callbacks.
- ✅ `test_project_context.py`: AST symbol extraction, .gitignore parsing, .env exclusion.
- ✅ `test_tools.py`: Safe file reading, line slicing, AST symbol search, syntax error pinpointing, diff proposal generation, sandboxed execution.
- ✅ `test_conversation.py`: Multi-turn conversation windowing, mode preservation, session clearing.
- ✅ `test_assistant.py`: Progressive mode flows, specialized workflows (debug, review, plan), tool calling loops, and provider error handling.

---

## 🔮 Future Extensibility

The modular architecture is prepared for future enhancements:
1. **Desktop GUI / Web UI:** `CodingMentorAssistant` is decoupled from `main.py`, allowing easy integration with Streamlit, Next.js, or PyQt.
2. **VS Code / Antigravity IDE Extension:** JSON-RPC / Language Server Protocol (LSP) adapter for in-editor sidecar mentoring.
3. **Additional Providers:** Simple extension of `LLMProvider` for Anthropic Claude, Google Gemini, or local HuggingFace models.
4. **Persistent Project Knowledge:** Project-specific indexing and notes stored in user-controlled local sqlite databases.
