# _snaps

Photos and stories. A plain static site, no WordPress, no database.

## Adding a story (the "admin")

The admin is a phone-friendly editor called Pages CMS (https://pagescms.org). It is not
part of the website, so there is nothing on the site to hack or update.

1. Open Pages CMS on the phone (add it to the home screen), sign in with GitHub.
2. Stories > New. Fill in: title, date, cover photo (the thumbnail), details (camera, film),
   and the story. Insert photos from the phone gallery, in the order they should appear.
3. Save. About a minute later the story is live on filipmat.us and in the sitemap.

Optional: a short description (otherwise made from the first lines of the story),
`draft` to keep a story hidden.

## What happens behind the scenes

- Stories are Markdown files in `content/stories/`, photos are in `media/`.
- On every save, GitHub runs `build.py`, which creates the finished site in `dist/`
  (resized WebP photos, thumbnails, GPS and EXIF removed) and pushes it to Blueboard's
  Git deployment (`git@neuron.blueboard.cz:filipmat.us`, branch `production`), which
  publishes it to filipmat.us. Only changed files are sent.
- Photos: `![describe the photo](/media/x.jpg)`. The text in brackets becomes the alt text
  that screen readers, Google and AI tools read. If left empty it becomes "title, photo N".

## Automatic SEO and AI discoverability (generated from the story content)

- Page title, meta description (first lines of the story), canonical address
- Open Graph and Twitter cards with the cover photo (nice previews in messages and social)
- Structured data (schema.org): BlogPosting per story, WebSite and ItemList on the home page
- `sitemap.xml` including photos, `robots.txt` open to all crawlers, `feed.xml` (RSS)
- `llms.txt` and `llms-full.txt`: plain-text index and full text of all stories for AI tools
- Fast pages (WebP, responsive sizes, lazy loading), semantic HTML, https and one canonical host
- Clean addresses like `https://filipmat.us/through-dads-lens/`

Nobody can guarantee rankings or that a particular AI tool uses these files, but they are
what search engines and AI crawlers look for. Real descriptions in the alt text and a few
sentences of text per story help the most.

## Publishing setup (done)

- GitHub repository `matusfilip-alt/filipmat-site`, workflow `.github/workflows/deploy.yml`.
- Blueboard > filipmat.us > Git: deployment active, key "GitHub Actions (filipmat-site)".
- GitHub secret `BLUEBOARD_SSH_KEY`: the private half of that key.
- Optional GitHub variables: `GA_ID` (Google Analytics), `BUTTONDOWN` (subscribe form).
- After launch: submit `https://filipmat.us/sitemap.xml` in Google Search Console and Bing.

## Look and settings

- Styling: `static/style.css` (about 70 lines).
- Site name, author, description, language, address: top of `build.py`.
- Preview without a server: `PREVIEW=1 python build.py`, then open `dist/index.html`.
