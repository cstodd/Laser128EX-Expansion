// Laser 128 / 128EX battery-backed SRAM + RTC card: CPLD logic
// Target: ATF1504AS-10JU44 / -7JX44 (PLCC-44). Pin numbers in comments match
// hardware/README.md and tools/gen_sch.py.
//
// The Laser motherboard holds the slinky address register ($C0D0-$C0D2) and drives this card
// as if it were 4 x 256K DRAM: multiplexed ERA0-8, /RASB, /ECAS1-4, /RWR, MEMRD, /E1MOE.
// This CPLD turns that into SRAM cycles:
//   * ROWCLK = /RASB fall   -> external 74AHCT574 captures row ERA0-7 (MA9-16); ERA8 -> MA17 here
//   * COL_LE = no /ECAS low -> external 74AHCT573 is transparent until the first /ECASn fall,
//     then holds column ERA0-7 (MA0-7). ERA8 -> MA8 is registered here on that same edge.
//   * bank = which /ECASn fired: bank[0] -> MA18, bank[1] selects U5 (0) / U6 (1)
//   * RAS-only refresh (no /ECAS) never touches the SRAM
//   * 128EX timing (Tech Ref Fig. 11-19): /E1MOE rises at the CPUP0 fall while /RASB,
//     /ECAS and /RWR are still low, so every strobe is qualified by /E1MOE: writes end
//     early (on /E1MOE rise), and reads are held until /E1MOE rises.
//
// RTC port (DS3231 on SDA/SCL): hidden behind an 8-byte unlock key so the full 1 MB stays
// usable as a RAM disk. See docs/rtc-protocol.md.

module laser128_ramcard (
    // from the Laser (J1)
    input  wire       rasb_n,     // pin 2  (GCLK2)
    input  wire       ecas1_n,    // pin 1
    input  wire       ecas2_n,    // pin 44
    input  wire       ecas3_n,    // pin 4
    input  wire       ecas4_n,    // pin 5
    input  wire       e1moe_n,    // pin 43 (GCLK1)
    input  wire       rwr_n,      // pin 6
    input  wire       era8,       // pin 8
    input  wire       memrd,      // pin 39 (also wired straight to the '245 DIR)
    input  wire       pwr_rst_n,  // pin 40 (MAX693A /RESET)
    // card-side data bus (SRAM DQ, '245 A side)
    inout  wire [7:0] xd,         // pins 9 11 12 14 16 17 18 19
    // to the address registers / SRAM
    output wire       rowclk,     // pin 20
    output wire       col_le,     // pin 21 -> U3 74AHCT573 LE (high = transparent)
    output reg        ma8,        // pin 33 (column ERA8)
    output reg        ma17,       // pin 37 (row ERA8)
    output wire       ma18,       // pin 24 (bank bit 0)
    output wire       ram_ce_n,   // pin 25 -> MAX693A CE IN -> both SRAM CE#
    output wire       oe0_n,      // pin 26
    output wire       oe1_n,      // pin 27
    output wire       we0_n,      // pin 28
    output wire       we1_n,      // pin 29
    output wire       buf_oe_n,   // pin 31 -> 74HCT245 /G
    // RTC I2C, open-drain (external 4.7k pull-ups)
    inout  wire       sda,        // pin 34
    inout  wire       scl,        // pin 36
    output wire       dbg0        // pin 41 (J3)
);
    // ------------------------------------------------------------------ unlock key
    // Arbitrary, non-pattern bytes (avoid 00/FF/55/AA/E5 fill and RAM-test patterns).
    localparam [63:0] KEY = 64'h8E_27_D1_5B_3F_C4_72_A9;   // sent first byte first: 8E 27 D1 ...
    localparam [5:0]  SIGNATURE = 6'b101101;              // RTC-mode read: {SIGNATURE, scl, sda}

    // ------------------------------------------------------------------ address clocks
    wire cas_any = ~(ecas1_n & ecas2_n & ecas3_n & ecas4_n);
    assign rowclk = ~rasb_n;          // '574 captures on the rising edge = /RASB fall
    assign col_le = ~cas_any;         // '573 transparent until /ECAS falls, then holds

    always @(negedge rasb_n) ma17 <= era8;      // row bit 8
    // column bit 8: a flip-flop on the first /ECASn fall, not a transparent latch. A gated D
    // latch built from product terms needs a redundant consensus term to be glitch-free, and
    // fitters tend to minimise that term away. A flip-flop has no such hazard. MA8 is then valid
    // one CPLD delay after /ECAS - the same as MA18, which already sets the worst-case path.
    always @(posedge cas_any) ma8 <= era8;

    // bank: set/reset latches written out as the sum-of-products the macrocell will implement,
    // Q = S | (Q & ~R). This form is glitch-free by construction: when S releases, the holding
    // term Q & ~R is already true. Each bit is set by the /ECAS lines of the banks where it is 1
    // and cleared by those where it is 0; with every /ECAS high it holds. (Only one /ECAS is
    // ever low, so S and R never overlap.) A latch gated by cas_any would race as /ECAS rises:
    // that glitched A18 at the end of 1 MHz writes in simulation.
    wire [1:0] bank;
    wire b0_set = ~ecas2_n | ~ecas4_n, b0_clr = ~ecas1_n | ~ecas3_n;
    wire b1_set = ~ecas3_n | ~ecas4_n, b1_clr = ~ecas1_n | ~ecas2_n;
    assign bank[0] = b0_set | (bank[0] & ~b0_clr);
    assign bank[1] = b1_set | (bank[1] & ~b1_clr);
    assign ma18 = bank[0];

    // ------------------------------------------------------------------ access qualification
    wire access = cas_any & ~e1moe_n;           // $C0D3 data-port access, column phase
    wire rd     = access &  rwr_n;
    wire wr     = access & ~rwr_n;

    reg  rtc_mode;                              // set by the key, cleared by lock or power-on reset
    wire ram    = ~rtc_mode;

    // CE asserts for the whole $C0D3 cycle (early) so tACE and the MAX693A delay are off the
    // critical path; OE/WE still wait for /ECAS. Address changes while CE is low are harmless.
    assign ram_ce_n = ~(~e1moe_n & ram);
    assign oe0_n    = ~(rd & ram & ~bank[1]);
    assign oe1_n    = ~(rd & ram &  bank[1]);
    assign we0_n    = ~(wr & ram & ~bank[1]);
    assign we1_n    = ~(wr & ram &  bank[1]);
    assign buf_oe_n = e1moe_n;                  // routed via the CPLD so it can be retimed later

    // ------------------------------------------------------------------ key matcher and RTC port
    // Write data is sampled on the column strobe of a write cycle (data is valid by then:
    // Fig. 11-19 shows it settling right after /E1MOE falls, well before /ECAS falls).
    // Mode changes are computed when the byte is sampled but only applied when the write cycle
    // ends (wr falls), so a cycle is never switched between RAM and RTC halfway through: the
    // 8th key byte is a complete RAM write and the lock byte never reaches RAM.
    reg  [2:0] matched;                         // key bytes matched so far
    reg        mode_next;
    reg        sda_low, scl_low;
    wire [7:0] key_byte = KEY[63 - 8*matched -: 8];

    always @(posedge wr or negedge pwr_rst_n) begin
        if (!pwr_rst_n) begin
            matched   <= 3'd0;
            mode_next <= 1'b0;
            sda_low   <= 1'b0;
            scl_low   <= 1'b0;
        end else if (rtc_mode) begin
            if (xd[7]) begin                    // bit 7 set: release the bus and lock
                mode_next <= 1'b0;
                sda_low   <= 1'b0;
                scl_low   <= 1'b0;
            end else begin
                sda_low   <= xd[0];
                scl_low   <= xd[1];
            end
            matched <= 3'd0;
        end else if (xd == key_byte) begin
            if (matched == 3'd7) mode_next <= 1'b1;
            matched <= matched + 3'd1;          // wraps to 0 on unlock
        end else begin
            matched <= (xd == KEY[63:56]) ? 3'd1 : 3'd0;
        end
    end

    always @(negedge wr or negedge pwr_rst_n)
        if (!pwr_rst_n) rtc_mode <= 1'b0;
        else            rtc_mode <= mode_next;

    assign sda = sda_low ? 1'b0 : 1'bz;
    assign scl = scl_low ? 1'b0 : 1'bz;

    // RTC-mode reads: the CPLD drives the card bus (the SRAMs are deselected)
    wire rtc_rd = rd & rtc_mode;
    assign xd = rtc_rd ? {SIGNATURE, scl, sda} : 8'bz;

    assign dbg0 = rtc_mode;
endmodule
