# mechidan.com

Bilingual static business site. Spanish at `/`, English at `/en/`. No framework, no build
dependencies for the HTML, no third-party requests at runtime.

## Layout

```
site.config.json      every value that changes: prices, contact, legal, toggles
content/es.json       Spanish copy
content/en.json       English copy
build.py              renders HTML, sitemap, robots.txt, llms.txt   (stdlib only)
check.py              verifies the build, and prints the DNS table  (stdlib only)
make_assets.py        renders scope PDFs, favicon, social card      (needs pip deps)
Makefile              shortcuts for all of the above
assets/css/style.css  the whole stylesheet
assets/js/app.js      quote builder, form, language preference
assets/fonts/*.woff2  self-hosted, OFL licensed
```

Generated files (`index.html`, `en/`, `sitemap.xml`, `robots.txt`, `llms.txt`, `CNAME`,
`404.html`, `site.webmanifest`) get committed, because GitHub Pages serves them directly.
Edit the JSON, never the HTML.

## Daily use

```bash
make deps      # once
make all       # rebuild HTML and assets
make serve     # preview on http://localhost:8000
make check     # validate JSON-LD, internal links, sitemap
make deploy    # build, verify, commit, push
make dns       # print the Porkbun records
```

## First-time setup

### 1. Fill the placeholders

`build.py` prints a warning for every value still set to `FILL_ME`. The site builds and works
without them, and hides whatever it cannot show. Fill these in `site.config.json`:

| Key | Effect while unset |
|---|---|
| `contact.phoneE164` | WhatsApp and call buttons stay hidden |
| `form.endpoint` | the form opens a mail client instead of posting |
| `identity.legalName`, `taxId`, `registeredAddress` | legal notice shows a pending banner |

Set `identity.autonomoRegistered` to `true` once you register, and the banner disappears.

### 2. Wire up the form

GitHub Pages serves static files, so the form needs an endpoint elsewhere. Sign up at
formspree.io, create a form pointed at `kamil@mechidan.com`, and paste the endpoint URL into
`form.endpoint`. The free tier covers 50 submissions a month.

Whatever you pick, keep `legal.processorName`, `legal.processorCountry` and
`legal.processorPrivacyUrl` in sync. The privacy policy reads those three values and names your
processor, which GDPR requires you to disclose.

Once your VPS is running, move the endpoint to your own box and set `processorCountry` to Spain.
That drops the third-country transfer from your privacy policy entirely, and it demonstrates the
thing you sell.

### 3. Publish

```bash
git add -A
git commit -m "Initial site"
git push -u origin main
```

Then in the repo settings, under Pages, set the source to the `main` branch, folder `/ (root)`,
and put `mechidan.com` in the custom domain field. Tick "Enforce HTTPS" once the certificate
issues, which takes up to an hour.

### 4. DNS at Porkbun

Run `make dns` for the exact table. Four A records and four AAAA records on the blank host,
plus a CNAME on `www` pointing at `mkkouarti.github.io`. Delete the parking records Porkbun
creates by default, or GitHub will not resolve the apex.

Verify:

```bash
dig mechidan.com +noall +answer -t A
dig www.mechidan.com +noall +answer -t CNAME
```

Porkbun also gives you free email forwarding, which is how `kamil@mechidan.com` reaches your
inbox without paying for a mailbox.

## Cookies and GDPR

The site sets no cookies and runs no analytics. Fonts are self-hosted, so no request reaches
Google. The only browser storage is one `localStorage` key holding your visitor's language
choice, which is a functional preference the visitor asked for and needs no consent banner.

The contact form collects personal data, so the privacy policy at `/privacidad.html` exists and
the form will not submit until the visitor ticks the consent box. If you ever add analytics,
you also need a consent banner, and the "no cookies" claims in both policies stop being true.

## Editing prices

Prices live in `site.config.json` under `services`. Names and descriptions live in
`content/*.json` under `services.items`, keyed by the same ids. Change a number, run
`make all`, and it updates the cards, the quote builder, the structured data and `llms.txt`
at once.

To retire the launch offer, set `commercial.launchOffer.enabled` to `false`.

## SEO and answer engines

Both locales carry canonical URLs and reciprocal `hreflang` tags, with Spanish as `x-default`.
`sitemap.xml` lists both language versions of every page. Structured data covers
`ProfessionalService` with priced offers, `FAQPage`, `HowTo` and `WebSite`.

`llms.txt` is a plain-text brief for answer engines: prices, terms and the full FAQ, generated
from the same JSON so it never drifts from the page.
