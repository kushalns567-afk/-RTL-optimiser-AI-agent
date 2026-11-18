"""
Deterministic Heuristic Transformations for Verilog RTL
Applies verified PPA optimization rules directly to RTL code.
"""

import re

class HeuristicOptimizer:
    def __init__(self, code: str):
        self.code = code
        self.applied_transformations: list[str] = []

    def optimize(self, strategy: str = "balanced") -> tuple[str, list[str]]:
        opt_code = self.code
        
        # 1. Strength Reduction (Applicable to area, timing, power, balanced)
        opt_code, str_applied = self.apply_strength_reduction(opt_code)
        self.applied_transformations.extend(str_applied)

        # 2. Latch Elimination (Always safe and required)
        opt_code, latch_applied = self.apply_latch_elimination(opt_code)
        self.applied_transformations.extend(latch_applied)

        # 3. Resource Sharing (Primarily for Area and Power)
        if strategy in ["area", "power", "balanced"]:
            opt_code, share_applied = self.apply_resource_sharing(opt_code)
            self.applied_transformations.extend(share_applied)

        return opt_code, self.applied_transformations

    def apply_strength_reduction(self, code: str) -> tuple[str, list[str]]:
        """Replaces constant multiplications with equivalent shift and add expressions."""
        applied = []

        def replace_mult(match):
            sig1, c1, c2, sig2 = match.groups()
            sig = sig1 or sig2
            const_val = int(c1 or c2)

            # Check power of two: 2, 4, 8, 16, 32, 64, 128, 256
            if (const_val & (const_val - 1) == 0) and const_val > 1:
                shift = const_val.bit_length() - 1
                applied.append(f"Strength reduction: '{sig} * {const_val}' -> '({sig} << {shift})'")
                return f"({sig} << {shift})"
            
            # Common constants: 3, 5, 6, 7, 9, 10, 12
            if const_val == 3:
                applied.append(f"Strength reduction: '{sig} * 3' -> '(({sig} << 1) + {sig})'")
                return f"(({sig} << 1) + {sig})"
            elif const_val == 5:
                applied.append(f"Strength reduction: '{sig} * 5' -> '(({sig} << 2) + {sig})'")
                return f"(({sig} << 2) + {sig})"
            elif const_val == 6:
                applied.append(f"Strength reduction: '{sig} * 6' -> '(({sig} << 2) + ({sig} << 1))'")
                return f"(({sig} << 2) + ({sig} << 1))"
            elif const_val == 9:
                applied.append(f"Strength reduction: '{sig} * 9' -> '(({sig} << 3) + {sig})'")
                return f"(({sig} << 3) + {sig})"
            elif const_val == 10:
                applied.append(f"Strength reduction: '{sig} * 10' -> '(({sig} << 3) + ({sig} << 1))'")
                return f"(({sig} << 3) + ({sig} << 1))"

            return match.group(0)

        # Match "var * num" or "num * var"
        pattern = r"\b([a-zA-Z_]\w*)\s*\*\s*(\d+)\b|\b(\d+)\s*\*\s*([a-zA-Z_]\w*)\b"
        new_code = re.sub(pattern, replace_mult, code)
        return new_code, applied

    def apply_latch_elimination(self, code: str) -> tuple[str, list[str]]:
        """Ensures combinational case blocks have a default branch."""
        applied = []
        lines = code.splitlines()
        new_lines = []
        in_comb = False
        in_case = False
        has_default = False
        case_end_idx = -1

        for line in lines:
            clean = re.sub(r"//.*", "", line)
            if re.search(r"always\s*@\s*\(\s*\*\s*\)|always_comb", clean):
                in_comb = True
            
            if in_comb and re.search(r"\bcase\s*\(", clean):
                in_case = True
                has_default = False

            if in_case and "default" in clean:
                has_default = True

            if in_case and re.search(r"\bendcase\b", clean):
                if not has_default:
                    # Insert safe default before endcase
                    indent = " " * (len(line) - len(line.lstrip()) + 4)
                    new_lines.append(f"{indent}default: ; // Inferred latch prevention added by RTL Optimizer Agent")
                    applied.append("Latch elimination: Added missing 'default: ;' to combinational case block")
                in_case = False
                in_comb = False

            new_lines.append(line)

        return "\n".join(new_lines), applied

    def apply_resource_sharing(self, code: str) -> tuple[str, list[str]]:
        """Detects ternary operator arithmetic sharing e.g. cond ? (a + b) : (a + c) => a + (cond ? b : c)."""
        applied = []
        # Pattern: cond ? (a + b) : (a + c) or cond ? a + b : a + c
        pattern = re.compile(r"(\([^\)]+\)|[a-zA-Z0-9_]+)\s*\?\s*\(?\s*([a-zA-Z0-9_]+)\s*\+\s*([a-zA-Z0-9_]+)\s*\)?\s*:\s*\(?\s*\2\s*\+\s*([a-zA-Z0-9_]+)\s*\)?")
        
        def share_adder(match):
            cond = match.group(1)
            shared_op = match.group(2)
            op1 = match.group(3)
            op2 = match.group(4)
            applied.append(f"Resource sharing: Shared adder for '{shared_op} + ({cond} ? {op1} : {op2})'")
            return f"({shared_op} + ({cond} ? {op1} : {op2}))"

        new_code = pattern.sub(share_adder, code)
        return new_code, applied
