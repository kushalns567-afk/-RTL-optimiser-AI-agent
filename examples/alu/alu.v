// 8-bit ALU with duplicate adders across conditional branches
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
