#!/usr/bin/env python3
"""Static site builder for _snaps.

Reads Markdown stories from content/stories/*.md and photos from media/,
writes the finished website into dist/. Everything search engines and AI
tools need (meta tags, structured data, sitemap, feed, llms.txt, image alt
text) is generated from the story content, nothing to maintain by hand.

    pip install -r requirements.txt
    python build.py              # production build
    PREVIEW=1 python build.py    # relative links, for viewing without a server
"""
import html
import json
import os
import re
import shutil
from datetime import date, datetime, timezone
from email.utils import format_datetime
from pathlib import Path

import markdown
import yaml
from PIL import Image, ImageOps

ROOT = Path(__file__).parent
CONTENT = ROOT / "content" / "stories"
MEDIA = ROOT / "media"
STATIC = ROOT / "static"
DIST = ROOT / "dist"

# ---- site settings (edit here) ------------------------------------------
SITE_URL = os.environ.get("SITE_URL", "https://filipmat.us").rstrip("/")
SITE_TITLE = "_snaps"
DOMAIN = "filipmat.us"
AUTHOR = "Filip Matuš"
SITE_DESC = "Photo stories and snaps from travelling and everyday life by Filip Matuš."
LANG = "en"
# Google Analytics 4 measurement ID, e.g. "G-ABC123XYZ". Empty = no analytics at all.
GA_ID = os.environ.get("GA_ID") or "G-Y3X6999H9Q"
# Buttondown username for the "new stories by email" form. Empty = no form.
BUTTONDOWN = os.environ.get("BUTTONDOWN") or "filipmatus"
# --------------------------------------------------------------------------

PREVIEW = bool(os.environ.get("PREVIEW"))
IMG_WIDTHS = (1600,) if os.environ.get("PREVIEW") else (800, 1600, 2400)  # sizes per photo
WEBP_Q = 88   # light compression: photos should look like photos
THUMB = 480               # square thumbnail used on the home page

_img_cache = {}


# ---------- helpers --------------------------------------------------------
def slugify(text):
    text = re.sub(r"[^a-zA-Z0-9]+", "-", text).strip("-").lower()
    return text or "photo"


def parse(path):
    text = path.read_text(encoding="utf-8")
    m = re.match(r"^---\s*\n(.*?)\n---\s*\n?(.*)$", text, re.S)
    if not m:
        return {}, text
    return (yaml.safe_load(m.group(1)) or {}), m.group(2)


def to_date(value):
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        try:
            return date.fromisoformat(value[:10])
        except ValueError:
            pass
    return date.min


def fmt_date(d):
    return "" if d == date.min else f"{d.day}.{d.month}.{d.year}"


def abs_url(path):
    return f"{SITE_URL}/{path.lstrip('/')}"


def href(path):
    """Internal page link. In preview mode directories need an explicit index.html."""
    if PREVIEW and (path.endswith("/") or path == ""):
        return path + "index.html"
    return path


def esc(text):
    return html.escape(str(text), quote=True)


def plain_text(md):
    """Markdown story text -> plain text (no photos, links, or markup)."""
    t = re.sub(r"!\[[^\]]*\]\([^)]*\)", " ", md)
    t = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", t)
    t = re.sub(r"[*_`>#]+", "", t)
    return re.sub(r"\s+", " ", t).strip()


def shorten(text, n=155):
    if len(text) <= n:
        return text
    cut = text[:n].rsplit(" ", 1)[0].rstrip(",;:. ")
    return cut + "…"


def make_description(title, text, n_photos, details):
    if text:
        return shorten(text)
    d = f'Photo story "{title}" by {AUTHOR}'
    if n_photos:
        d += f", {n_photos} photo{'s' if n_photos != 1 else ''}"
    if details:
        d += f". {details}"
    return d + "."


# ---------- photos ---------------------------------------------------------
def process_image(ref):
    """Resize one photo (once), strip EXIF/GPS, return its info or None."""
    rel = ref.split("?")[0].lstrip("/")
    if rel.startswith("media/"):
        rel = rel[len("media/"):]
    if rel in _img_cache:
        return _img_cache[rel]

    src = MEDIA / rel
    if not src.is_file():
        print(f"  ! missing photo: {ref}")
        _img_cache[rel] = None
        return None

    stem = slugify(Path(rel).with_suffix("").as_posix())
    out_dir = DIST / "img"
    out_dir.mkdir(parents=True, exist_ok=True)

    im = ImageOps.exif_transpose(Image.open(src)).convert("RGB")
    w, h = im.size
    sizes = sorted({min(w, x) for x in IMG_WIDTHS})
    files = []
    for tw in sizes:
        th = round(h * tw / w)
        name = f"{stem}-{tw}.webp"
        im.resize((tw, th), Image.LANCZOS).save(out_dir / name, "WEBP", quality=WEBP_Q, method=4)
        files.append((tw, f"img/{name}"))

    thumb_name = f"{stem}-thumb.webp"
    ImageOps.fit(im, (THUMB, THUMB), Image.LANCZOS).save(
        out_dir / thumb_name, "WEBP", quality=WEBP_Q, method=4
    )

    info = {"w": w, "h": h, "files": files, "thumb": f"img/{thumb_name}"}
    _img_cache[rel] = info
    return info


def render_body(body, prefix, title, full=()):
    """Markdown -> composed story layout.

    The story is read as a sequence of text, headings and photos, then laid
    out in varied blocks so it never reads as one long column:
      side   text next to the photo that follows it (alternating sides)
      pair   two photos of the same orientation side by side
      full   a landscape photo, full width
      tall   a portrait photo, narrower, alternating left/right
      line   a short sentence set large
      head   a heading, as a small mono label
      text   longer text with no photo to sit beside
    """
    photos = []
    items = []
    for chunk in re.split(r"\n\s*\n", body.strip()):
        chunk = chunk.strip()
        if not chunk:
            continue
        m = re.fullmatch(r'!\[([^\]]*)\]\(([^)\s]+)(?:\s+"([^"]*)")?\)', chunk)
        if m:
            info = process_image(m.group(2))
            if info:
                alt = m.group(1).strip()
                items.append({"k": "img", "info": info, "alt": alt, "cap": m.group(3) or "",
                              "no": sum(1 for x in items if x["k"] == "img") + 1})
            continue
        if chunk.startswith("#"):
            items.append({"k": "head", "text": chunk.lstrip("#").strip()})
            continue
        html_ = markdown.markdown(chunk, extensions=["extra", "sane_lists"])
        items.append({"k": "text", "html": html_, "len": len(chunk)})

    def fig(it, bleed=False):
        info = it["info"]
        n = len(photos) + 1
        alt = it["alt"] or f"{title}, photo {n}"
        photos.append({"info": info, "alt": alt})
        srcset = ", ".join(f"{prefix}{p} {w}w" for w, p in info["files"])
        big = prefix + info["files"][-1][1]
        w0, small = info["files"][0]
        h0 = round(info["h"] * w0 / info["w"])
        cap = f"<span>{esc(it['cap'])}</span>" if it["cap"] else ""
        return (f'<figure><a href="{big}"><img src="{prefix}{small}" srcset="{srcset}" '
                f'sizes="{"100vw" if bleed else "(min-width: 760px) 70vw, 100vw"}" width="{w0}" height="{h0}" loading="lazy" '
                f'alt="{esc(alt)}"></a><figcaption class="mono"><span>{n:02d}</span>{cap}</figcaption></figure>')

    def ratio(it):
        return it["info"]["w"] / it["info"]["h"]

    def portrait(it):
        return ratio(it) < 1

    def same_shape(x, y):
        return portrait(x) == portrait(y) and abs(ratio(x) - ratio(y)) / ratio(x) <= 0.03

    def block(kind, inner, style=""):
        return f'<div class="b b-{kind}"{style}>{inner}</div>'

    def text_div(html_):
        return f'<div class="t">{html_}</div>'

    # Rules: see LAYOUT.md
    full = {int(n) for n in (full or [])}

    def forced(x):
        return x is not None and x.get("k") == "img" and x.get("no") in full

    out, i = [], 0
    chapter_start = True   # next landscape photo opens a chapter -> bleed
    want_pair = True       # landscape runs alternate pair / wide
    mirror = False         # side and tall blocks alternate left / right
    while i < len(items):
        it = items[i]
        nxt = items[i + 1] if i + 1 < len(items) else None

        if it["k"] == "head":
            out.append(block("head", f'<h2 class="mono">{esc(it["text"])}</h2>'))
            chapter_start, want_pair = True, True
            i += 1
            continue

        if it["k"] == "text":
            run = []
            while i < len(items) and items[i]["k"] == "text":
                run.append(items[i]); i += 1
            total = sum(t["len"] for t in run)
            text_html = "".join(t["html"] for t in run)
            photo = items[i] if i < len(items) and items[i]["k"] == "img" else None
            if len(run) == 1 and total < 70:
                out.append(block("line", text_div(text_html)))
            elif photo and total < 900 and not forced(photo):
                kind = "side-t" if portrait(photo) else "side"
                kind += "-b" if mirror else "-a"
                mirror = not mirror
                out.append(block(kind, text_div(text_html) + fig(photo)))
                chapter_start = False
                i += 1
            else:
                out.append(block("text", text_div(text_html)))
            continue

        # photos
        if forced(it):
            out.append(block("bleed", fig(it, True), f' style="--ar:{ratio(it):.4f}"'))
            chapter_start, want_pair = False, True
            i += 1
            continue
        if portrait(it):
            if nxt and nxt["k"] == "img" and same_shape(it, nxt) and not forced(nxt):
                out.append(block("pair", fig(it) + fig(nxt), f' style="--ar:{ratio(it):.4f}"'))
                i += 2
            else:
                out.append(block("tall-b" if mirror else "tall-a", fig(it)))
                mirror = not mirror
                i += 1
            continue
        if chapter_start:
            out.append(block("bleed", fig(it, True), f' style="--ar:{ratio(it):.4f}"'))
            chapter_start, want_pair = False, True
            i += 1
            continue
        if want_pair and nxt and nxt["k"] == "img" and same_shape(it, nxt) and not forced(nxt):
            out.append(block("pair", fig(it) + fig(nxt), f' style="--ar:{ratio(it):.4f}"'))
            i += 2
        else:
            out.append(block("wide", fig(it)))
            i += 1
        want_pair = not want_pair
    return '<div class="story">\n' + "\n".join(out) + "\n</div>", photos


# ---------- page shell + SEO -----------------------------------------------
def jsonld(data):
    return (
        '<script type="application/ld+json">'
        + json.dumps(data, ensure_ascii=False).replace("</", "<\\/")
        + "</script>"
    )


def page(title, main, *, desc, canonical, prefix="", image=None, og_type="website",
         data=None, scripts="", noindex=False):
    t = esc(title)
    robots = (
        '<meta name="robots" content="noindex">'
        if noindex
        else '<meta name="robots" content="index,follow,max-image-preview:large">'
    )
    og = ""
    if not noindex:
        og = (
            f'<link rel="canonical" href="{esc(canonical)}">\n'
            f'<meta property="og:type" content="{og_type}">\n'
            f'<meta property="og:site_name" content="{esc(SITE_TITLE)}">\n'
            f'<meta property="og:title" content="{t}">\n'
            f'<meta property="og:description" content="{esc(desc)}">\n'
            f'<meta property="og:url" content="{esc(canonical)}">\n'
            f'<meta name="twitter:card" content="{"summary_large_image" if image else "summary"}">\n'
        )
        if image:
            og += f'<meta property="og:image" content="{esc(image)}">\n'
    ld = jsonld(data) if (data and not noindex) else ""
    ga_attr = f' data-ga="{esc(GA_ID)}"' if GA_ID else ""
    if GA_ID:
        scripts = scripts + f'\n<script src="{prefix}analytics.js" defer></script>'
    return f"""<!DOCTYPE html>
<html lang="{LANG}"{ga_attr}>
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{t}</title>
<meta name="description" content="{esc(desc)}">
<meta name="author" content="{esc(AUTHOR)}">
{robots}
{og}<link rel="alternate" type="application/rss+xml" title="{esc(SITE_TITLE)}" href="{prefix}feed.xml">
<link rel="icon" type="image/svg+xml" href="{prefix}favicon.svg">
<link rel="preload" href="{prefix}fonts/special-elite-latin-400-normal.woff2" as="font" type="font/woff2" crossorigin>
<link rel="stylesheet" href="{prefix}style.css">
{ld}
</head>
<body>
<main>
{main}
</main>
{scripts}
</body>
</html>
"""


def person():
    return {"@type": "Person", "name": AUTHOR, "url": SITE_URL + "/"}


# ---------- build ----------------------------------------------------------
def load_stories():
    stories = []
    for path in sorted(CONTENT.glob("*.md")):
        meta, body = parse(path)
        if meta.get("draft"):
            continue
        slug = path.stem
        title = str(meta.get("title") or slug.replace("-", " "))
        print(f"story: {slug}")
        content, photos = render_body(body, "../", title, meta.get("full") or [])
        cover = process_image(str(meta["cover"])) if meta.get("cover") else None
        if not cover and photos:
            cover = photos[0]["info"]
        details = str(meta.get("details") or "")
        place = str(meta.get("place") or "")
        text = plain_text(body)
        desc = str(meta.get("summary") or "") or make_description(title, text, len(photos), details)
        stories.append({
            "slug": slug, "title": title, "date": to_date(meta.get("date")),
            # when it went online; sorts the home page and gives the story its number
            "published": to_date(meta.get("published") or meta.get("date")),
            "html": content, "photos": photos, "cover": cover,
            "details": details, "place": place, "text": text, "desc": desc,
            "url": abs_url(slug + "/"),
        })
    stories.sort(key=lambda s: (s["published"], s["date"]), reverse=True)
    return stories


def write(path, text):
    p = DIST / path
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")


def camera(details):
    return re.split(r"\s*[|,]\s*", details)[0] if details else ""


def frames(n):
    return f"{n} frame{'s' if n != 1 else ''}"


def bar(prefix, right=""):
    return (f'<header class="bar top"><a class="brand" href="{href(prefix or "./")}">'
            f'<span class="site">{SITE_TITLE}</span> <span class="by mono">by {DOMAIN}</span></a>'
            f'<span class="right">{right}</span></header>')


def subscribe():
    if not BUTTONDOWN:
        return ""
    return (f'<form class="sub mono" action="https://buttondown.com/api/emails/embed-subscribe/{esc(BUTTONDOWN)}" '
            'method="post" target="_blank">'
            '<label for="sub-email">new stories by email</label>'
            '<input id="sub-email" type="email" name="email" placeholder="your@email" required autocomplete="email">'
            '<button type="submit">subscribe</button></form>')


def foot(prefix):
    return (f'{subscribe()}<footer class="foot mono"><span>{SITE_TITLE} by {DOMAIN} · photo stories by {esc(AUTHOR)}</span>'
            f'<a href="{prefix}feed.xml">rss</a></footer>')


def number(stories):
    for i, s in enumerate(sorted(stories, key=lambda s: (s["published"], s["date"]))):
        s["no"] = f"{i + 1:02d}"


def build_story_pages(stories):
    for i, s in enumerate(stories):
        iso = s["date"].isoformat() if s["date"] != date.min else ""
        label = []
        if iso:
            label.append(f'<time datetime="{iso}">{fmt_date(s["date"])}</time>')
        if s["place"]:
            label.append(f'<span>{esc(s["place"])}</span>')
        if s["details"]:
            label.append(f'<span>{esc(s["details"])}</span>')
        if s["photos"]:
            label.append(f'<span>{frames(len(s["photos"]))}</span>')
        nxt = stories[(i + 1) % len(stories)] if len(stories) > 1 else None
        next_html = ""
        if nxt:
            th = f'<img src="../{nxt["cover"]["thumb"]}" alt="" width="89" height="89" loading="lazy">' if nxt["cover"] else "<span></span>"
            next_html = (f'<a class="next" href="{href("../" + nxt["slug"] + "/")}">{th}'
                         f'<span><span class="mono">next · №&nbsp;{nxt["no"]}</span><br>'
                         f'<span class="t">{esc(nxt["title"])}</span></span></a>')
        main = (
            bar("../") + "\n"
            f'<article>\n<div class="head"><span class="no mono">№&nbsp;{s["no"]}</span>'
            f'<h1>{esc(s["title"])}</h1><div class="label mono">{"".join(label)}</div></div>\n'
            f'{s["html"]}\n</article>\n{next_html}\n{foot("../")}'
        )
        images = [abs_url(p["info"]["files"][-1][1]) for p in s["photos"]]
        og_image = abs_url(s["cover"]["files"][-1][1]) if s["cover"] else None
        data = {
            "@context": "https://schema.org", "@type": "BlogPosting",
            "headline": s["title"], "description": s["desc"], "url": s["url"],
            "mainEntityOfPage": {"@type": "WebPage", "@id": s["url"]},
            "inLanguage": LANG, "author": person(), "publisher": person(),
            "isPartOf": {"@type": "Blog", "name": SITE_TITLE, "url": SITE_URL + "/"},
        }
        if iso:
            data["datePublished"] = iso
            data["dateModified"] = iso
        if images:
            data["image"] = images
        if s["details"]:
            data["keywords"] = s["details"]
        if s["place"]:
            data["contentLocation"] = {"@type": "Place", "name": s["place"]}
            data["locationCreated"] = {"@type": "Place", "name": s["place"]}
        write(f'{s["slug"]}/index.html', page(
            f'{s["title"]} - {SITE_TITLE} by {DOMAIN}', main, desc=s["desc"], canonical=s["url"],
            prefix="../", image=og_image, og_type="article", data=data,
            scripts='<script src="../viewer.js" defer></script>' if s["photos"] else ""))


def build_home(stories):
    tiles = []
    for s in stories:
        c = s["cover"]
        if c:
            w, path = c["files"][0]
            h = round(c["h"] * w / c["w"])
            srcset = ", ".join(f"{p} {fw}w" for fw, p in c["files"])
            img = (f'<img src="{path}" srcset="{srcset}" sizes="(min-width:900px) 360px, 50vw" '
                   f'width="{w}" height="{h}" alt="{esc(s["title"])}" loading="lazy">')
        else:
            img = '<img alt="">'
        meta = " · ".join(f"<span>{esc(x)}</span>" for x in (
            str(s["date"].year) if s["date"] != date.min else "",
            camera(s["details"]),
            frames(len(s["photos"])) if s["photos"] else "") if x)
        tiles.append(
            f'<li><a class="tile" href="{href(s["slug"] + "/")}">{img}<span class="idx">'
            f'<span class="no">{s["no"]}</span><span class="title">{esc(s["title"])}</span>'
            f'<span class="meta mono">{meta}</span></span></a></li>')
    total = sum(len(s["photos"]) for s in stories)
    main = (bar("", f'{len(stories)} stories · {total} frames') + "\n"
            '<h1 class="visually-hidden">' + esc(f"{SITE_TITLE}, photo stories by {AUTHOR}") + '</h1>\n'
            '<ul class="grid">\n' + "\n".join(tiles) + "\n</ul>\n" + foot(""))
    data = {
        "@context": "https://schema.org",
        "@graph": [
            {"@type": "WebSite", "name": f"{SITE_TITLE} by {DOMAIN}", "url": SITE_URL + "/",
             "description": SITE_DESC, "inLanguage": LANG, "author": person()},
            {"@type": "CollectionPage", "name": SITE_TITLE, "url": SITE_URL + "/",
             "mainEntity": {"@type": "ItemList", "itemListElement": [
                 {"@type": "ListItem", "position": i + 1, "url": s["url"], "name": s["title"]}
                 for i, s in enumerate(stories)]}},
        ],
    }
    og_image = abs_url(stories[0]["cover"]["files"][-1][1]) if stories and stories[0]["cover"] else None
    write("index.html", page(f"{SITE_TITLE} by {DOMAIN} - photo stories by {AUTHOR}", main, desc=SITE_DESC,
                             canonical=SITE_URL + "/", image=og_image, data=data))


def build_extras(stories):
    # 404
    write("404.html", page("not found", bar("/") + '\n<p>nothing here.</p>',
                           desc="Page not found", canonical=SITE_URL + "/", noindex=True))

    # sitemap with photos
    urls = []
    newest = max((s["date"] for s in stories if s["date"] != date.min), default=None)
    urls.append(f'<url><loc>{SITE_URL}/</loc>' + (f"<lastmod>{newest.isoformat()}</lastmod>" if newest else "") + "</url>")
    for s in stories:
        imgs = "".join(
            f'<image:image><image:loc>{esc(abs_url(p["info"]["files"][-1][1]))}</image:loc></image:image>'
            for p in s["photos"]
        )
        lm = f'<lastmod>{s["date"].isoformat()}</lastmod>' if s["date"] != date.min else ""
        urls.append(f'<url><loc>{esc(s["url"])}</loc>{lm}{imgs}</url>')
    write("sitemap.xml",
          '<?xml version="1.0" encoding="UTF-8"?>\n'
          '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" '
          'xmlns:image="http://www.google.com/schemas/sitemap-image/1.1">\n'
          + "\n".join(urls) + "\n</urlset>\n")

    # robots: everything open, including AI search and assistant crawlers
    write("robots.txt",
          "# Open to all crawlers, including search engines and AI assistants.\n"
          "User-agent: *\nAllow: /\n\n"
          f"Sitemap: {SITE_URL}/sitemap.xml\n")

    # RSS feed
    items = []
    for s in stories:
        pub = ""
        if s["date"] != date.min:
            dt = datetime(s["date"].year, s["date"].month, s["date"].day, 12, tzinfo=timezone.utc)
            pub = f"<pubDate>{format_datetime(dt)}</pubDate>"
        items.append(
            f'<item><title>{esc(s["title"])}</title><link>{esc(s["url"])}</link>'
            f'<guid>{esc(s["url"])}</guid>{pub}<description>{esc(s["desc"])}</description></item>'
        )
    write("feed.xml",
          '<?xml version="1.0" encoding="UTF-8"?>\n<rss version="2.0"><channel>'
          f"<title>{esc(SITE_TITLE)}</title><link>{SITE_URL}/</link>"
          f"<description>{esc(SITE_DESC)}</description><language>{LANG}</language>"
          + "".join(items) + "</channel></rss>\n")

    # llms.txt (short index) and llms-full.txt (all text + photo descriptions)
    short = [f"# {SITE_TITLE}", "", f"> {SITE_DESC}", "", "## Stories", ""]
    full = [f"# {SITE_TITLE}", "", f"> {SITE_DESC}", ""]
    for s in stories:
        short.append(f'- [{s["title"]}]({s["url"]}): {s["desc"]}')
        full += ["", f'## {s["title"]}', "", f'URL: {s["url"]}']
        if s["date"] != date.min:
            full.append(f'Date: {s["date"].isoformat()}')
        if s["place"]:
            full.append(f'Place: {s["place"]}')
        if s["details"]:
            full.append(f'Camera: {s["details"]}')
        if s["text"]:
            full += ["", s["text"]]
        if s["photos"]:
            full += ["", "Photos:"]
            full += [f'- {p["alt"]}: {abs_url(p["info"]["files"][-1][1])}' for p in s["photos"]]
    write("llms.txt", "\n".join(short) + "\n")
    write("llms-full.txt", "\n".join(full) + "\n")


def build():
    if DIST.exists():
        shutil.rmtree(DIST)
    DIST.mkdir()
    if STATIC.exists():
        shutil.copytree(STATIC, DIST, dirs_exist_ok=True)
    stories = load_stories()
    number(stories)
    build_story_pages(stories)
    build_home(stories)
    build_extras(stories)
    print(f"done: {len(stories)} stories -> {DIST}" + (" (preview links)" if PREVIEW else ""))


if __name__ == "__main__":
    build()
