"""
Main Launcher for RTL Optimizer AI Agent
"""

import sys
import subprocess
from pathlib import Path

# Add project root to path
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

def launch_gui():
    app_path = ROOT_DIR / "rtl_agent" / "ui" / "app.py"
    print(f"Starting RTL Optimizer Web Dashboard at http://localhost:8501...")
    cmd = [sys.executable, "-m", "streamlit", "run", str(app_path)]
    subprocess.run(cmd)

def run_demo():
    print("=" * 70)
    print("  RUNNING RTL OPTIMIZER AI AGENT DEMONSTRATION")
    print("=" * 70)
    from rtl_agent.core.optimizer import RTLOptimizerAgent

    mac_input = ROOT_DIR / "examples" / "mac_unit" / "mac_unit.v"
    mac_tb = ROOT_DIR / "examples" / "mac_unit" / "mac_unit_tb.v"
    mac_output = ROOT_DIR / "examples" / "mac_unit" / "mac_unit_optimized.v"

    agent = RTLOptimizerAgent(provider="heuristic_only")
    print(f"\n[1] Optimizing MAC Unit: {mac_input.name}")
    opt_code, report = agent.optimize_file(
        input_file=str(mac_input),
        output_file=str(mac_output),
        testbench_file=str(mac_tb),
        top_module="mac_unit",
        strategy="balanced"
    )

    print("\n" + report.generate_markdown())
    print("\n[Demo Complete] Optimized RTL generated at: examples/mac_unit/mac_unit_optimized.v")

def main():
    if len(sys.argv) > 1 and sys.argv[1] == "--gui":
        launch_gui()
    elif len(sys.argv) > 1 and sys.argv[1] == "--demo":
        run_demo()
    else:
        from rtl_agent.ui.cli import main as cli_main
        cli_main()

if __name__ == "__main__":
    main()
