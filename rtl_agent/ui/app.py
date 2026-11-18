"""
RTL Optimizer AI Agent - Interactive Web Dashboard
Streamlit-based GUI for VLSI RTL Analysis, Optimization & PPA Benchmarking.
"""

import os
import streamlit as st
import matplotlib.pyplot as plt
from pathlib import Path

from rtl_agent.eda.installer import check_eda_environment
from rtl_agent.core.analyzer import RTLAnalyzer
from rtl_agent.core.optimizer import RTLOptimizerAgent

# Example benchmark RTLs
SAMPLE_BENCHMARKS = {
    "MAC Unit (Multiply-Accumulator with Constant Scaling)": """// Multiply-Accumulator Unit with constant scaling factor
module mac_unit (
    input  wire        clk,
    input  wire        rst_n,
    input  wire [7:0]  data_in,
    input  wire        valid_in,
    output reg  [15:0] acc_out
);

    wire [15:0] scaled_val;
    // Anti-pattern: Multiplying by constant 10 and 4 in combinational path
    assign scaled_val = (data_in * 10) + (data_in * 4);

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            acc_out <= 16'd0;
        end else if (valid_in) begin
            acc_out <= acc_out + scaled_val;
        end
    end

endmodule
""",
    "ALU (Arithmetic Logic Unit with Resource Sharing Opportunities)": """// 8-bit ALU with duplicate adders across conditional branches
module alu (
    input  wire [7:0] a,
    input  wire [7:0] b,
    input  wire [7:0] c,
    input  wire       mode,
    output wire [8:0] result
);

    // Anti-pattern: Separate adders instantiated across ternary conditional
    assign result = mode ? (a + b) : (a + c);

endmodule
""",
    "State Machine with Inferred Latch Risk": """// FSM with combinational case block missing default
module fsm_decoder (
    input  wire [1:0] state,
    input  wire [7:0] data,
    output reg  [7:0] ctrl_out
);

    // Anti-pattern: Incomplete case block infers transparent latches
    always @(*) begin
        case (state)
            2'b00: ctrl_out = data;
            2'b01: ctrl_out = data + 8'd1;
            2'b10: ctrl_out = data << 1;
        endcase
    end

endmodule
"""
}

def main():
    st.set_page_config(
        page_title="RTL Optimizer AI Agent",
        page_icon="⚡",
        layout="wide"
    )

    st.title("⚡ RTL Optimizer AI Agent for VLSI")
    st.caption("Automated PPA (Power, Performance, Area) Optimization & Formal Equivalence Verification for Verilog/SystemVerilog")

    # Sidebar: Toolchain & Configuration
    with st.sidebar:
        st.header("🛠️ Toolchain Status")
        env = check_eda_environment()
        
        yosys_ok = env["yosys"]["available"]
        iverilog_ok = env["iverilog"]["available"]

        st.markdown(f"**Yosys (Synthesis & Formal)**: {'🟢 Available' if yosys_ok else '🔴 Missing'}")
        if yosys_ok:
            st.caption(f"Path: `{env['yosys']['path']}`")
        
        st.markdown(f"**Icarus Verilog (Simulation)**: {'🟢 Available' if iverilog_ok else '🔴 Missing'}")
        if iverilog_ok:
            st.caption(f"Path: `{env['iverilog']['path']}`")

        if not (yosys_ok and iverilog_ok):
            st.info("💡 To install open-source EDA tools (OSS CAD Suite):\nRun `python scripts/download_tools.py` in your terminal.")

        st.divider()
        st.header("⚙️ Agent Settings")
        provider = st.selectbox(
            "AI / Optimization Engine",
            ["gemini", "openai", "heuristic_only", "ollama"],
            index=2,
            help="'heuristic_only' uses rule-based VLSI passes with 0 API keys required."
        )

        api_key = ""
        if provider in ["gemini", "openai"]:
            api_key = st.text_input(f"{provider.upper()} API Key", type="password", value=os.environ.get(f"{provider.upper()}_API_KEY", ""))

        strategy = st.selectbox(
            "Optimization Target",
            ["balanced", "area", "timing", "power"],
            index=0,
            help="Directs the optimization passes towards specific PPA constraints."
        )

        top_module = st.text_input("Top Module Name (Optional)", value="")

    # Benchmark loader
    selected_sample = st.selectbox(
        "Load Sample VLSI Benchmark or Write Custom Code:",
        ["[Custom RTL Input]"] + list(SAMPLE_BENCHMARKS.keys())
    )

    initial_code = SAMPLE_BENCHMARKS.get(selected_sample, "") if selected_sample != "[Custom RTL Input]" else ""

    col_orig, col_opt = st.columns(2)

    with col_orig:
        st.subheader("📄 Baseline RTL (Verilog)")
        verilog_input = st.text_area(
            "Original Verilog Code:",
            value=initial_code,
            height=380,
            placeholder="// Paste your synthesizable Verilog code here..."
        )

    # Static Analysis Button
    if verilog_input.strip():
        analyzer = RTLAnalyzer(verilog_input)
        opps = analyzer.analyze()
        with st.expander(f"🔍 Static RTL Bottlenecks Detected ({len(opps)} findings)", expanded=(len(opps) > 0)):
            if not opps:
                st.success("✅ Clean RTL! No obvious hardware anti-patterns found.")
            else:
                for opp in opps:
                    color = "red" if opp.severity == "High" else "orange"
                    st.markdown(f"- **:{color}[[{opp.severity}]] {opp.category}** (Line {opp.line_number}): {opp.description}")
                    st.caption(f"👉 **Suggested Action**: {opp.suggested_action}")

    # Optimize Button
    if st.button("🚀 Run RTL Optimization", type="primary", disabled=not bool(verilog_input.strip())):
        with st.spinner("Analyzing RTL, running baseline synthesis, applying PPA optimizations, and verifying equivalence..."):
            agent = RTLOptimizerAgent(
                provider=provider,
                api_key=api_key
            )
            opt_code, report = agent.optimize_code(
                code=verilog_input,
                top_module=top_module,
                strategy=strategy
            )

            # Store in session state
            st.session_state["opt_code"] = opt_code
            st.session_state["report"] = report

    # Display results if available
    if "opt_code" in st.session_state and "report" in st.session_state:
        opt_code = st.session_state["opt_code"]
        report = st.session_state["report"]
        deltas = report.compute_deltas()

        with col_opt:
            st.subheader("✨ Optimized RTL (Verilog)")
            st.text_area("Optimized Verilog Code:", value=opt_code, height=380)
            st.download_button(
                "⬇️ Download Optimized RTL (.v)",
                data=opt_code,
                file_name="optimized_rtl.v",
                mime="text/plain"
            )

        st.divider()
        st.header("📊 PPA Optimization Metrics & Verification")

        # Metric Cards
        m_col1, m_col2, m_col3, m_col4 = st.columns(4)
        m_col1.metric(
            label="Total Cell Count",
            value=deltas["opt_cells"],
            delta=f"{deltas['cell_reduction_pct']:+.1f}%" if deltas["cell_reduction_pct"] != 0 else "0%",
            delta_color="inverse"
        )
        m_col2.metric(
            label="Estimated Area (GE)",
            value=f"{deltas['opt_area']} GE",
            delta=f"{deltas['area_reduction_pct']:+.1f}%" if deltas["area_reduction_pct"] != 0 else "0%",
            delta_color="inverse"
        )
        m_col3.metric(
            label="Logic Levels (Critical Path)",
            value=deltas["opt_depth"],
            delta=f"{deltas['depth_reduction_pct']:+.1f}%" if deltas["depth_reduction_pct"] != 0 else "0%",
            delta_color="inverse"
        )
        
        equiv_ok = deltas["equivalent"]
        m_col4.metric(
            label="Equivalence Verification",
            value="PASSED ✅" if equiv_ok else "FAILED ❌",
            delta=deltas["verification_method"]
        )

        # Plot PPA Bar Chart
        st.subheader("📈 PPA Comparison Chart")
        fig, ax = plt.subplots(figsize=(8, 3.2))
        categories = ["Total Cells", "Estimated Area (GE)", "Logic Depth"]
        baseline_vals = [deltas["orig_cells"], deltas["orig_area"], deltas["orig_depth"]]
        opt_vals = [deltas["opt_cells"], deltas["opt_area"], deltas["opt_depth"]]

        import numpy as np
        x = np.arange(len(categories))
        width = 0.35

        ax.bar(x - width/2, baseline_vals, width, label='Baseline RTL', color='#e74c3c')
        ax.bar(x + width/2, opt_vals, width, label='Optimized RTL', color='#2ecc71')

        ax.set_ylabel('Metrics Count')
        ax.set_title('Baseline vs Optimized RTL Comparison')
        ax.set_xticks(x)
        ax.set_xticklabels(categories)
        ax.legend()
        ax.grid(axis='y', linestyle='--', alpha=0.5)

        st.pyplot(fig)

        # Transformation Notes
        st.subheader("📝 Optimization Details")
        st.markdown(report.notes)
        st.info(f"Verification Details: {report.equiv_res.details}")

if __name__ == "__main__":
    main()
