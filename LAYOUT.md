# _snaps layout system

The rules every page follows. They are applied automatically by `build.py`,
so a new story gets a composed layout without any manual placement.

## 1. One grid, shared by everything

Every story is a single CSS grid. Each block (photo, pair, text) is a row of
that same grid (`subgrid`), so all edges come from the same column lines and
nothing can drift by a few pixels.

| screen            | columns | gutter | outer margin |
|-------------------|---------|--------|--------------|
| phone  (< 760px)  | 2       | 13px   | 21px         |
| larger (≥ 760px)  | 6       | 21px   | 55px         |

Max content width 1240px.

On larger screens only four vertical lines are ever used inside the content:
**0, 2, 3, 4, 6** (column boundaries). Every photo and every text column
starts or ends on one of them.

```
0     1     2     3     4     5     6
|-----|-----|-----|-----|-----|-----|
```

## 2. Block types

| block    | when                                                        | larger screens        | phone            |
|----------|-------------------------------------------------------------|-----------------------|------------------|
| bleed    | first landscape photo of a story or of a chapter            | full window width     | full window width|
| wide     | a single landscape photo                                    | 0–6                   | 0–2              |
| pair     | two photos in a row with the same shape (±3 %)              | 0–3 + 3–6             | 0–1 + 1–2        |
| tall     | a single portrait photo, alternating sides                  | 0–3 or 3–6            | 0–2              |
| side     | text followed by a landscape photo                          | text 0–2, photo 2–6 (or mirrored: photo 0–4, text 4–6) | text above photo |
| side-tall| text followed by a portrait photo                           | photo 0–3, text 3–6 (or mirrored) | text above photo |
| text     | longer text with no photo next to it                        | 2–6, max 34em         | 0–2              |
| line     | one short sentence (under 70 characters)                    | 2–6, large italic     | 0–2              |
| head     | a heading in the story                                      | 0–6, small mono label | 0–2              |

A story can force frames to full screen with `full: [18, 24]` (the frame numbers shown under the photos).

Runs of landscape photos alternate **wide, pair, wide, pair** so long series
read like a contact sheet, not a scroll.

Pairs always have equal height: photos are only paired when their shapes are
within 3 %, and the pair shares one exact aspect ratio (a crop of at most 3 %).

Text beside a photo is centred vertically on the photo (not on photo plus frame number).

## 3. Vertical rhythm

| between                         | space |
|---------------------------------|-------|
| photo and photo                 | 34px (21px on phone) |
| anything and text               | 55px (34px on phone) |
| before a heading                | 89px (55px on phone) |
| frame number under a photo      | 8px   |

## 4. Type

- Inter 500: site name, story titles, home titles.
- Special Elite (typewriter, with ink imperfections): story text at 15px in #555, short lines set larger.
- IBM Plex Mono: everything that is a fact. Numbers, dates, cameras, frames, headings as labels.

## 5. Home page

Every tile has the same 3:2 frame. The photo sits uncropped inside it, aligned
to the bottom-left corner, so all index lines under the tiles share one
baseline across the row, whatever the photo's shape.

## 6. Checks

`tools/check_layout.py` opens every page at 390, 1024 and 1440px wide,
measures the left and right edge of every photo and text column, and fails if
any edge is not on a grid line (±1px).
