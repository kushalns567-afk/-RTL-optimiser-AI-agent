"""
RTL Static Code Analyzer & Antipattern Detector
Inspects Verilog/SystemVerilog RTL for VLSI design bottlenecks,
timing critical paths, inferred latches, and PPA optimization opportunities.
"""

import re
from dataclasses import dataclass
from typing import List

@dataclass
class OptimizationOpportunity:
    category: str        # e.g., "Strength Reduction", "Resource Sharing", "Pipelining", "Latch Elimination", "FSM"
    severity: str        # "High", "Medium", "Low"
    line_number: int
    code_snippet: str
    description: str
    suggested_action: str

class RTLAnalyzer:
    def __init__(self, code: str):
        self.code = code
        self.lines = code.splitlines()

    def analyze(self) -> List[OptimizationOpportunity]:
        opportunities = []
        opportunities.extend(self._check_strength_reduction())
        opportunities.extend(self._check_resource_sharing())
        opportunities.extend(self._check_inferred_latches())
        opportunities.extend(self._check_pipelining_opportunities())
        opportunities.extend(self._check_fsm_encoding())
        opportunities.extend(self._check_cascaded_muxes())
        return opportunities

    def _check_strength_reduction(self) -> List[OptimizationOpportunity]:
        """Detects multiplication or division by constants that can be converted to shift-and-add."""
        results = []
        # Pattern: signal * <number> or <number> * signal
        mult_pat = re.compile(r"([a-zA-Z0-9_]+)\s*\*\s*(\d+)|(\d+)\s*\*\s*([a-zA-Z0-9_]+)")
        for idx, line in enumerate(self.lines, start=1):
            # Skip comments
            clean_line = re.sub(r"//.*", "", line)
            match = mult_pat.search(clean_line)
            if match:
                const_val = int(match.group(2) or match.group(3))
                # Powers of 2 or small composite integers (e.g. 3, 5, 6, 7, 9, 10)
                is_power_of_two = (const_val & (const_val - 1) == 0) and const_val > 0
                if is_power_of_two:
                    shift_amt = const_val.bit_length() - 1
                    results.append(OptimizationOpportunity(
                        category="Strength Reduction",
                        severity="High",
                        line_number=idx,
                        code_snippet=line.strip(),
                        description=f"Multiplication by power-of-2 constant ({const_val}) synthesizes into an expensive DSP/multiplier block.",
                        suggested_action=f"Replace '{match.group(0)}' with bit shift: '<< {shift_amt}' to consume 0 logic gates."
                    ))
                elif const_val in [3, 5, 6, 7, 9, 10, 12, 14, 15]:
                    results.append(OptimizationOpportunity(
                        category="Strength Reduction",
                        severity="High",
                        line_number=idx,
                        code_snippet=line.strip(),
                        description=f"Multiplication by small integer constant ({const_val}) incurs high silicon area and delay.",
                        suggested_action=f"Convert to shift-and-add equivalent (e.g., * {const_val} => (x << n) + (x << m))."
                    ))
        return results

    def _check_resource_sharing(self) -> List[OptimizationOpportunity]:
        """Detects duplicated arithmetic operations across mutually exclusive branches or ternary expressions."""
        results = []
        # Check ternary duplicate arithmetic e.g. cond ? (a + b) : (a + c) or cond ? a + b : a + c
        ternary_pat = re.compile(r"\?\s*\(?\s*([a-zA-Z0-9_]+)\s*([+\-*/])\s*([a-zA-Z0-9_]+)\s*\)?\s*:\s*\(?\s*([a-zA-Z0-9_]+)\s*\2\s*([a-zA-Z0-9_]+)\s*\)?")
        for idx, line in enumerate(self.lines, start=1):
            clean = re.sub(r"//.*", "", line)
            match = ternary_pat.search(clean)
            if match:
                op = match.group(2)
                results.append(OptimizationOpportunity(
                    category="Resource Sharing",
                    severity="Medium",
                    line_number=idx,
                    code_snippet=line.strip(),
                    description=f"Duplicate arithmetic operator '{op}' detected in ternary multiplexer.",
                    suggested_action="Factor out the common operator and multiplex the operands before the arithmetic operation."
                ))

        # Check if multiple adders/multipliers appear inside different branches of a case/if statement
        adders_in_branches = 0
        branch_lines = []
        for idx, line in enumerate(self.lines, start=1):
            clean = re.sub(r"//.*", "", line)
            if re.search(r"\b(if|else|case)\b", clean):
                pass
            if "+" in clean or "-" in clean:
                if any(k in clean for k in ["<=", "="]) and not re.search(r"\bfor\b", clean):
                    adders_in_branches += 1
                    branch_lines.append((idx, line.strip()))

        if adders_in_branches >= 2 and not results:
            results.append(OptimizationOpportunity(
                category="Resource Sharing",
                severity="Medium",
                line_number=branch_lines[0][0] if branch_lines else 1,
                code_snippet=branch_lines[0][1] if branch_lines else "",
                description=f"Detected {adders_in_branches} separate addition/subtraction instances in conditional paths.",
                suggested_action="Multiplex the adder inputs rather than the outputs to share a single hardware adder unit."
            ))
        return results

    def _check_inferred_latches(self) -> List[OptimizationOpportunity]:
        """Detects combinational always blocks missing default assignment, inferring unwanted transparent latches."""
        results = []
        in_comb_always = False
        start_line = 1
        has_default = False
        has_case = False

        for idx, line in enumerate(self.lines, start=1):
            clean = re.sub(r"//.*", "", line)
            if re.search(r"always\s*@\s*\(\s*\*\s*\)|always_comb", clean):
                in_comb_always = True
                start_line = idx
                has_default = False
                has_case = False

            if in_comb_always:
                if "case" in clean:
                    has_case = True
                if "default:" in clean or "default :" in clean:
                    has_default = True
                if "end" in clean and in_comb_always:
                    if has_case and not has_default:
                        results.append(OptimizationOpportunity(
                            category="Latch Elimination",
                            severity="High",
                            line_number=start_line,
                            code_snippet=self.lines[start_line - 1].strip(),
                            description="Combinational 'case' statement lacks a 'default' branch, potentially inferring transparent latches.",
                            suggested_action="Add 'default: ...' or assign default safe values at the beginning of the combinational block."
                        ))
                    in_comb_always = False
        return results

    def _check_pipelining_opportunities(self) -> List[OptimizationOpportunity]:
        """Detects long unpipelined combinational paths (e.g. multiply followed by multi-operand addition)."""
        results = []
        for idx, line in enumerate(self.lines, start=1):
            clean = re.sub(r"//.*", "", line)
            # Detect chained arithmetic e.g. a * b + c * d
            if clean.count("*") >= 2 or (("*" in clean) and (clean.count("+") >= 2)):
                results.append(OptimizationOpportunity(
                    category="Pipelining / Retiming",
                    severity="High",
                    line_number=idx,
                    code_snippet=line.strip(),
                    description="Deep combinational arithmetic path (chained multiplication and addition) limits maximum clock frequency (Fmax).",
                    suggested_action="Insert pipeline register stage between multiplier and accumulator/adder tree."
                ))
        return results

    def _check_fsm_encoding(self) -> List[OptimizationOpportunity]:
        """Checks for FSM state encodings (binary vs one-hot vs gray)."""
        results = []
        state_params = []
        for idx, line in enumerate(self.lines, start=1):
            clean = re.sub(r"//.*", "", line)
            if re.search(r"(parameter|localparam)\s+.*STATE|S_\w+", clean, re.IGNORECASE):
                state_params.append((idx, line.strip()))
        
        if len(state_params) >= 4:
            results.append(OptimizationOpportunity(
                category="FSM Optimization",
                severity="Medium",
                line_number=state_params[0][0],
                code_snippet=state_params[0][1],
                description=f"Detected FSM with {len(state_params)} states.",
                suggested_action="Evaluate One-Hot encoding for FPGA/high-speed targets or Gray/Binary for low-power and minimum area."
            ))
        return results

    def _check_cascaded_muxes(self) -> List[OptimizationOpportunity]:
        """Detects nested if-else ladders inferring priority encoders."""
        results = []
        else_if_count = 0
        first_line = 1
        for idx, line in enumerate(self.lines, start=1):
            clean = re.sub(r"//.*", "", line)
            if "else if" in clean:
                if else_if_count == 0:
                    first_line = idx
                else_if_count += 1
            elif "end" in clean:
                if else_if_count >= 3:
                    results.append(OptimizationOpportunity(
                        category="Multiplexer Restructuring",
                        severity="Medium",
                        line_number=first_line,
                        code_snippet=self.lines[first_line - 1].strip(),
                        description=f"Deep 'else-if' chain ({else_if_count + 1} levels) synthesizes into a serial priority encoder with high propagation delay.",
                        suggested_action="Convert mutually exclusive conditions to parallel 'case' or balanced tree to reduce critical path delay."
                    ))
                else_if_count = 0
        return results
