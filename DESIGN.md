# DESIGN.md — Mesa de postulación (`docs/index.html`)

The visual system is Swiss International Typographic Style, applied to a working tool. The page is built on a grid, ruled with hairlines, and has no cards or shadows. The match score is the axis that organizes everything.

## Color
| Token | Light | Dark | Use |
|---|---|---|---|
| `--band` | #1F3FCC | #1A2E9E | Cobalt band (header, axis), primary button |
| `--ground` / `--surface` | #F2F3F1 / #FFF | #0E1014 / #161920 | Background / form fields |
| `--ink`, `--ink-2`, `--ink-3` | #121316, #4A4E57, #6B707A | #ECEEF2, #B4B9C4, #8C93A0 | Text, by hierarchy |
| `--qa` `--frontend` `--design` `--admin` | #1F3FCC #0B7A5C #C2410C #8A6700 | lighter versions | Data series by family (score numerals, labels) |
| `--tick-*` | white, mint, orange, yellow | same | Ticks on the band |
| `--ok` `--warn` `--bad` | green, ochre, red | — | Job tags |

## Type
Archivo (Google Fonts, variable `wdth` and `wght` axes).
- Title: 800 weight, wdth 82.
- Scores: 850 weight, wdth 70, tabular numerals.
- Body: 400 weight at 15px.
- Labels: 600 weight at 12px.

## Components
- **Score axis (signature):** one tick per job on a 0–100 scale, with the 55 threshold dashed. Dragging selects a range, the handles respond to the keyboard, and clicking a tick jumps to its row.
- **Row:** a 3-column grid (score, content, actions) separated by 1px rules.
- **Buttons:** square corners with a 1px ink border; primary is cobalt and the quiet variant uses `--rule`. `:active` scales to 0.97.
- **Compose:** expands in place by animating `grid-template-rows` 0fr→1fr over 240ms with `--ease-out`. It opens Gmail with `authuser`; nothing is ever sent automatically.

## Motion
- Easing: `--ease-out: cubic-bezier(0.23,1,0.32,1)`.
- Durations are 150–240ms, and only specific properties are transitioned.
- `prefers-reduced-motion` turns transitions off.

## Rules
- No rounded cards, gradients, glass or emoji icons. Icons are inline SVG with a 1.6 stroke.
- Every new view uses the same band + filter column + ruled list layout.
