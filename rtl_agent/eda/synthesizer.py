"""
RTL Synthesis & PPA Metrics Extractor
Runs logic synthesis via Yosys, technology maps to generic or Sky130 gates,
and computes gate count, sequential/combinational cells, logic levels, and area.
"""

import os
import re
import json
import subprocess
import tempfile
from pathlib import Path
from rtl_agent.eda.installer import get_installed_tool

class SynthesisResult:
    def __init__(self, success: bool, top_module: str = "", raw_output: str = "", errors: str = ""):
        self.success = success
        self.top_module = top_module
        self.raw_output = raw_output
        self.errors = errors
        self.total_cells = 0
        self.num_wires = 0
        self.num_wire_bits = 0
        self.num_registers = 0
        self.num_comb_cells = 0
        self.cell_breakdown: dict[str, int] = {}
        self.estimated_area = 0.0      # in Gate Equivalents (GE)
        self.logic_depth = 0           # estimated critical path logic levels
        self.metrics_source = "yosys"  # or "heuristic_estimator"

    def to_dict(self):
        return {
            "success": self.success,
            "top_module": self.top_module,
            "total_cells": self.total_cells,
            "num_wires": self.num_wires,
            "num_wire_bits": self.num_wire_bits,
            "num_registers": self.num_registers,
            "num_comb_cells": self.num_comb_cells,
            "cell_breakdown": self.cell_breakdown,
            "estimated_area_ge": round(self.estimated_area, 2),
            "logic_depth": self.logic_depth,
            "metrics_source": self.metrics_source,
            "errors": self.errors
        }

class Synthesizer:
    def __init__(self, yosys_path: str = ""):
        self.yosys = get_installed_tool("yosys", yosys_path)

    def is_available(self) -> bool:
        return bool(self.yosys)

    def synthesize(self, rtl_file: str, top_module: str = "", tech: str = "generic", timeout: int = 90) -> SynthesisResult:
        """
        Synthesizes RTL code and computes PPA metrics.
        """
        if not self.is_available():
            return self._heuristic_synthesis_estimate(rtl_file, top_module)

        # Use workspace-local temp directory so WASI (yowasp-yosys) has full read/write permission
        tmp_dir = Path(".rtl_agent_tmp")
        tmp_dir.mkdir(parents=True, exist_ok=True)
        netlist_path = tmp_dir / "synth.v"

        rtl_posix = Path(rtl_file).as_posix()
        top_arg = f"-top {top_module}" if top_module else "-auto-top"

        commands = [
            f'read_verilog -sv {rtl_posix}',
            f'synth {top_arg} -noabc',
            'stat'
        ]
        cmd_str = "; ".join(commands)

        try:
            proc = subprocess.run(
                [self.yosys, "-p", cmd_str],
                capture_output=True,
                text=True,
                timeout=timeout
            )
        except subprocess.TimeoutExpired:
            return SynthesisResult(False, top_module, "", "Yosys synthesis timed out.")
        except Exception as e:
            return SynthesisResult(False, top_module, "", f"Yosys execution failed: {e}")

        if proc.returncode != 0 and "ERROR:" in (proc.stderr or proc.stdout):
            # If native yosys failed, fallback to heuristic estimate
            res = self._heuristic_synthesis_estimate(rtl_file, top_module)
            res.errors = proc.stderr or proc.stdout
            return res

        output = proc.stdout + "\n" + proc.stderr
        result = self._parse_yosys_output(output, top_module)
        result.raw_output = output
        return result

    def _parse_yosys_output(self, output: str, top_module: str) -> SynthesisResult:
        res = SynthesisResult(True, top_module, output)
        normalized = output.replace("\r", "")
        
        # Look for JSON stat section in Yosys output
        json_match = re.search(r'\{\s*"creator":\s*"Yosys.*\}', normalized, re.DOTALL)
        if json_match:
            try:
                data = json.loads(json_match.group(0))
                modules = data.get("modules", {})
                for mod_name, mod_data in modules.items():
                    res.top_module = mod_name
                    num_cells = mod_data.get("num_cells_by_type", {})
                    res.cell_breakdown = num_cells
                    res.total_cells = sum(num_cells.values())
                    res.num_wires = mod_data.get("num_wires", 0)
                    res.num_wire_bits = mod_data.get("num_wire_bits", 0)

                    for cell, count in num_cells.items():
                        c_upper = cell.upper()
                        if any(ff in c_upper for ff in ["DFF", "DFFE", "SDFF", "REG", "LATCH"]):
                            res.num_registers += count
                        else:
                            res.num_comb_cells += count

                    res.estimated_area = (res.num_comb_cells * 1.2) + (res.num_registers * 5.0)
                    res.logic_depth = max(1, int(res.num_comb_cells ** 0.5) if res.num_comb_cells > 0 else 1)
                    return res
            except Exception:
                pass

        # Find the final '=== <module> ===' stat block in Yosys output
        stat_blocks = re.findall(r"===\s*([a-zA-Z0-9_]+)\s*===(.*?)(?=(?:===|\Z|End of script))", normalized, re.DOTALL)
        stat_content = stat_blocks[-1][1] if stat_blocks else normalized

        cells_match = re.search(r"(\d+)\s+cells", stat_content) or re.search(r"Number of cells:\s+(\d+)", stat_content)
        if cells_match:
            res.total_cells = int(cells_match.group(1))

        wires_match = re.search(r"(\d+)\s+wires", stat_content)
        if wires_match:
            res.num_wires = int(wires_match.group(1))

        bits_match = re.search(r"(\d+)\s+wire bits", stat_content)
        if bits_match:
            res.num_wire_bits = int(bits_match.group(1))

        # Cell breakdown lines in stat block e.g. "       82   $_AND_"
        cell_lines = re.findall(r"(\d+)\s+(\$_\w+|[A-Za-z0-9_]+)", stat_content)
        res.cell_breakdown = {}
        for count_str, cell_name in cell_lines:
            if any(k in cell_name.lower() for k in ["wire", "port", "bit", "cell", "local", "public", "count"]):
                continue
            c = int(count_str)
            res.cell_breakdown[cell_name] = c
            if any(k in cell_name.upper() for k in ["DFF", "DFFE", "REG", "LATCH"]):
                res.num_registers += c
            else:
                res.num_comb_cells += c

        if res.num_comb_cells == 0 and res.total_cells > 0:
            res.num_comb_cells = max(0, res.total_cells - res.num_registers)

        res.estimated_area = (res.num_comb_cells * 1.2) + (res.num_registers * 5.0)
        res.logic_depth = max(1, int(res.num_comb_cells ** 0.5) if res.num_comb_cells > 0 else 1)
        return res

    def _heuristic_synthesis_estimate(self, rtl_file: str, top_module: str = "") -> SynthesisResult:
        """
        Fast AST/RTL parser estimating gate counts, registers, and logic levels
        when Yosys is not installed.
        """
        code = Path(rtl_file).read_text(encoding="utf-8", errors="ignore")
        res = SynthesisResult(True, top_module or "top", "")
        res.metrics_source = "heuristic_estimator"

        # Count registers (always @(posedge ...))
        reg_assigns = len(re.findall(r"<=", code))
        dff_matches = len(re.findall(r"always\s*@\s*\(\s*posedge", code, re.IGNORECASE))
        res.num_registers = max(dff_matches, reg_assigns)

        # Count arithmetic operations
        mult_count = len(re.findall(r"\*", code)) - len(re.findall(r"/\*|\*/|\*\*", code))
        add_sub_count = len(re.findall(r"[+\-]", code))
        bitwise_count = len(re.findall(r"[&|^~]", code))
        mux_count = len(re.findall(r"\?|case|if\s*\(", code))

        # Estimate gate equivalents
        # 1-bit full adder ~ 7 GE, 8-bit mult ~ 150 GE, 16-bit mult ~ 600 GE
        est_mult_cells = max(0, mult_count) * 220
        est_add_cells = max(0, add_sub_count) * 28
        est_bitwise_cells = max(0, bitwise_count) * 4
        est_mux_cells = max(0, mux_count) * 12
        est_comb = est_mult_cells + est_add_cells + est_bitwise_cells + est_mux_cells

        res.num_comb_cells = max(10, est_comb)
        res.total_cells = res.num_comb_cells + (res.num_registers * 6)
        res.estimated_area = (res.num_comb_cells * 1.2) + (res.num_registers * 5.0)
        
        # Estimate logic depth (levels of combinational logic)
        res.logic_depth = max(2, int((mult_count * 8) + (add_sub_count * 3) + (mux_count * 2)))
        res.cell_breakdown = {
            "EST_COMB_GATES": res.num_comb_cells,
            "EST_DFF": res.num_registers,
            "EST_ARITH_MULT": max(0, mult_count),
            "EST_ARITH_ADD_SUB": max(0, add_sub_count),
            "EST_MUX": max(0, mux_count)
        }
        return res
