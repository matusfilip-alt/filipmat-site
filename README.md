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
  (resized WebP photos, thumbnails, GPS and EXIF removed) and uploads only the changed
  files to the Blueboard hosting over FTP with TLS.
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

## One-time setup

1. GitHub: create an account and a repository, upload this folder.
2. Blueboard administration > My domains > filipmat.us > FTP: create an FTP account.
   You get a server (host), login and password.
3. GitHub repository > Settings > Secrets and variables > Actions:
   - Secrets: `FTP_SERVER`, `FTP_USERNAME`, `FTP_PASSWORD`
   - Variable (optional): `FTP_DIR`, the target folder on the hosting (default `./`)
4. Pages CMS: sign in with GitHub and pick the repository.

## Switching from WordPress (do it in this order)

1. Back up WordPress (files and database). Blueboard also keeps daily backups for 30 days.
2. Test first: create a subdomain (for example new.filipmat.us), set `FTP_DIR` to its folder,
   run the workflow (Actions > Build and upload to Blueboard > Run workflow, tick dry run
   first), and check the result on the subdomain.
3. Go live: set `FTP_DIR` to the folder of filipmat.us and run the workflow again.
   The old WordPress files (`wp-admin`, `wp-content`, `wp-includes`, `*.php`) are not removed
   automatically. Delete them over FTP once the new site works. The new `.htaccess`
   replaces the old one.
4. Check http://filipmat.us, http://www.filipmat.us and https://filipmat.us all end up on
   https://filipmat.us. If you get a redirect loop, tell me and send the rule you see.
5. Submit `https://filipmat.us/sitemap.xml` in Google Search Console and Bing Webmaster Tools.

The domain stays where it is, DNS does not change because the site stays on the same hosting.
To prefer `www.filipmat.us` instead, change `SITE_URL` in `build.py` and the two redirect
lines in `static/.htaccess`.

## Look and settings

- Styling: `static/style.css` (about 70 lines).
- Site name, author, description, language, address: top of `build.py`.
- Preview without a server: `PREVIEW=1 python build.py`, then open `dist/index.html`.
