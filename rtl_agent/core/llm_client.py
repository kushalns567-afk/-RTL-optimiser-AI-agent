"""
Unified LLM Client for RTL Optimization
Supports Gemini, OpenAI, Claude, local Ollama, and Heuristic Fallback mode.
"""

import os
import re
import json
from rtl_agent.core.prompt_templates import VLSI_OPTIMIZER_SYSTEM_PROMPT, USER_OPTIMIZE_PROMPT_TEMPLATE
from rtl_agent.core.heuristics import HeuristicOptimizer

class LLMOptimizerClient:
    def __init__(self, provider: str = "gemini", model: str = "", api_key: str = ""):
        self.provider = provider.lower()
        self.model = model
        self.api_key = api_key or os.environ.get("GEMINI_API_KEY") or os.environ.get("OPENAI_API_KEY", "")

    def is_api_configured(self) -> bool:
        if self.provider == "ollama":
            return True
        return bool(self.api_key)

    def optimize_rtl(self, rtl_code: str, strategy: str, bottlenecks_str: str) -> tuple[str, str]:
        """
        Calls the configured LLM or falls back to the deterministic heuristic engine.
        Returns: (optimized_code, explanation)
        """
        if not self.is_api_configured() or self.provider == "heuristic_only":
            return self._heuristic_fallback(rtl_code, strategy)

        prompt = USER_OPTIMIZE_PROMPT_TEMPLATE.format(
            strategy=strategy,
            target_focus=f"Target: {strategy.upper()} optimization",
            bottlenecks=bottlenecks_str or "None specified",
            rtl_code=rtl_code
        )

        try:
            if self.provider == "gemini":
                return self._call_gemini(prompt)
            elif self.provider == "openai":
                return self._call_openai(prompt)
            elif self.provider == "ollama":
                return self._call_ollama(prompt)
            else:
                return self._heuristic_fallback(rtl_code, strategy)
        except Exception as e:
            print(f"[LLM Client Warning] LLM call failed ({e}). Falling back to deterministic heuristics.")
            return self._heuristic_fallback(rtl_code, strategy)

    def _call_gemini(self, prompt: str) -> tuple[str, str]:
        try:
            # Try new google-genai SDK
            from google import genai
            client = genai.Client(api_key=self.api_key)
            model_name = self.model or "gemini-1.5-pro"
            response = client.models.generate_content(
                model=model_name,
                contents=prompt,
                config={'system_instruction': VLSI_OPTIMIZER_SYSTEM_PROMPT}
            )
            text = response.text
            return self._extract_verilog_and_notes(text)
        except Exception:
            # Try fallback requests-based Gemini API call
            import urllib.request
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model or 'gemini-1.5-flash'}:generateContent?key={self.api_key}"
            payload = {
                "contents": [{"parts": [{"text": prompt}]}],
                "systemInstruction": {"parts": [{"text": VLSI_OPTIMIZER_SYSTEM_PROMPT}]}
            }
            req = urllib.request.Request(
                url,
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json"}
            )
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = json.loads(resp.read().decode())
                text = data["candidates"][0]["content"]["parts"][0]["text"]
                return self._extract_verilog_and_notes(text)

    def _call_openai(self, prompt: str) -> tuple[str, str]:
        from openai import OpenAI
        client = OpenAI(api_key=self.api_key)
        resp = client.chat.completions.create(
            model=self.model or "gpt-4o",
            messages=[
                {"role": "system", "content": VLSI_OPTIMIZER_SYSTEM_PROMPT},
                {"role": "user", "content": prompt}
            ],
            temperature=0.2
        )
        text = resp.choices[0].message.content
        return self._extract_verilog_and_notes(text)

    def _call_ollama(self, prompt: str) -> tuple[str, str]:
        import urllib.request
        url = "http://localhost:11434/api/generate"
        payload = {
            "model": self.model or "codellama",
            "prompt": f"{VLSI_OPTIMIZER_SYSTEM_PROMPT}\n\n{prompt}",
            "stream": False
        }
        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"}
        )
        with urllib.request.urlopen(req, timeout=45) as resp:
            data = json.loads(resp.read().decode())
            return self._extract_verilog_and_notes(data.get("response", ""))

    def _heuristic_fallback(self, rtl_code: str, strategy: str) -> tuple[str, str]:
        opt = HeuristicOptimizer(rtl_code)
        opt_code, changes = opt.optimize(strategy=strategy)
        if not changes:
            notes = "Heuristic engine inspected the design: No rule-based bottlenecks found, or design is already optimized."
        else:
            notes = "Applied Rule-Based Heuristic VLSI Passes:\n" + "\n".join(f"- {c}" for c in changes)
        return opt_code, notes

    def _extract_verilog_and_notes(self, text: str) -> tuple[str, str]:
        match = re.search(r"```(?:verilog|systemverilog|v)?(.*?)```", text, re.DOTALL | re.IGNORECASE)
        if match:
            code = match.group(1).strip()
            # Everything outside the code block is explanation
            notes = text.replace(match.group(0), "").strip()
            return code, notes
        return text, "Generated response"
