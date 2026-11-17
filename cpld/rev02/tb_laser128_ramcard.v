// Testbench: Laser 128EX expansion-RAM bus (Tech Ref Fig. 11-19) driving the card model:
// CPLD + 74AHCT574 row register + 74AHCT573 column latch + 74AHCT245 + MAX693A CE gate +
// 2 x AS6C4008 (with datasheet read/write timing checks).
//
//   iverilog -g2012 -o tb cpld/laser128_ramcard.v cpld/tb_laser128_ramcard.v && vvp tb
//
// Laser timing: 1 MHz edges are read off Fig. 11-19 (not to scale). Fast-cycle strobes are placed
// at the MMU delay-line tap times (D60/D90/D120, Tech Ref sec. 11.4) - an inference, to be
// confirmed with a scope. The run reports the read-data margin at the CPU sample point for each speed.
`timescale 1ns/100ps

module tb;
    // ---------------------------------------------------------------- part delays (ns, max)
    parameter real T_CPLD = 10.0;   // ATF1504AS-10 pin-to-pin (7.5 for -7)
    parameter real PH_FAST = 264.0; // CPUP0 high in "fast" cycles. Expansion RAM never runs faster than 2.3 MHz
                                    // (Tech Ref App. A; scoped: same timing at the 2.3 and 3.6 settings).
                                    // Scope, 128EX, Nov 2026: /E1MOE low 266-270 ns in fast cycles.
    // Strobe timing scoped on a 128EX (J13, STA/LDA $C0D3 loops, Nov 2026), relative to /E1MOE falling:
    //   fast: /RWR falls up to 4.72 ns AFTER /E1MOE (MMU delay line); /RASB falls 79.6-82.8 ns after,
    //         low >= 181 ns, rises just before /E1MOE rises
    //   slow: /RWR falls 8.7-14 ns BEFORE /E1MOE; /RASB falls up to 34.4 ns after, low >= 352 ns, rises ~90 ns
    //         before /E1MOE rises
    // The model uses the worse side of each: /RWR 6 ns late (fast), /RASB at the latest measured time.
    parameter real T_RWR_LAG = 6.0;   // fast write: /RWR falls this long after /E1MOE
    parameter real T_RAS_FAST = 83.0; // /E1MOE fall -> /RASB fall, fast
    parameter real T_RAS_SLOW = 35.0; // /E1MOE fall -> /RASB fall, slow
    // /E1MOE fall -> /ECAS fall: scoped 174 ns worst case fast, ~212 ns at 1 MHz (Nov 2026). /ECAS rises ~27 ns
    // after /E1MOE in fast cycles and just before it at 1 MHz. With 55 ns SRAM a bank-change read then has only
    // ~1-2 ns of worst-case margin here (fails from T_CAS_FAST ~176); 45 ns SRAM (-Ptb.T_AA=45 -Ptb.T_ACE=45)
    // passes to ~184. See cpld/rev02/README.md.
    parameter real T_CAS_FAST = 174.0, T_CAS_SLOW = 212.0;
    // /E1MOE fall -> column address settled on ERA: scoped ~148 ns fast (row set ~90 ns BEFORE /E1MOE falls).
    parameter real T_COL_FAST = 150.0;
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
    wire rtc_cs_n, rtc_sclk;
    tri1 rtc_dio;                                   // shared DIN/DOUT (weak pull-up so a deselected read is defined)
    laser128_ramcard dut(.rasb_n(rasb_n), .ecas1_n(ecas_n[1]), .ecas2_n(ecas_n[2]),
        .ecas3_n(ecas_n[3]), .ecas4_n(ecas_n[4]), .e1moe_n(e1moe_n), .rwr_n(rwr_n), .era8(era[8]),
        .pwr_rst_n(pwr_rst_n), .xd(xd), .rowclk(rowclk), .col_le(col_le),
        .ma8(ma8), .ma17(ma17), .ma18(ma18), .ram_ce_n(ram_ce_n), .oe0_n(oe0_n), .oe1_n(oe1_n),
        .we0_n(we0_n), .we1_n(we1_n), .buf_oe_n(buf_oe_n), .rtc_cs_n(rtc_cs_n), .rtc_sclk(rtc_sclk), .rtc_dio(rtc_dio), .dbg0(dbg0));
    ds3234 rtc(.cs_n(rtc_cs_n), .sclk(rtc_sclk), .dio(rtc_dio));

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
            ph = fast ? PH_FAST : 489;
            t0 = $realtime;
            era = a[17:9];
            // Slow cycles: /RWR (from the 65C02's R/W) is set before /E1MOE falls. Fast cycles: the MMU's delay
            // line drops /RWR a few ns AFTER /E1MOE (scoped), so a write starts with a short "/E1MOE low,
            // /RWR high" window that looks like a read; the RTC port must not clock SCLK on it.
            // MEMRD ('245 direction) scoped: falls 22-26 ns before /E1MOE on writes at both speeds, rises ~15-20 ns
            // after /E1MOE rises, stays high on reads. Modelled 5 ns before (pessimistic) and 15 ns after.
            if (wr) memrd = 0;
            if (wr && !fast) rwr_n = 0;
            #5  e1moe_n = 0;
            if (wr && fast) rwr_n <= #(T_RWR_LAG) 0;
            // 65C02 write data. Scoped (3.6 MHz): D0 crosses the threshold as /E1MOE falls and is fully settled ~25 ns
            // later; it then stays valid ~515 ns past /E1MOE rising. Modelled: valid at +25 (fast), held only 8 ns.
            if (wr) begin cpu_d = wd; cpu_drive <= #(fast ? 25 : 40) 1; end
            if (fast) begin
                #(T_RAS_FAST) rasb_n = 0;        // +88  (scoped 79.6-82.8 ns after /E1MOE)
                #(T_COL_FAST - T_RAS_FAST) era = a[8:0];   // column (scoped: settled ~148 ns after /E1MOE)
                #(T_CAS_FAST - T_COL_FAST) cas_fall(a[19:18]);
                #(ph - T_CAS_FAST - 5 - T_DSU) s = $realtime;   // CPU samples read data
                rd = d;
                if (!wr) chk_margin(fast, s);
                #(T_DSU) ;                      // +ph: CPUP0 fall
                rasb_n = 1;                     // scoped: /RASB rises just before /E1MOE
                #2  e1moe_n = 1;
                #6  rwr_n = 1;
                #2  cpu_drive = 0;              // CPU write hold
                #7  memrd = 1;
                #7  ecas_n = 4'hF;
                #3  era = 9'h1AB;               // next row
                #(435 - ph - 27) ;              // 2.3 MHz cycle: 435 ns
            end else begin
                #(T_RAS_SLOW) rasb_n = 0;        // +40
                #50 era = a[8:0];
                #(T_CAS_SLOW - T_RAS_SLOW - 50) cas_fall(a[19:18]);
                #(385 - 5 - T_CAS_SLOW) rasb_n = 1;                // +385  (RAS ends BEFORE CAS: Fig. 11-19a; scoped ~90 ns before /E1MOE)
                #(ph - 385 - T_DSU) s = $realtime;
                rd = d;
                if (!wr) chk_margin(fast, s);
                #(T_DSU) ;                      // +489
                ecas_n = 4'hF; e1moe_n = 1;
                #6  rwr_n = 1;
                #4  cpu_drive = 0;
                #5  memrd = 1;
                if (refresh) begin              // RAS-only refresh in CPUP0 low (Fig. 11-19a)
                    #16 era = $urandom;         // +520
                    #40 rasb_n = 0;             // +560
                    #340 rasb_n = 1;            // +900
                    #78 ;
                end else #474 ;
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

    // ---------------------------------------------------------------- SPI helpers (rev 0.2 RTC port)
    // control write: D6 = 1, D0 = chip select, D1 = drive DIO. Data bit: write D0, then a read clocks it.
    integer spi_a = 0;
    task automatic spi_sel(input bit fast, input bit cs, input bit oe);
        begin wr8(fast, addrs[spi_a % 8], {6'b010000, oe, cs}); spi_a++;
              if (!cs) #400; end   // DS3234 CS inactive >= 400 ns: real code always has instructions in between
    endtask
    task automatic spi_tx(input bit fast, input [7:0] v);
        integer i; reg [7:0] dummy;
        for (i = 7; i >= 0; i--) begin
            wr8(fast, addrs[spi_a % 8], {7'b0, v[i]}); spi_a++;
            rd8(fast, addrs[spi_a % 8], dummy); spi_a++;
        end
    endtask
    task automatic spi_rx(input bit fast, output [7:0] v);
        integer i; reg [7:0] r;
        for (i = 7; i >= 0; i--) begin
            rd8(fast, addrs[spi_a % 8], r); spi_a++;
            v[i] = r[0];
        end
    endtask

    // ---------------------------------------------------------------- tests
    localparam [63:0] KEY = 64'h8E_27_D1_5B_3F_C4_72_A9;
    reg [7:0]  shadow [0:1048575];
    reg [19:0] addrs [0:399];
    reg [7:0]  v;
    integer i, k;

    // RAM-mode write to a random address in any of the four banks (the real driver writes the key at
    // whatever the slinky address happens to be). The shadow copy is kept up to date.
    task automatic wram(input bit fast, input [7:0] val);
        reg [19:0] a;
        begin a = $urandom & 20'hFFFFF; shadow[a] = val; wr8(fast, a, val); end
    endtask

    // Quiet-bus check: once /E1MOE has been high for 30 ns (CPLD delay plus margin), SRAM CE and the
    // '245 enable must both be off. A '245 left enabled would drive the Laser's data bus during
    // other devices' read cycles, which the card-cycle tests alone can't see.
    // (e1hi is set by the edge events themselves, so the check can't race the timestamp update)
    real t_e1hi = 0; integer quiet_viol = 0; reg quiet_seen = 0, e1hi = 1;
    always @(posedge e1moe_n) begin t_e1hi = $realtime; quiet_seen = 0; e1hi = 1; end
    always @(negedge e1moe_n) e1hi = 0;
    always #1 if (pwr_rst_n === 1'b1 && e1hi && $realtime > t_e1hi + 30 && !quiet_seen
                  && (ce_d !== 1'b1 || boe_d !== 1'b1)) begin
        quiet_seen = 1; quiet_viol++;
        if (quiet_viol <= 5) $display("FAIL quiet bus: /E1MOE high since %0.1f but CE=%b '245 /G=%b at %0.1f",
                                      t_e1hi, ce_d, boe_d, $realtime);
    end

    initial begin
        #10 pwr_rst_n = 0; #190 pwr_rst_n = 1;  // MAX693A /RESET pulse at power-up

        // 1. random writes / reads at both speeds, all four banks. Read back in a different order
        //    from the writes: A18 comes from a latch that holds the previous access's bank bit, so
        //    a fault there only shows when the preceding access differs between write and read.
        for (i = 0; i < 400; i++) begin
            addrs[i] = $urandom & 20'hFFFFF;
            v = $urandom;
            shadow[addrs[i]] = v;
            wr8(i & 1, addrs[i], v);
        end
        for (i = 0; i < 400; i++) begin
            k = (i * 7919 + 123) % 400;         // a permutation of 0..399
            expect8(i % 3 == 0, addrs[k], shadow[addrs[k]], "ram readback");
        end

        // 1b. bank aliasing: the same offset in all four banks holds four different values
        for (i = 0; i < 64; i++) begin : alias_test
            reg [17:0] off; integer b;
            off = $urandom;
            for (b = 0; b < 4; b++) begin
                v = $urandom; shadow[{b[1:0], off}] = v; wr8(i & 1, {b[1:0], off}, v);
            end
            for (b = 0; b < 4; b++) begin
                k = (b * 3 + i) % 4;            // read the four banks in a rotating order
                expect8(!(i & 1), {k[1:0], off}, shadow[{k[1:0], off}], "bank alias");
            end
        end

        // 2. near-miss key (7 good bytes + bad) must not unlock
        for (k = 0; k < 7; k++) wram(1, KEY[63-8*k -: 8]);
        wram(1, 8'h00);
        if (dbg0) begin errors++; $display("FAIL: unlocked by a wrong 8th byte"); end

        // 3. correct key -> RTC mode
        for (k = 0; k < 8; k++) wram(1, KEY[63-8*k -: 8]);
        if (!dbg0) begin errors++; $display("FAIL: key did not unlock"); end

        // 4. RTC port (SPI to the DS3234). All accesses use addresses holding RAM data (section 5 checks
        //    they were not touched). Deselected read: signature, CS = 0, DIO pulled up.
        expect8(1, addrs[5], {6'b101101, 1'b0, 1'b1}, "rtc signature (deselected)");
        if (rtc.edges != 0) begin errors++; $display("FAIL: SCLK moved while deselected"); end
        // burst read of 00h-06h at 3.6 MHz, then at 1 MHz
        for (k = 0; k < 2; k++) begin : rd_burst
            reg [7:0] b; integer r;
            spi_sel(k == 0, 1, 1); spi_tx(k == 0, 8'h00); spi_sel(k == 0, 1, 0);
            for (r = 0; r < 7; r++) begin
                spi_rx(k == 0, b);
                if (b !== rtc.regs[r]) begin errors++;
                    $display("FAIL: SPI read reg %0d fast=%0d got %02h want %02h", r, k == 0, b, rtc.regs[r]); end
            end
            spi_sel(k == 0, 0, 0);
        end
        // write minutes (01h) = 42h, read it back
        spi_sel(1, 1, 1); spi_tx(1, 8'h81); spi_tx(1, 8'h42); spi_sel(1, 0, 0);
        if (rtc.regs[1] !== 8'h42) begin errors++; $display("FAIL: SPI write minutes: %02h", rtc.regs[1]); end
        spi_sel(0, 1, 1); spi_tx(0, 8'h01); spi_sel(0, 1, 0);
        begin : rd_back reg [7:0] b; spi_rx(0, b);
            if (b !== 8'h42) begin errors++; $display("FAIL: SPI read-back minutes: %02h", b); end end
        spi_sel(0, 0, 0);
        wr8(1, addrs[2], 8'h80);                // lock
        if (dbg0) begin errors++; $display("FAIL: lock did not exit RTC mode"); end
        #1 if (rtc_cs_n !== 1'b1 || rtc_sclk !== 1'b1) begin errors++; $display("FAIL: SPI not idle after lock"); end

        // 5. RAM untouched by RTC-mode accesses
        for (i = 0; i < 8; i++) expect8(1, addrs[i], shadow[addrs[i]], "ram after rtc");

        // 6. power-on reset clears RTC mode
        for (k = 0; k < 8; k++) wram(0, KEY[63-8*k -: 8]);
        if (!dbg0) begin errors++; $display("FAIL: key did not unlock at 1 MHz"); end
        pwr_rst_n = 0; #50 pwr_rst_n = 1;
        if (dbg0) begin errors++; $display("FAIL: reset did not clear RTC mode"); end

        // 7. key matcher, exhaustive: every state s (0-7 bytes matched) x every byte value. The
        //    state after the byte is identified by finding which key tails KEY[j..7] unlock: the tail
        //    j = expected next state must, and so must j = 0 (the whole key, which restarts the matcher
        //    from any state); no other may. Key bytes are distinct, so only the right state accepts a
        //    given tail.
        //    Catches a wrong or missing literal in any key-matcher product term. Skip with +quick.
        if (!$test$plusargs("quick")) begin : exhaustive
            integer s, j, nxt, n7;
            reg [7:0] kb [0:7];
            n7 = 0;
            for (k = 0; k < 8; k++) kb[k] = KEY[63-8*k -: 8];
            for (s = 0; s < 8; s++)
                for (i = 0; i < 256; i++) begin
                    nxt = (i == kb[s]) ? s + 1 : (i == kb[0]) ? 1 : 0;
                    for (j = 0; j < ((nxt == 8) ? 1 : 8); j++) begin
                        pwr_rst_n = 0; #20 pwr_rst_n = 1;
                        for (k = 0; k < s; k++) wram(1, kb[k]);
                        wram(1, i[7:0]);
                        if (nxt < 8) for (k = j; k < 8; k++) wram(1, kb[k]);
                        if (dbg0 !== (nxt == 8 || j == nxt || j == 0)) begin
                            errors++; n7++;
                            if (n7 <= 5) $display("FAIL key matcher: state %0d byte %02h tail %0d -> rtc_mode %b, want %b",
                                                  s, i[7:0], j, dbg0, (nxt == 8 || j == nxt || j == 0));
                        end
                    end
                end
            pwr_rst_n = 0; #20 pwr_rst_n = 1;
            $display("key matcher exhaustive test: %0d errors", n7);
        end

        $display("read-data margin at CPU sample point: fast cycles %0.1f ns, 1 MHz %0.1f ns",
                 min_margin_fast, min_margin_slow);
        $display("SRAM timing violations: %0d", u5.viol + u6.viol);
        $display("quiet-bus violations: %0d", quiet_viol);
        $display("DS3234 SPI timing violations: %0d, DIO contention: %0d, bytes read: %0d", rtc.viol, rtc.fight, rtc.nread);
        errors += u5.viol + u6.viol + quiet_viol + rtc.viol + rtc.fight;
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

// DS3234 SPI model (mode 3: SCLK idles high when CS falls). Registers 00h-06h only. Checks the datasheet
// timing that matters for this interface; DOUT changes tCDD = 80 ns after SCLK falls.
module ds3234(input cs_n, input sclk, inout dio);
    reg [7:0] regs [0:7];
    integer viol = 0, fight = 0, edges = 0, nread = 0;
    reg [7:0] sh, addr; integer nbit; reg addr_done, rmode, dout_en, dout;
    real t_fall = -1e9, t_rise = -1e9, t_csf = -1e9, t_csr = -1e9, t_d = 0;
    assign dio = dout_en ? dout : 1'bz;
    initial begin
        regs[0] = 8'h33; regs[1] = 8'h47; regs[2] = 8'h21; regs[3] = 8'h01;
        regs[4] = 8'h15; regs[5] = 8'h11; regs[6] = 8'h26; regs[7] = 8'h00;
        dout_en = 0; dout = 0;
    end
    always @(dio) begin t_d = $realtime; if (dio === 1'bx) begin fight++; if (fight <= 3) $display("DS3234: DIO contention at %0t", $time); end end
    task automatic v(input string s); begin viol++; if (viol <= 5) $display("DS3234 timing: %s at %0t", s, $time); end endtask
    always @(negedge cs_n) begin
        t_csf = $realtime; nbit = 0; addr_done = 0; rmode = 0; dout_en = 0;
        if (sclk !== 1'b1) v("SCLK not high at CS fall (mode 3)");
        if ($realtime - t_csr < 400) v("CS inactive time < 400 ns");
    end
    always @(posedge cs_n) begin t_csr = $realtime; dout_en = 0;
        if ($realtime - t_rise < 100) v("SCLK to CS hold < 100 ns"); end
    always @(negedge sclk) if (!cs_n) begin
        edges++; t_fall = $realtime;
        if ($realtime - t_csf < 400) v("CS to SCLK setup < 400 ns");
        if ($realtime - t_rise < 110) v("SCLK high time < 110 ns");
        if (addr_done && rmode) begin
            dout_en <= #80 1;
            dout <= #80 regs[addr[2:0]][7 - (nbit % 8)];
        end
    end else edges++;
    always @(posedge sclk) if (!cs_n) begin
        t_rise = $realtime;
        if ($realtime - t_fall < 110) v("SCLK low time < 110 ns");
        if (!rmode && $realtime - t_d < 30) v("DIN setup < 30 ns");
        if (!addr_done) begin
            sh = {sh[6:0], dio}; nbit++;
            if (nbit == 8) begin addr = sh; addr_done = 1; rmode = !sh[7]; addr[7] = 0; nbit = 0; end
        end else if (rmode) begin
            nbit++;
            if (nbit % 8 == 0) begin addr = addr + 1; nread++; end
        end else begin
            sh = {sh[6:0], dio}; nbit++;
            if (nbit % 8 == 0) begin regs[addr[2:0]] = sh; addr = addr + 1; end
        end
    end
    // DIN hold: DIO must not change within 30 ns after a rising edge while writing
    always @(dio) if (!cs_n && !rmode && t_rise > 0 && $realtime - t_rise < 30) v("DIN hold < 30 ns");
endmodule
