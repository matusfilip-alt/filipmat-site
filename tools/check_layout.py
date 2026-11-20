#!/usr/bin/env python3
"""Layout check (LAYOUT.md §6).

Serve dist/ and run:  python tools/check_layout.py http://localhost:8765/
Opens every story at several widths, computes the grid lines from the story
grid and fails if any photo or text column edge is off a line by more than 1px.
Also checks that all index lines in a home-page row share one baseline.
"""
import sys
from playwright.sync_api import sync_playwright

ROOT = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8765/"
WIDTHS = (390, 760, 1024, 1440)

MEASURE = """() => {
  const story = document.querySelector('.story');
  if (!story) return null;
  const cs = getComputedStyle(story);
  const cols = cs.gridTemplateColumns.split(' ').map(parseFloat);
  const gap = parseFloat(cs.columnGap);
  const r = story.getBoundingClientRect();
  const lines = [r.left];
  let x = r.left;
  cols.forEach((w, i) => { x += w; lines.push(x); if (i < cols.length - 1) { x += gap; lines.push(x); } });
  const edges = [];
  story.querySelectorAll('.b').forEach((b, bi) => {
    if (b.classList.contains('b-bleed')) return;
    b.querySelectorAll('figure img, .t').forEach(el => {
      const e = el.getBoundingClientRect();
      if (!e.width) return;
      const what = (b.className.replace('b ', '')) + ' ' + (el.tagName === 'IMG' ? 'photo' : 'text');
      edges.push({what, left: e.left, right: el.tagName === 'IMG' ? e.right : null});
    });
  });
  // pairs must have equal heights
  const pairs = [...story.querySelectorAll('.b-pair')].map(p => [...p.querySelectorAll('img')].map(i => i.getBoundingClientRect().height));
  return {lines, edges, pairs};
}"""

HOME = """() => {
  const rows = {};
  document.querySelectorAll('.tile .idx').forEach(el => {
    const t = Math.round(el.getBoundingClientRect().top);
    const li = el.closest('li').getBoundingClientRect().top;
    (rows[Math.round(li)] ||= []).push(t);
  });
  return Object.values(rows);
}"""


def main():
    bad = 0
    with sync_playwright() as p:
        b = p.chromium.launch()
        for w in WIDTHS:
            pg = b.new_page(viewport={"width": w, "height": 900})
            pg.goto(ROOT + "index.html", wait_until="load")
            pg.evaluate("document.querySelectorAll('img').forEach(i=>i.loading='eager')")
            pg.wait_for_timeout(300)
            slugs = pg.eval_on_selector_all(".tile", "els => els.map(e => e.getAttribute('href'))")
            for row in pg.evaluate(HOME):
                if max(row) - min(row) > 1:
                    print(f"  {w}px home: index lines not level {row}"); bad += 1
            for slug in slugs:
                pg.goto(ROOT + slug.lstrip("./"), wait_until="load")
                pg.evaluate("document.querySelectorAll('img').forEach(i=>i.loading='eager')")
                pg.wait_for_timeout(300)
                m = pg.evaluate(MEASURE)
                if not m:
                    continue
                lines = m["lines"]
                for e in m["edges"]:
                    for side in ("left", "right"):
                        v = e[side]
                        if v is None:
                            continue
                        if min(abs(v - l) for l in lines) > 1:
                            print(f"  {w}px {slug}: {e['what']} {side} edge {v:.1f} off grid"); bad += 1
                for hs in m["pairs"]:
                    if max(hs) - min(hs) > 1:
                        print(f"  {w}px {slug}: pair heights differ {hs}"); bad += 1
                print(f"{w}px {slug}: {len(m['edges'])} edges checked")
        b.close()
    print("FAIL" if bad else "OK: every edge on the grid", f"({bad} problems)")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
