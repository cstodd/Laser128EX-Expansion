# Mechanical

## Measured (Nov 2026) on Renée Harke's bare clone of the stock card (702175 "Cx rev 1")
- Card: **~190 × 90 mm** (measured 189 × 90; assumed trimmed by ~1 mm).
- Mounting holes: 182 mm centre-to-centre along the bottom, 82 mm centre-to-centre along the left,
  so the holes sit ~4 mm in from each edge. **Caveat:** Renée wrote that her clone's *left-hand* holes "don't
  quite line up", so only the right-hand hole is trusted.
- **Bottom-right hole → J17:** 23 mm from the hole centre to the centre of the lowest pin pair (pins 15/16).
  The J17 centreline (between the two pin rows) passes through the hole centre.
- Renée's working CPLD card (v0.2, 2020) uses **only that bottom-right hole**, with the 2×15 header on the right
  edge above it. We do the same.

## Derived card geometry (this project)
Board coordinates: origin at the top-left corner, x to the right, y down, viewed from the component side.

| Item | Position (mm) |
|---|---|
| Board outline | **100 × 90** (rev 0.1, KiCad 10). Inside the stock envelope; right and bottom edges match the stock card |
| H1 mounting hole (M3, Laser standoff) | (96.00, 86.00): 4 mm in from the right and bottom edges |
| H3 (M3, user standoff/spacer) | (5, 86): left-side support, position not critical (H2 removed) |
| J1 pin 1 (square pad, interior row) | (94.73, 27.44) |
| J1 pin 30 | (97.27, 27.44) |
| J1 pins 15 / 16 | (94.73, 63.00) / (97.27, 63.00): 23.00 mm above H1 |
| J1 socket body | **underside** (non-component side). Pad numbering is as seen from the component side |

J1's row centreline is x = 96.00, through the H1 centre. The stock card extends a further ~90 mm to the left of our board (x < 0 in these coordinates),
space we don't use.

## Still to confirm
- Component height limit above the card (tallest parts: the PLCC socket with chip, the CR2032 holder, the 22 µF cap).
- Nothing above the 90 mm top edge inside the case was measured; ours is the same height as the stock card.
