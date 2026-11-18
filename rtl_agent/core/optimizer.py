"""
RTL Optimization Orchestrator
Coordinates static analysis, synthesis, simulation, LLM/heuristic transformations,
and formal equivalence verification into an end-to-end agentic loop.
"""

import tempfile
from pathlib import Path
from rtl_agent.core.analyzer import RTLAnalyzer
from rtl_agent.core.llm_client import LLMOptimizerClient
from rtl_agent.core.reporter import OptimizationReport
from rtl_agent.eda.synthesizer import Synthesizer, SynthesisResult
from rtl_agent.eda.simulator import Simulator
from rtl_agent.eda.equivalence import EquivalenceChecker, EquivalenceResult

class RTLOptimizerAgent:
    def __init__(
        self,
        provider: str = "gemini",
        model: str = "",
        api_key: str = "",
        yosys_path: str = "",
        iverilog_path: str = "",
        vvp_path: str = ""
    ):
        self.synthesizer = Synthesizer(yosys_path=yosys_path)
        self.simulator = Simulator(iverilog_path=iverilog_path, vvp_path=vvp_path)
        self.equiv_checker = EquivalenceChecker(yosys_path=yosys_path, iverilog_path=iverilog_path)
        self.llm_client = LLMOptimizerClient(provider=provider, model=model, api_key=api_key)

    def optimize_file(
        self,
        input_file: str,
        output_file: str = "",
        testbench_file: str = "",
        top_module: str = "",
        strategy: str = "balanced"
    ) -> tuple[str, OptimizationReport]:
        """
        Executes end-to-end RTL optimization on a Verilog file.
        """
        code = Path(input_file).read_text(encoding="utf-8")
        opt_code, report = self.optimize_code(
            code=code,
            testbench_file=testbench_file,
            top_module=top_module,
            strategy=strategy
        )

        if output_file:
            out_p = Path(output_file)
            out_p.parent.mkdir(parents=True, exist_ok=True)
            out_p.write_text(opt_code, encoding="utf-8")

        return opt_code, report

    def optimize_code(
        self,
        code: str,
        testbench_file: str = "",
        top_module: str = "",
        strategy: str = "balanced"
    ) -> tuple[str, OptimizationReport]:
        """
        Executes end-to-end optimization loop on raw code string.
        """
        # 1. Static RTL Analysis
        analyzer = RTLAnalyzer(code)
        opportunities = analyzer.analyze()
        opp_strings = [
            f"- [{o.severity}] {o.category} at line {o.line_number}: {o.description} -> {o.suggested_action}"
            for o in opportunities
        ]
        bottlenecks_text = "\n".join(opp_strings) if opp_strings else "No critical anti-patterns detected."

        # Write original code to local temp file for synthesis and formal equivalence
        tmp_path = Path(".rtl_agent_tmp")
        tmp_path.mkdir(parents=True, exist_ok=True)
        orig_file = tmp_path / "baseline.v"
        orig_file.write_text(code, encoding="utf-8")

        # 2. Baseline Synthesis
        baseline_synth = self.synthesizer.synthesize(str(orig_file), top_module=top_module)
        module_name = top_module or baseline_synth.top_module or "top_module"

        # 3. Baseline Simulation (if TB provided)
        if testbench_file and Path(testbench_file).exists():
            tb_base_sim = self.simulator.run_simulation([str(orig_file)], testbench_file, module_name)
            if not tb_base_sim.success:
                print(f"[Warning] Baseline testbench simulation failed:\n{tb_base_sim.errors}")

        # 4. LLM / Heuristic Optimization
        opt_code, notes = self.llm_client.optimize_rtl(code, strategy=strategy, bottlenecks_str=bottlenecks_text)

        # Write optimized candidate to file
        opt_file = tmp_path / "optimized.v"
        opt_file.write_text(opt_code, encoding="utf-8")

        # 5. Formal & Simulation Equivalence Verification
        equiv_res = self.equiv_checker.verify(
            orig_file=str(orig_file),
            opt_file=str(opt_file),
            top_module=module_name,
            testbench_file=testbench_file
        )

        # 6. Post-Optimization Synthesis & PPA extraction
        opt_synth = self.synthesizer.synthesize(str(opt_file), top_module=module_name)

        # 7. Build Comprehensive Report
        report = OptimizationReport(
            module_name=module_name,
            strategy=strategy,
            baseline_synth=baseline_synth,
            opt_synth=opt_synth,
            equiv_res=equiv_res,
            notes=notes
        )

        return opt_code, report
