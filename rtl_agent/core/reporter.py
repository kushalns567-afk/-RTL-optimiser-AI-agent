"""
PPA Metrics Delta & Optimization Reporter
Generates comprehensive reports comparing baseline vs optimized RTL.
"""

from rtl_agent.eda.synthesizer import SynthesisResult
from rtl_agent.eda.equivalence import EquivalenceResult

class OptimizationReport:
    def __init__(
        self,
        module_name: str,
        strategy: str,
        baseline_synth: SynthesisResult,
        opt_synth: SynthesisResult,
        equiv_res: EquivalenceResult,
        notes: str = ""
    ):
        self.module_name = module_name
        self.strategy = strategy
        self.baseline_synth = baseline_synth
        self.opt_synth = opt_synth
        self.equiv_res = equiv_res
        self.notes = notes

    def compute_deltas(self) -> dict:
        base = self.baseline_synth
        opt = self.opt_synth

        def pct(old, new):
            if old == 0:
                return 0.0
            return round(((old - new) / old) * 100, 2)

        return {
            "cell_reduction_pct": pct(base.total_cells, opt.total_cells),
            "area_reduction_pct": pct(base.estimated_area, opt.estimated_area),
            "depth_reduction_pct": pct(base.logic_depth, opt.logic_depth),
            "reg_diff": opt.num_registers - base.num_registers,
            "orig_cells": base.total_cells,
            "opt_cells": opt.total_cells,
            "orig_area": round(base.estimated_area, 1),
            "opt_area": round(opt.estimated_area, 1),
            "orig_depth": base.logic_depth,
            "opt_depth": opt.logic_depth,
            "equivalent": self.equiv_res.equivalent,
            "verification_method": self.equiv_res.method
        }

    def generate_markdown(self) -> str:
        d = self.compute_deltas()
        equiv_status = "PASSED" if d["equivalent"] else "FAILED"
        
        md = []
        md.append(f"# RTL Optimization Report: `{self.module_name}`")
        md.append(f"**Strategy**: `{self.strategy.upper()}` | **Equivalence Verification**: `{equiv_status}` ({d['verification_method']})")
        md.append("")
        md.append("## PPA Comparison Matrix")
        md.append("| Metric | Baseline | Optimized | Delta | Improvement |")
        md.append("| :--- | :--- | :--- | :--- | :--- |")
        md.append(f"| **Total Cell Count** | {d['orig_cells']} | {d['opt_cells']} | {d['opt_cells'] - d['orig_cells']} | **{d['cell_reduction_pct']:+.1f}%** |")
        md.append(f"| **Estimated Area (GE)** | {d['orig_area']} | {d['opt_area']} | {round(d['opt_area'] - d['orig_area'], 1)} | **{d['area_reduction_pct']:+.1f}%** |")
        md.append(f"| **Critical Path Depth** | {d['orig_depth']} lvls | {d['opt_depth']} lvls | {d['opt_depth'] - d['orig_depth']} | **{d['depth_reduction_pct']:+.1f}%** |")
        md.append(f"| **Registers / DFFs** | {self.baseline_synth.num_registers} | {self.opt_synth.num_registers} | {d['reg_diff']:+d} | - |")
        md.append("")
        md.append("## Verification Details")
        md.append(f"> {self.equiv_res.details}")
        md.append("")
        if self.notes:
            md.append("## Agent Notes & Transformation Log")
            md.append(self.notes)
            md.append("")

        return "\n".join(md)
