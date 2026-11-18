`timescale 1ns/1ps

module mac_unit_tb;
    reg         clk;
    reg         rst_n;
    reg  [7:0]  data_in;
    reg         valid_in;
    wire [15:0] acc_out;

    mac_unit uut (
        .clk(clk),
        .rst_n(rst_n),
        .data_in(data_in),
        .valid_in(valid_in),
        .acc_out(acc_out)
    );

    always #5 clk = ~clk;

    initial begin
        clk = 0;
        rst_n = 0;
        data_in = 0;
        valid_in = 0;

        #15 rst_n = 1;

        // Test vector 1: data = 2. Expected scaled = 2*10 + 2*4 = 28. acc = 28
        #10 data_in = 8'd2; valid_in = 1;
        #10 data_in = 8'd3; valid_in = 1; // Expected scaled = 3*14 = 42. acc = 28 + 42 = 70
        #10 data_in = 8'd5; valid_in = 1; // Expected scaled = 5*14 = 70. acc = 70 + 70 = 140
        #10 valid_in = 0;

        #15;
        if (acc_out === 16'd140) begin
            $display("[TESTBENCH PASS] mac_unit accumulated correctly: %d", acc_out);
        end else begin
            $display("[TESTBENCH FAILED] Expected 140, got %d", acc_out);
            $finish(1);
        end

        $finish(0);
    end
endmodule
