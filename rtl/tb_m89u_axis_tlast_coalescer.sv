`timescale 1ns/1ps

module tb_m89u_axis_tlast_coalescer;
    reg clk = 0; always #2.4 clk = ~clk;
    reg resetn = 0;
    reg [3:0] descriptor_count = 0;
    reg [63:0] s_data = 0;
    reg [7:0] s_keep = 8'hff, s_strb = 8'hff;
    reg s_last = 0, s_valid = 0;
    wire s_ready;
    wire [63:0] m_data;
    wire [7:0] m_keep, m_strb;
    wire m_last, m_valid;
    reg m_ready = 0;
    integer cycle = 0, errors = 0, expected_remaining = 0;
    reg [63:0] next_data = 64'h1000, expected_data = 64'h1000;

    m89u_axis_tlast_coalescer dut(
        .aclk(clk), .aresetn(resetn), .descriptor_count(descriptor_count),
        .s_axis_tdata(s_data), .s_axis_tkeep(s_keep), .s_axis_tstrb(s_strb),
        .s_axis_tlast(s_last), .s_axis_tvalid(s_valid), .s_axis_tready(s_ready),
        .m_axis_tdata(m_data), .m_axis_tkeep(m_keep), .m_axis_tstrb(m_strb),
        .m_axis_tlast(m_last), .m_axis_tvalid(m_valid), .m_axis_tready(m_ready));

    always @(posedge clk) begin
        cycle <= cycle + 1;
        m_ready <= ((cycle % 7) != 2) && ((cycle % 11) != 5);
        if (resetn && m_valid && m_ready) begin
            if (m_data !== expected_data || m_keep !== 8'hff || m_strb !== 8'hff) begin
                $display("M89U_DATA_MISMATCH cycle=%0d", cycle); errors <= errors + 1;
            end
            if (m_last !== (expected_remaining == 1)) begin
                $display("M89U_TLAST_MISMATCH cycle=%0d remaining=%0d", cycle, expected_remaining);
                errors <= errors + 1;
            end
            expected_data <= expected_data + 1;
            expected_remaining <= expected_remaining - 1;
        end
    end

    task send_word(input reg last_word);
    begin
        @(negedge clk);
        s_data = next_data; s_last = last_word; s_valid = 1;
        do @(posedge clk); while (!s_ready);
        @(negedge clk);
        next_data = next_data + 1;
        s_valid = 0; s_last = 0;
    end
    endtask

    task send_chain(input integer count);
        integer d, w;
    begin
        descriptor_count = count[3:0];
        expected_remaining = count * 4;
        for (d = 0; d < count; d = d + 1)
            for (w = 0; w < 4; w = w + 1)
                send_word(w == 3);
        while (expected_remaining != 0) @(posedge clk);
        repeat (3) @(posedge clk);
    end
    endtask

    initial begin
        repeat (4) @(posedge clk); resetn = 1;
        send_chain(1); send_chain(2); send_chain(4); send_chain(10);
        if (errors == 0) $display("M89U_TLAST_COALESCER_BACKPRESSURE_SIM_PASS");
        else $display("M89U_TLAST_COALESCER_SIM_FAIL errors=%0d", errors);
        $finish(errors != 0);
    end
endmodule
