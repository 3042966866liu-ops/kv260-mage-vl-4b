`timescale 1ns/1ps

module m89u_axis_tlast_coalescer #(
    parameter integer DATA_WIDTH = 64
) (
    input  wire                  aclk,
    input  wire                  aresetn,
    input  wire [3:0]            descriptor_count,
    input  wire [DATA_WIDTH-1:0] s_axis_tdata,
    input  wire [DATA_WIDTH/8-1:0] s_axis_tkeep,
    input  wire [DATA_WIDTH/8-1:0] s_axis_tstrb,
    input  wire                  s_axis_tlast,
    input  wire                  s_axis_tvalid,
    output wire                  s_axis_tready,
    output wire [DATA_WIDTH-1:0] m_axis_tdata,
    output wire [DATA_WIDTH/8-1:0] m_axis_tkeep,
    output wire [DATA_WIDTH/8-1:0] m_axis_tstrb,
    output wire                  m_axis_tlast,
    output wire                  m_axis_tvalid,
    input  wire                  m_axis_tready
);
    reg [3:0] completed_packets;
    wire [3:0] effective_count = (descriptor_count == 0) ? 4'd1 : descriptor_count;
    wire final_packet = (completed_packets + 4'd1 >= effective_count);
    wire transfer = s_axis_tvalid && s_axis_tready;

    assign s_axis_tready = m_axis_tready;
    assign m_axis_tvalid = s_axis_tvalid;
    assign m_axis_tdata  = s_axis_tdata;
    assign m_axis_tkeep  = s_axis_tkeep;
    assign m_axis_tstrb  = s_axis_tstrb;
    assign m_axis_tlast  = s_axis_tlast && final_packet;

    always @(posedge aclk) begin
        if (!aresetn) begin
            completed_packets <= 4'd0;
        end else if (transfer && s_axis_tlast) begin
            if (final_packet)
                completed_packets <= 4'd0;
            else
                completed_packets <= completed_packets + 4'd1;
        end
    end
endmodule
