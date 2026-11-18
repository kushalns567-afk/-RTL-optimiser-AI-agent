// Multiply-Accumulator Unit with constant scaling factor
module mac_unit (
    input  wire        clk,
    input  wire        rst_n,
    input  wire [7:0]  data_in,
    input  wire        valid_in,
    output reg  [15:0] acc_out
);

    wire [15:0] scaled_val;
    // Anti-pattern: Multiplying by constant 10 and 4 in combinational path
    assign scaled_val = (((data_in << 3) + (data_in << 1))) + ((data_in << 2));

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            acc_out <= 16'd0;
        end else if (valid_in) begin
            acc_out <= acc_out + scaled_val;
        end
    end

endmodule