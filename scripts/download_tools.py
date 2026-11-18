"""
Download and Setup Required EDA Tools for RTL Optimizer AI Agent
Installs open-source synthesis and simulation tools:
- OSS CAD Suite (Yosys + Icarus Verilog + VVP + GTKWave)
- Python dependencies (requirements.txt)
"""

import sys
import subprocess
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from rtl_agent.eda.installer import check_eda_environment, install_oss_cad_suite

def install_python_deps():
    req_file = Path(__file__).resolve().parent.parent / "requirements.txt"
    print("\n[Step 1/2] Installing Python dependencies from requirements.txt...")
    cmd = [sys.executable, "-m", "pip", "install", "-r", str(req_file)]
    try:
        subprocess.run(cmd, check=True)
        print("[OK] Python dependencies installed successfully.")
    except Exception as e:
        print(f"[Warning] Failed to install Python dependencies: {e}")

def setup_eda_tools():
    print("\n[Step 2/2] Checking & Downloading Open-Source EDA Toolchain...")
    env = check_eda_environment()
    missing = [tool for tool, status in env.items() if not status["available"]]

    if not missing:
        print("[OK] All required EDA tools are already available on your system:")
        for tool, status in env.items():
            print(f" - {tool}: {status['path']}")
        return

    print(f"Missing tools: {', '.join(missing)}")
    print("Initiating automatic download and extraction of OSS CAD Suite (Yosys + Icarus Verilog)...")
    try:
        install_oss_cad_suite()
        print("\nRe-checking EDA environment...")
        new_env = check_eda_environment()
        for tool, status in new_env.items():
            status_str = "[READY]" if status["available"] else "[FAILED]"
            print(f" {status_str} {tool}: {status['path']}")
    except Exception as e:
        print(f"\n[Notice] Automated download encountered: {e}")
        print("\nManual Alternative:")
        print("1. Download the latest 'oss-cad-suite-windows-x64-*.exe' from:")
        print("   https://github.com/YosysHQ/oss-cad-suite-build/releases")
        print("2. Extract it into 'tools/oss-cad-suite' in this project folder.")
        print("3. Alternatively, install via Scoop: 'scoop install yosys iverilog'")

if __name__ == "__main__":
    install_python_deps()
    setup_eda_tools()
