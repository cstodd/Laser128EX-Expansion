// Testbench: Laser 128EX expansion-RAM bus (Tech Ref Fig. 11-19) driving the card model:
// CPLD + 74AHCT574 row register + 74AHCT573 column latch + 74AHCT245 + MAX693A CE gate +
// 2 x AS6C4008 (with datasheet read/write timing checks).
//
//   iverilog -g2012 -o tb cpld/laser128_ramcard.v cpld/tb_laser128_ramcard.v && vvp tb
//
// Laser timing below is read off Fig. 11-19; the figure is not drawn to scale, so edges are
// approximate. The run reports the read-data margin at the CPU sample point for each speed.
`timescale 1ns/100ps

module tb;
    // ---------------------------------------------------------------- part delays (ns, max)
    parameter real T_CPLD = 10.0;   // ATF1504AS-10 pin-to-pin (7.5 for -7)
    localparam real T_574  = 9.0;    // 74AHCT574 clk->Q
    localparam real T_573  = 9.0;    // 74AHCT573 D->Q / LE->Q
    localparam real T_245  = 8.0;    // 74AHCT245 tpd / tPZ / tPHZ
    localparam real T_CE   = 10.0;   // MAX693A CE IN -> CE OUT
    parameter real T_AA = 55, T_ACE = 55, T_OE = 30, T_OH = 10;    // AS6C4008-55
    localparam real T_DW = 25, T_WP = 45;
    localparam real T_DSU = 10.0;    // 65C02 read data setup before CPUP0 fall

    // ---------------------------------------------------------------- Laser-side signals
    reg  [8:0] era = 0;
    reg  rasb_n = 1, e1moe_n = 1, rwr_n = 1, memrd = 1, pwr_rst_n = 1;
    reg  [4:1] ecas_n = 4'hF;
    reg  [7:0] cpu_d = 0; reg cpu_drive = 0;
    wire [7:0] d;                                   // Laser data bus (J1)
    assign d = cpu_drive ? cpu_d : 8'bz;

    // ---------------------------------------------------------------- card
    wire [7:0] xd;
    wire rowclk, col_le, ma8, ma17, ma18, ram_ce_n, oe0_n, oe1_n, we0_n, we1_n, buf_oe_n, dbg0;
    tri1 sda, scl;                                  // 4.7k pull-ups
    laser128_ramcard dut(.rasb_n(rasb_n), .ecas1_n(ecas_n[1]), .ecas2_n(ecas_n[2]),
        .ecas3_n(ecas_n[3]), .ecas4_n(ecas_n[4]), .e1moe_n(e1moe_n), .rwr_n(rwr_n), .era8(era[8]),
        .memrd(memrd), .pwr_rst_n(pwr_rst_n), .xd(xd), .rowclk(rowclk), .col_le(col_le),
        .ma8(ma8), .ma17(ma17), .ma18(ma18), .ram_ce_n(ram_ce_n), .oe0_n(oe0_n), .oe1_n(oe1_n),
        .we0_n(we0_n), .we1_n(we1_n), .buf_oe_n(buf_oe_n), .sda(sda), .scl(scl), .dbg0(dbg0));

    // CPLD output delays
    wire #(T_CPLD) rowclk_d = rowclk, col_le_d = col_le, ma8_d = ma8, ma17_d = ma17, ma18_d = ma18;
    wire #(T_CPLD) ce_d = ram_ce_n, oe0_d = oe0_n, oe1_d = oe1_n, we0_d = we0_n, we1_d = we1_n;
    wire #(T_CPLD) boe_d = buf_oe_n;

    reg [7:0] row_q = 0, col_l = 0;
    always @(posedge rowclk_d) row_q <= #(T_574) era[7:0];
    always @* if (col_le_d) col_l = era[7:0];
    wire [7:0] col_q; assign #(T_573) col_q = col_l;
    wire ceo_n; assign #(T_CE) ceo_n = ce_d;

    wire [18:0] ma = {ma18_d, ma17_d, row_q, ma8_d, col_q};

    // 74AHCT245: A = xd (card), B = d (Laser); DIR = MEMRD (high: A -> B)
    assign #(T_245) d  = (!boe_d &&  memrd) ? xd : 8'bz;
    assign #(T_245) xd = (!boe_d && !memrd) ? d  : 8'bz;

    sram #(.T_AA(T_AA), .T_ACE(T_ACE), .T_OE(T_OE), .T_OH(T_OH), .T_DW(T_DW), .T_WP(T_WP))
        u5(.a(ma), .dq(xd), .ce_n(ceo_n), .oe_n(oe0_d), .we_n(we0_d)),
        u6(.a(ma), .dq(xd), .ce_n(ceo_n), .oe_n(oe1_d), .we_n(we1_d));

    // ---------------------------------------------------------------- bus cycle generator
    integer errors = 0;
    real    min_margin_fast = 1e9, min_margin_slow = 1e9;
    real    t_d;  always @(d) t_d = $realtime;

    // UDC mapping (any consistent mapping works): bank = A19:18, row = A17:9, col = A8:0
    task automatic cycle(input bit fast, input bit wr, input [19:0] a, input [7:0] wd,
                         output [7:0] rd, input bit refresh);
        real t0, ph, s;
        begin
            ph = fast ? 140 : 489;
            t0 = $realtime;
            era = a[17:9];
            #5  e1moe_n = 0; if (wr) begin rwr_n = 0; memrd = 0; end
            if (wr) begin cpu_d = wd; cpu_drive <= #(fast ? 15 : 40) 1; end  // 65C02 write data
            if (fast) begin
                #26 rasb_n = 0;                 // +31
                #22 era = a[8:0];               // +53 column (AX low)
                #7  cas_fall(a[19:18]);         // +60
                #(ph - 60 - T_DSU) s = $realtime;                 // CPU samples read data
                rd = d;
                if (!wr) chk_margin(fast, s);
                #(T_DSU) ;                      // +140 CPUP0 fall
                #2  e1moe_n = 1;
                #6  rwr_n = 1; memrd = 1;
                #2  cpu_drive = 0;              // CPU write hold ends at +150
                #26 rasb_n = 1;                 // +176
                #14 ecas_n = 4'hF;              // +190
                #3  era = 9'h1AB;               // next row
                #86 ;                           // cycle 279 ns
            end else begin
                #55 rasb_n = 0;                 // +60
                #50 era = a[8:0];               // +110
                #40 cas_fall(a[19:18]);         // +150
                #310 rasb_n = 1;                // +460  (RAS ends BEFORE CAS: Fig. 11-19a)
                #(ph - 460 - T_DSU) s = $realtime;
                rd = d;
                if (!wr) chk_margin(fast, s);
                #(T_DSU) ;                      // +489
                ecas_n = 4'hF; e1moe_n = 1;
                #6  rwr_n = 1; memrd = 1;
                #4  cpu_drive = 0;
                if (refresh) begin              // RAS-only refresh in CPUP0 low (Fig. 11-19a)
                    #21 era = $urandom;         // +520
                    #40 rasb_n = 0;             // +560
                    #340 rasb_n = 1;            // +900
                    #78 ;
                end else #479 ;
            end
        end
    endtask

    task automatic cas_fall(input [1:0] b);
        case (b) 2'd0: ecas_n[1] = 0; 2'd1: ecas_n[2] = 0; 2'd2: ecas_n[3] = 0; default: ecas_n[4] = 0; endcase
    endtask

    task automatic chk_margin(input bit fast, input real s);
        real m;
        begin
            m = s - t_d;
            if (fast) begin if (m < min_margin_fast) min_margin_fast = m; end
            else      begin if (m < min_margin_slow) min_margin_slow = m; end
        end
    endtask

    task automatic wr8(input bit fast, input [19:0] a, input [7:0] v);
        reg [7:0] dummy; begin cycle(fast, 1, a, v, dummy, 1); end
    endtask
    task automatic rd8(input bit fast, input [19:0] a, output [7:0] v);
        begin cycle(fast, 0, a, 0, v, 1); end
    endtask
    task automatic expect8(input bit fast, input [19:0] a, input [7:0] want, input string what);
        reg [7:0] got;
        begin
            rd8(fast, a, got);
            if (got !== want) begin
                errors++;
                $display("FAIL %s: addr %05h fast=%0d got %02h want %02h  t=%0t", what, a, fast, got, want, $time);
            end
        end
    endtask

    // ---------------------------------------------------------------- tests
    localparam [63:0] KEY = 64'h8E_27_D1_5B_3F_C4_72_A9;
    reg [7:0]  shadow [0:1048575];
    reg [19:0] addrs [0:399];
    reg [7:0]  v;
    integer i, k;

    initial begin
        #10 pwr_rst_n = 0; #190 pwr_rst_n = 1;  // MAX693A /RESET pulse at power-up

        // 1. random writes / reads at both speeds, all four banks
        for (i = 0; i < 400; i++) begin
            addrs[i] = $urandom & 20'hFFFFF;
            v = $urandom;
            shadow[addrs[i]] = v;
            wr8(i & 1, addrs[i], v);
        end
        for (i = 0; i < 400; i++) expect8(i % 3 == 0, addrs[i], shadow[addrs[i]], "ram readback");

        // 2. near-miss key (7 good bytes + bad) must not unlock
        for (k = 0; k < 7; k++) wr8(1, 20'h10000 + k, KEY[63-8*k -: 8]);
        wr8(1, 20'h10007, 8'h00);
        if (dbg0) begin errors++; $display("FAIL: unlocked by a wrong 8th byte"); end

        // 3. correct key -> RTC mode
        for (k = 0; k < 8; k++) wr8(1, 20'h20000 + k, KEY[63-8*k -: 8]);
        if (!dbg0) begin errors++; $display("FAIL: key did not unlock"); end

        // 4. RTC port: in RTC mode writes must not touch RAM and reads return {SIG,scl,sda}
        wr8(1, addrs[0], 8'h01);                // pull SDA low (addr = a location holding data)
        #1 if (sda !== 1'b0 || scl !== 1'b1) begin errors++; $display("FAIL: SDA/SCL %b%b after 01", sda, scl); end
        expect8(1, addrs[5], {6'b101101, 1'b1, 1'b0}, "rtc read sda low");
        wr8(0, addrs[1], 8'h02);                // SCL low, SDA released (1 MHz cycle)
        expect8(0, addrs[6], {6'b101101, 1'b0, 1'b1}, "rtc read scl low");
        wr8(1, addrs[2], 8'h80);                // lock
        if (dbg0) begin errors++; $display("FAIL: lock did not exit RTC mode"); end
        if (sda !== 1'b1 || scl !== 1'b1) begin errors++; $display("FAIL: bus not released on lock"); end

        // 5. RAM untouched by RTC-mode accesses
        for (i = 0; i < 8; i++) expect8(1, addrs[i], shadow[addrs[i]], "ram after rtc");

        // 6. power-on reset clears RTC mode
        for (k = 0; k < 8; k++) wr8(0, 20'h30000 + k, KEY[63-8*k -: 8]);
        if (!dbg0) begin errors++; $display("FAIL: key did not unlock at 1 MHz"); end
        pwr_rst_n = 0; #50 pwr_rst_n = 1;
        if (dbg0) begin errors++; $display("FAIL: reset did not clear RTC mode"); end

        $display("read-data margin at CPU sample point: 3.6 MHz %0.1f ns, 1 MHz %0.1f ns",
                 min_margin_fast, min_margin_slow);
        $display("SRAM timing violations: %0d", u5.viol + u6.viol);
        errors += u5.viol + u6.viol;
        if (errors == 0) $display("PASS");
        else             $display("FAILED with %0d errors", errors);
        $finish;
    end
endmodule

// AS6C4008 behavioural model with access-time tracking and write-timing checks
module sram #(parameter real T_AA = 55, T_ACE = 55, T_OE = 30, T_OH = 10, T_DW = 25, T_WP = 45)
             (input [18:0] a, inout [7:0] dq, input ce_n, oe_n, we_n);
    reg  [7:0] mem [0:524287];
    real t_a = 0, t_ce = 0, t_oe = 0, t_we = 0, t_dq = 0;
    integer viol = 0;
    reg  [7:0] q = 8'hxx;
    wire out_en = !ce_n && !oe_n && we_n;
    assign dq = out_en ? q : 8'bz;

    always @(a)            t_a  = $realtime;
    always @(negedge ce_n) t_ce = $realtime;
    always @(negedge oe_n) t_oe = $realtime;
    always @(negedge we_n) t_we = $realtime;
    always @(dq)           t_dq = $realtime;

    // read data valid only once every access time has elapsed (1 ns resolution)
    always #1 begin
        if (out_en && $realtime >= t_a + T_AA && $realtime >= t_ce + T_ACE && $realtime >= t_oe + T_OE)
            q = mem[a];
        else if ($realtime >= t_a + T_OH || !out_en)
            q = 8'hxx;
    end

    // write ends on the first of WE# or CE# rising; check pulse width and data setup
    always @(posedge we_n or posedge ce_n) begin
        if (!(we_n && ce_n) || $realtime == t_we) ; // no-op
        if ($realtime - t_we < 1e6 && (t_we > t_ce || 1)) begin end
    end
    reg in_write = 0;
    always @(negedge we_n) if (!ce_n) in_write = 1;
    always @(negedge ce_n) if (!we_n) in_write = 1;
    always @(posedge we_n or posedge ce_n) if (in_write) begin
        in_write = 0;
        if ($realtime - t_we < T_WP) begin viol++; $display("SRAM %m: tWP %0.1f < %0.1f at %0t", $realtime - t_we, T_WP, $time); end
        if ($realtime - t_dq < T_DW) begin viol++; $display("SRAM %m: tDW %0.1f < %0.1f at %0t", $realtime - t_dq, T_DW, $time); end
        if (^dq === 1'bx)           begin viol++; $display("SRAM %m: data X/Z at end of write %0t", $time); end
        else mem[a] = dq;
    end
endmodule
