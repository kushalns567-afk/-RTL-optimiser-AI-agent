"""
RTL Optimizer AI Agent - Command Line Interface
"""

import sys
import argparse
from pathlib import Path
from rtl_agent.eda.installer import check_eda_environment
from rtl_agent.core.analyzer import RTLAnalyzer
from rtl_agent.core.optimizer import RTLOptimizerAgent

def print_banner():
    banner = r"""
  ____ _____ _         ___        _   _           _              
 |  _ \_   _| |       / _ \ _ __ | |_(_)_ __ ___ (_)_______ _ __ 
 | |_) || | | |      | | | | '_ \| __| | '_ ` _ \| |_  / _ \ '__|
 |  _ < | | | |___   | |_| | |_) | |_| | | | | | | |/ /  __/ |   
 |_| \_\|_| |_____|   \___/| .__/ \__|_|_| |_| |_|_/___\___|_|   
                           |_|             AI Agent for VLSI RTL
    """
    print(banner)

def main():
    print_banner()
    parser = argparse.ArgumentParser(description="RTL Optimizer AI Agent for VLSI Digital Design")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Command: check-tools
    subparsers.add_parser("check-tools", help="Check EDA toolchain (Yosys, Icarus Verilog)")

    # Command: analyze
    p_analyze = subparsers.add_parser("analyze", help="Perform static analysis on Verilog file")
    p_analyze.add_argument("--input", "-i", required=True, help="Input Verilog file path")

    # Command: optimize
    p_opt = subparsers.add_parser("optimize", help="Run end-to-end PPA optimization")
    p_opt.add_argument("--input", "-i", required=True, help="Input Verilog file path")
    p_opt.add_argument("--output", "-o", default="", help="Output optimized Verilog file path")
    p_opt.add_argument("--testbench", "-t", default="", help="Testbench Verilog file for verification")
    p_opt.add_argument("--top", default="", help="Top-level module name")
    p_opt.add_argument("--strategy", "-s", choices=["balanced", "area", "timing", "power"], default="balanced", help="Optimization target")
    p_opt.add_argument("--provider", default="gemini", choices=["gemini", "openai", "heuristic_only", "ollama"], help="LLM Provider")

    args = parser.parse_args()

    if args.command == "check-tools":
        env = check_eda_environment()
        print("\nEDA Toolchain Environment Status:")
        for tool, status in env.items():
            avail = "[OK]" if status["available"] else "[MISSING]"
            path_str = status["path"] if status["available"] else "Not found on PATH or tools/"
            print(f"  {avail:9} {tool:<10} : {path_str}")
        print("\nTip: To download and install OSS CAD Suite (Yosys + iverilog), run:")
        print("  python scripts/download_tools.py\n")

    elif args.command == "analyze":
        input_path = Path(args.input)
        if not input_path.exists():
            print(f"Error: File '{args.input}' not found.")
            sys.exit(1)
        code = input_path.read_text(encoding="utf-8")
        analyzer = RTLAnalyzer(code)
        opps = analyzer.analyze()
        print(f"\nStatic Analysis Results for '{args.input}':")
        if not opps:
            print("  No critical anti-patterns or optimization bottlenecks found.")
        else:
            for opp in opps:
                print(f"  - [{opp.severity}] Line {opp.line_number} | {opp.category}")
                print(f"    Issue : {opp.description}")
                print(f"    Action: {opp.suggested_action}\n")

    elif args.command == "optimize":
        input_path = Path(args.input)
        if not input_path.exists():
            print(f"Error: Input file '{args.input}' not found.")
            sys.exit(1)

        print(f"Optimizing '{args.input}' (Strategy: {args.strategy.upper()})...")
        agent = RTLOptimizerAgent(provider=args.provider)
        opt_code, report = agent.optimize_file(
            input_file=args.input,
            output_file=args.output,
            testbench_file=args.testbench,
            top_module=args.top,
            strategy=args.strategy
        )

        print("\n" + report.generate_markdown())
        if args.output:
            print(f"\nOptimized RTL successfully saved to: {args.output}")

    else:
        parser.print_help()

if __name__ == "__main__":
    main()
