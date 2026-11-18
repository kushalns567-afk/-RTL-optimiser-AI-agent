`timescale 1ns/1ps

module alu_tb;
    reg  [7:0] a, b, c;
    reg        mode;
    wire [8:0] result;

    alu uut (
        .a(a),
        .b(b),
        .c(c),
        .mode(mode),
        .result(result)
    );

    initial begin
        a = 8'd10; b = 8'd20; c = 8'd30;
        
        mode = 1; #10;
        if (result !== 9'd30) begin
            $display("[TESTBENCH FAILED] mode=1 expected 30, got %d", result);
            $finish(1);
        end

        mode = 0; #10;
        if (result !== 9'd40) begin
            $display("[TESTBENCH FAILED] mode=0 expected 40, got %d", result);
            $finish(1);
        end

        $display("[TESTBENCH PASS] alu functional verification successful!");
        $finish(0);
    end
endmodule
