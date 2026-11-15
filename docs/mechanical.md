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
| Board outline | 100 × 90 (fits inside the stock envelope; right and bottom edges match the stock card) |
| H1 mounting hole (M3) | (96.00, 86.00): 4 mm in from the right and bottom edges |
| J1 pin 1 (square pad, interior row) | (94.73, 27.44) |
| J1 pin 30 | (97.27, 27.44) |
| J1 pins 15 / 16 | (94.73, 63.00) / (97.27, 63.00): 23.00 mm above H1 |

J1's row centreline is x = 96.00, through the hole centre. The stock card's left part (x < 0 in these coordinates,
down to −90 mm) is free space we don't use.

## Still to confirm
- **Which face the J1 socket body is on**, and the component height limit above/below the card.
  The pad numbering is correct as long as our components sit on the same face as the stock card's
  components; the socket body goes on whichever face mates with the motherboard pins.
- The top edge: the stock card is 90 mm tall, and so is ours. Nothing above it inside the case was measured.
