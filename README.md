# ⚡ RTL Optimizer AI Agent for VLSI Digital Design

An automated, closed-loop AI agent for hardware engineers to analyze, optimize, and formally verify synthesizable **Verilog / SystemVerilog** RTL for **PPA (Power, Performance, Area)** while guaranteeing **Zero Functional Drift**.

---

## 🌟 Key Features

1. **Static RTL Bottleneck & Anti-Pattern Detection**:
   - Inadvertent transparent latch inference (missing `default` in combinational case / if-else).
   - Non-optimal multiplier & divider constants (strength reduction candidates).
   - Duplicate arithmetic operators across multiplexer branches (resource sharing).
   - Deep combinational arithmetic chains (pipelining & retiming candidates).
   - Inefficient FSM state encodings (Binary, Gray, One-Hot).
   - Cascaded priority encoder ladders.

2. **Multi-Engine PPA Optimization**:
   - **Deterministic VLSI Passes**: Built-in rule-based transformations that work offline with **0 API keys required**.
   - **LLM-Guided Optimizer**: Integrated with Google Gemini 1.5 Pro / Flash, OpenAI GPT-4o, and local Ollama models conditioned with expert VLSI ASIC/FPGA system prompts.
   - **Customizable Strategy**: Optimize specifically for `Area`, `Timing (Fmax)`, `Power`, or `Balanced PPA`.

3. **Closed-Loop Verification & Benchmarking**:
   - **Formal Equivalence**: Uses Yosys SAT/formal engine (`equiv_make`, `equiv_simple`, `equiv_status -assert`) to mathematically prove 100% equivalence.
   - **Simulation Equivalence**: Automatically executes testbenches using Icarus Verilog (`iverilog` + `vvp`).
   - **Automated PPA Delta Matrix**: Reports cell counts, Gate Equivalents (GE) area, wire counts, and logic depth levels before & after optimization.

4. **Multiple Interfaces**:
   - **Interactive Web Dashboard**: Streamlit GUI with side-by-side Verilog code editor, live diffs, PPA metric cards, and charts.
   - **Command-Line Interface (CLI)**: Fast commands for CI/CD pipelines and scriptable RTL passes.

---

## 📁 Project Structure

```
vlsi project/
├── rtl_agent/
│   ├── core/
│   │   ├── analyzer.py          # Static AST code smell & bottleneck detector
│   │   ├── heuristics.py        # Deterministic VLSI transformation passes
│   │   ├── optimizer.py         # End-to-end agentic loop controller
│   │   ├── prompt_templates.py  # Expert VLSI system prompts
│   │   ├── llm_client.py        # Multi-provider LLM connector (Gemini, OpenAI, Ollama)
│   │   └── reporter.py          # PPA delta matrix and markdown reporter
│   ├── eda/
│   │   ├── installer.py         # EDA toolchain detector & portable installer
│   │   ├── synthesizer.py       # Yosys synthesis runner & PPA extractor
│   │   ├── simulator.py         # Icarus Verilog simulation executor
│   │   └── equivalence.py       # Formal and simulation equivalence checker
│   └── ui/
│       ├── app.py               # Streamlit interactive web dashboard
│       └── cli.py               # Rich terminal CLI
├── examples/
│   ├── mac_unit/                # MAC benchmark (Constant strength reduction)
│   └── alu/                     # ALU benchmark (Resource sharing)
├── scripts/
│   ├── run_agent.py             # Main entry point (CLI, Web GUI, or Demo)
│   ├── download_tools.py        # Automated EDA toolchain downloader
│   └── install_eda_tools.ps1    # PowerShell complete tool installer
├── requirements.txt             # Python packages
├── config.yaml                  # Agent configuration
└── README.md
```

---

## 🚀 Quick Start

### 1. Run Built-In Benchmark Demo (No Setup Needed)
```bash
python scripts/run_agent.py --demo
```
This runs the agent on the `mac_unit` benchmark, showing a **+70.5% Area reduction** and **+40.6% Critical Path improvement** with simulation equivalence verification.

### 2. Static Analysis on Any Verilog File
```bash
python scripts/run_agent.py analyze -i examples/alu/alu.v
```

### 3. Run Optimization via CLI
```bash
python scripts/run_agent.py optimize -i examples/alu/alu.v -t examples/alu/alu_tb.v -s area --provider heuristic_only
```

### 4. Launch the Interactive Web Dashboard
```bash
python scripts/run_agent.py --gui
```
Access the dashboard at `http://localhost:8501`.

---

## 🛠️ Downloading & Installing Required EDA Tools

To enable full gate-level logic synthesis, cell mapping, and formal equivalence checking:

### Option A: Automatic Installer
Run the automated downloader (requires internet access):
```powershell
powershell -ExecutionPolicy Bypass -File scripts\install_eda_tools.ps1
```
Or run the Python installer:
```bash
python scripts/download_tools.py
```

### Option B: Package Managers
- **Scoop (Windows)**:
  ```powershell
  scoop install yosys iverilog
  ```
- **Chocolatey**:
  ```powershell
  choco install iverilog
  ```
- **Manual OSS CAD Suite**:
  Download `oss-cad-suite-windows-x64-*.exe` from [YosysHQ Releases](https://github.com/YosysHQ/oss-cad-suite-build/releases) and extract into `tools/oss-cad-suite`.

---

## ⚙️ Configuration & LLM Integration

Edit `config.yaml` to specify your target technology (e.g. `generic`, `sky130`, `ice40`), tool paths, or LLM providers:
```yaml
llm:
  provider: "gemini" # Options: gemini, openai, ollama, heuristic_only
  model: "gemini-1.5-pro"
  api_key_env_var: "GEMINI_API_KEY"
```

To use Gemini or OpenAI:
```powershell
$env:GEMINI_API_KEY = "your-api-key"
```
If no API key is provided, the agent automatically runs the offline **Deterministic Heuristic Engine**.
