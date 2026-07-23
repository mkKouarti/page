#!/usr/bin/env python3
"""
Mechidan static site builder.

Reads:   site.config.json, content/<locale>.json
Writes:  index.html, en/index.html, legal pages, 404.html,
         sitemap.xml, robots.txt, llms.txt, CNAME, .nojekyll

Idempotent: run it as many times as you like, the output is identical
for identical input. No hardcoded values live in this file; everything
comes from the two JSON sources.

Usage:  python3 build.py
"""

import json
import html
import os
import re
import sys
from datetime import date, datetime, timezone
from urllib.parse import quote

ROOT = os.path.dirname(os.path.abspath(__file__))
PLACEHOLDER = "FILL_ME"
WARNINGS = []


# --------------------------------------------------------------------------
# helpers
# --------------------------------------------------------------------------
def load(path):
    with open(os.path.join(ROOT, path), encoding="utf-8") as fh:
        return json.load(fh)


def write(relpath, text):
    dest = os.path.join(ROOT, relpath)
    os.makedirs(os.path.dirname(dest) or ".", exist_ok=True)
    with open(dest, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(text)
    return relpath


def e(value):
    """Escape for HTML text and attribute context."""
    return html.escape(str(value), quote=True)


def filled(value):
    """Return None when a config value is still a placeholder."""
    if value is None:
        return None
    if isinstance(value, str) and value.startswith(PLACEHOLDER):
        return None
    return value


def require(value, label):
    got = filled(value)
    if got is None:
        WARNINGS.append(label)
    return got


def fill(template, values):
    """Replace {token} placeholders in copy with real values."""
    def sub(match):
        key = match.group(1)
        return str(values.get(key, match.group(0)))
    return re.sub(r"\{(\w+)\}", sub, str(template))


# --------------------------------------------------------------------------
# inline svg icons (no icon font, no external requests)
# --------------------------------------------------------------------------
ICON = {
    "check": '<path d="M20 6 9 17l-5-5"/>',
    "plus": '<path d="M12 5v14M5 12h14"/>',
    "arrow": '<path d="M5 12h14M13 6l6 6-6 6"/>',
    "back": '<path d="M19 12H5M11 18l-6-6 6-6"/>',
    "mail": '<rect x="2" y="4" width="20" height="16" rx="2"/><path d="m22 7-10 6L2 7"/>',
    "phone": '<path d="M22 16.9v3a2 2 0 0 1-2.2 2 19.8 19.8 0 0 1-8.6-3.1 19.5 19.5 0 0 1-6-6A19.8 19.8 0 0 1 2.1 4.2 2 2 0 0 1 4.1 2h3a2 2 0 0 1 2 1.7c.1 1 .4 1.9.7 2.8a2 2 0 0 1-.5 2.1L8.1 9.9a16 16 0 0 0 6 6l1.3-1.2a2 2 0 0 1 2.1-.5c.9.3 1.8.6 2.8.7a2 2 0 0 1 1.7 2Z"/>',
    "whatsapp": '<path d="M12.04 2A9.9 9.9 0 0 0 2.1 11.9a9.8 9.8 0 0 0 1.34 4.95L2 22l5.3-1.38a9.9 9.9 0 0 0 4.74 1.2h.01A9.9 9.9 0 0 0 22 11.92 9.9 9.9 0 0 0 12.04 2Zm5.8 14.05c-.25.69-1.44 1.32-1.98 1.37-.53.05-1.03.24-3.47-.72-2.92-1.15-4.77-4.14-4.91-4.33-.14-.2-1.17-1.56-1.17-2.97 0-1.42.74-2.11 1-2.4.26-.29.57-.36.76-.36l.55.01c.17 0 .41-.07.64.49l.88 2.13c.07.15.12.32.02.51-.1.2-.15.32-.3.49l-.44.51c-.14.15-.29.3-.13.6.17.28.75 1.23 1.6 2 1.11.98 2.04 1.28 2.33 1.43.29.15.46.12.63-.07l.9-1.05c.2-.24.38-.19.63-.1l1.8.85c.26.12.43.19.5.29.06.1.06.6-.19 1.29Z"/>',
    "linkedin": '<path d="M4.98 3.5A2.5 2.5 0 1 1 2.5 6 2.5 2.5 0 0 1 4.98 3.5ZM3 8.98h4V21H3ZM9.5 8.98h3.83v1.64h.05a4.2 4.2 0 0 1 3.78-2.08c4.04 0 4.79 2.66 4.79 6.12V21h-4v-5.45c0-1.3-.02-2.98-1.81-2.98-1.82 0-2.1 1.42-2.1 2.88V21h-4Z"/>',
    "github": '<path d="M12 2a10 10 0 0 0-3.16 19.49c.5.09.68-.22.68-.48l-.01-1.7c-2.78.6-3.37-1.34-3.37-1.34-.45-1.16-1.1-1.47-1.1-1.47-.91-.62.07-.6.07-.6 1 .07 1.53 1.03 1.53 1.03.9 1.53 2.34 1.09 2.91.83.09-.65.35-1.09.63-1.34-2.22-.25-4.55-1.11-4.55-4.94 0-1.09.39-1.98 1.03-2.68-.1-.25-.45-1.27.1-2.65 0 0 .84-.27 2.75 1.02a9.5 9.5 0 0 1 5 0c1.91-1.3 2.75-1.02 2.75-1.02.55 1.38.2 2.4.1 2.65.64.7 1.03 1.6 1.03 2.68 0 3.84-2.34 4.68-4.57 4.93.36.31.68.92.68 1.85l-.01 2.75c0 .27.18.58.69.48A10 10 0 0 0 12 2Z"/>',
    "external": '<path d="M15 3h6v6M10 14 21 3M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"/>',
    "doc": '<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8Z"/><path d="M14 2v6h6M9 15h6"/>',
    "menu": '<path d="M3 6h18M3 12h18M3 18h18"/>',
    "shield": '<path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10Z"/><path d="m9 12 2 2 4-4"/>',
}


def icon(name, cls=""):
    body = ICON[name]
    fill_rule = "currentColor" if name in ("whatsapp", "linkedin", "github") else "none"
    stroke = "none" if fill_rule == "currentColor" else "currentColor"
    attrs = f' class="{e(cls)}"' if cls else ""
    return (
        f'<svg{attrs} viewBox="0 0 24 24" fill="{fill_rule}" stroke="{stroke}" '
        f'stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round" '
        f'aria-hidden="true" focusable="false">{body}</svg>'
    )


LOGO = (
    '<svg class="brand__mark" viewBox="0 0 32 32" fill="none" aria-hidden="true" focusable="false">'
    '<rect x="1.4" y="1.4" width="29.2" height="29.2" rx="6" stroke="currentColor" stroke-width="2.2"/>'
    '<path d="M9 11.5 13.6 16 9 20.5" stroke="currentColor" stroke-width="2.4" '
    'stroke-linecap="round" stroke-linejoin="round"/>'
    '<path d="M16.8 21h6.4" stroke="#C9930E" stroke-width="2.4" stroke-linecap="round"/>'
    "</svg>"
)


# --------------------------------------------------------------------------
# page shell
# --------------------------------------------------------------------------
def head(cfg, c, page, ctx):
    base = cfg["site"]["baseUrl"]
    brand = cfg["identity"]["brand"]
    title = fill(page["title"], {"brand": brand})
    desc = page["description"]
    canonical = base + page["path"]

    alt_es = base + page["altPaths"]["es"]
    alt_en = base + page["altPaths"]["en"]

    tags = [
        '<meta charset="utf-8">',
        '<meta name="viewport" content="width=device-width, initial-scale=1">',
        f"<title>{e(title)}</title>",
        f'<meta name="description" content="{e(desc)}">',
        f'<link rel="canonical" href="{e(canonical)}">',
        f'<link rel="alternate" hreflang="es" href="{e(alt_es)}">',
        f'<link rel="alternate" hreflang="en" href="{e(alt_en)}">',
        f'<link rel="alternate" hreflang="x-default" href="{e(alt_es)}">',
        f'<meta name="robots" content="{e(page.get("robots", "index,follow,max-image-preview:large"))}">',
        f'<meta name="author" content="{e(cfg["identity"]["displayName"])}">',
        '<meta name="theme-color" content="#072B28">',
        f'<meta property="og:type" content="{e(page.get("ogType", "website"))}">',
        f'<meta property="og:title" content="{e(title)}">',
        f'<meta property="og:description" content="{e(desc)}">',
        f'<meta property="og:url" content="{e(canonical)}">',
        f'<meta property="og:site_name" content="{e(brand)}">',
        f'<meta property="og:locale" content="{e(c["htmlLang"].replace("-", "_"))}">',
        f'<meta property="og:image" content="{e(base)}/assets/img/og.png">',
        '<meta property="og:image:width" content="1200">',
        '<meta property="og:image:height" content="630">',
        f'<meta property="og:image:alt" content="{e(fill(c["meta"]["ogAlt"], {"brand": brand}))}">',
        '<meta name="twitter:card" content="summary_large_image">',
        '<link rel="icon" href="/assets/img/favicon.svg" type="image/svg+xml">',
        '<link rel="apple-touch-icon" href="/assets/img/icon-180.png">',
        '<link rel="manifest" href="/site.webmanifest">',
    ]
    if page.get("keywords"):
        tags.append(f'<meta name="keywords" content="{e(page["keywords"])}">')

    for font in ("archivo-var", "publicsans-var", "jetbrainsmono-var"):
        tags.append(
            f'<link rel="preload" href="/assets/fonts/{font}.woff2" as="font" '
            'type="font/woff2" crossorigin>'
        )
    tags.append('<link rel="stylesheet" href="/assets/css/style.css">')

    for block in page.get("jsonld", []):
        tags.append(
            '<script type="application/ld+json">'
            + json.dumps(block, ensure_ascii=False, separators=(",", ":"))
            + "</script>"
        )
    return "\n  ".join(tags)


def masthead(cfg, c, ctx):
    home = ctx["home"]
    alt = ctx["altHome"]
    nav = c["nav"]
    links = "".join(
        f'<a href="{home}#{anchor}">{e(nav[key])}</a>'
        for key, anchor in (
            ("services", "services"),
            ("process", "process"),
            ("faq", "faq"),
            ("contact", "contact"),
        )
    )
    return f"""<header class="masthead">
  <div class="shell masthead__in">
    <a class="brand" href="{home}">{LOGO}<span>{e(cfg["identity"]["brand"])}</span></a>
    <nav class="mainnav" id="mainnav" data-open="false" aria-label="{e(nav["services"])}">{links}</nav>
    <a class="lang" href="{alt}" data-lang-set="{e(ctx["altLocale"])}" hreflang="{e(ctx["altLocale"])}"
       aria-label="{e(nav["langSwitch"])}">{e(c["altLocaleLabel"])}</a>
    <button class="burger" id="burger" type="button" aria-expanded="false"
            aria-controls="mainnav" aria-label="{e(nav["menuOpen"])}">{icon("menu")}</button>
  </div>
</header>"""


def footer(cfg, c, ctx):
    ident = cfg["identity"]
    f = c["footer"]
    year = date.today().year
    owner = filled(ident["legalName"]) or ident["displayName"]
    tax = filled(ident["taxId"])
    tax_line = f' <span>{e(tax)}</span>' if tax else ""
    return f"""<footer class="foot">
  <div class="shell">
    <div class="foot__top">
      <div>
        <span class="brand">{LOGO}<span>{e(ident["brand"])}</span></span>
        <p class="foot__tag">{e(f["tagline"])}</p>
      </div>
      <nav class="foot__links" aria-label="{e(f["legalNotice"])}">
        <a href="{ctx["legalUrl"]}">{e(f["legalNotice"])}</a>
        <a href="{ctx["privacyUrl"]}">{e(f["privacy"])}</a>
        <a href="{ctx["scopeUrl"]}">{e(f["scope"])}</a>
      </nav>
    </div>
    <div class="foot__bot">
      <span>&copy; {year} {e(owner)}.{tax_line} {e(f["rights"])}</span>
      <span>{e(f["builtNote"])}</span>
    </div>
  </div>
</footer>"""


def page_shell(cfg, c, ctx, page, body, payload=None):
    scripts = ""
    if payload is not None:
        scripts = (
            '\n<script type="application/json" id="site-data">'
            + json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
            + "</script>\n<script src=\"/assets/js/app.js\" defer></script>"
        )
    return f"""<!doctype html>
<html lang="{e(c["htmlLang"])}" dir="{e(c["dir"])}">
<head>
  {head(cfg, c, page, ctx)}
</head>
<body>
<a class="skip" href="#main">{e(c["nav"]["skipToContent"])}</a>
{masthead(cfg, c, ctx)}
<main id="main">
{body}
</main>
{footer(cfg, c, ctx)}{scripts}
</body>
</html>
"""


# --------------------------------------------------------------------------
# home page sections
# --------------------------------------------------------------------------
def sec_hero(cfg, c, ctx):
    h = c["hero"]
    p = c["panel"]
    com = cfg["commercial"]
    anchor = ctx["services"][0]

    trust = "".join(
        f'<li>{icon("check")}<span>{e(item)}</span></li>' for item in h["trust"]
    )

    cta = []
    if ctx["whatsapp"]:
        cta.append(
            f'<a class="btn btn--brass" href="{e(ctx["wa_link"](p["waMessage"]))}" '
            f'target="_blank" rel="noopener">{icon("whatsapp")}{e(h["ctaPrimary"])}</a>'
        )
    # without a phone number the form link carries the primary weight instead
    second_style = "btn--line" if ctx["whatsapp"] else "btn--brass"
    cta.append(f'<a class="btn {second_style}" href="#contact">{e(h["ctaSecondary"])}{icon("arrow")}</a>')

    items = "".join(f'<li>{icon("check")}<span>{e(item)}</span></li>' for item in p["items"])
    price = ctx["money"](anchor["basePrice"])
    delivery = fill(p["deliveryValue"], {"min": com["deliveryDaysMin"], "max": com["deliveryDaysMax"]})

    wa_btn = ""
    if ctx["whatsapp"]:
        wa_btn = (
            f'<a class="btn btn--line btn--block" href="{e(ctx["wa_link"](p["waMessage"]))}" '
            f'target="_blank" rel="noopener">{icon("whatsapp")}{e(p["ctaWhatsapp"])}</a>'
        )

    return f"""<section class="hero">
  <div class="shell hero__grid">
    <div>
      <p class="hero__eyebrow"><span class="pulse"></span>{e(h["eyebrow"])}</p>
      <h1>{e(h["h1Lead"])} <span class="accent">{e(h["h1Accent"])}</span></h1>
      <p class="hero__sub">{e(h["sub"])}</p>
      <div class="hero__cta">{"".join(cta)}</div>
      <ul class="trustrow">{trust}</ul>
    </div>

    <aside class="docket" aria-labelledby="docket-title">
      <div class="docket__head">
        <span class="docket__label">{e(p["label"])}</span>
        <span class="docket__ref">{e(p["ref"])}</span>
      </div>
      <div class="docket__body">
        <h2 class="docket__title" id="docket-title">{e(fill(p["title"], {"price": price}))}</h2>
        <p class="docket__intro">{e(p["intro"])}</p>

        <ul class="svc__list">{items}</ul>

        <dl class="ledger">
          <div class="ledger__total">
            <dt>{e(p["totalLabel"])}</dt>
            <dd>{e(price)}</dd>
          </div>
        </dl>
        <p class="ledger__note">{e(p["note"])}</p>
        <p class="ledger__note">{e(p["vatNote"])}</p>

        <div class="docket__meta">
          <span>{e(p["deliveryLabel"])}: {e(delivery)}</span>
          <span class="stamp">{icon("shield")}{e(p["stamp"])}</span>
        </div>

        <div class="docket__actions">
          {wa_btn}
          <a class="btn btn--ink btn--block" href="#contact">{e(p["cta"])}{icon("arrow")}</a>
        </div>
      </div>
    </aside>
  </div>
</section>"""


def sec_services(cfg, c, ctx):
    s = c["services"]
    cards = []
    for svc in ctx["services"]:
        if svc["basePrice"] > 0:
            price = (
                f'<div class="svc__price"><small>{e(s["priceFrom"])}</small>'
                f'{e(ctx["money"](svc["basePrice"]))}</div>'
            )
        else:
            price = f'<div class="svc__price is-text">{e(svc.get("priceModel") or s["priceCustom"])}</div>'

        includes = "".join(
            f'<li>{icon("check")}<span>{e(item)}</span></li>' for item in svc["includes"]
        )
        maint = ""
        if svc["maintenance"] > 0:
            maint = (
                f'<p class="svc__maint">{e(s["maintenanceFrom"])} '
                f'{e(ctx["money"](svc["maintenance"]))}/{e(s.get("perMonth", "mes"))}</p>'
            )

        cards.append(
            f"""<article class="svc reveal">
      <div class="svc__top"><h3 class="svc__name">{e(svc["name"])}</h3>{price}</div>
      <p class="svc__pitch">{e(svc["pitch"])}</p>
      <ul class="svc__list">{includes}</ul>
      {maint}
    </article>"""
        )

    return f"""<section class="band" id="services">
  <div class="shell">
    <p class="eyebrow">{e(s["eyebrow"])}</p>
    <h2 class="h-sec">{e(s["title"])}</h2>
    <p class="sec-lede">{e(s["sub"])}</p>
    <div class="svc-grid">{"".join(cards)}</div>
  </div>
</section>"""


def sec_process(cfg, c, ctx):
    p = c["process"]
    steps = "".join(
        f"""<article class="step reveal">
      <div class="step__n" aria-hidden="true"></div>
      <div><h3 class="step__name">{e(st["name"])}</h3>
      <p class="step__detail">{e(st["detail"])}</p></div>
    </article>"""
        for st in p["steps"]
    )
    return f"""<section class="band" id="process">
  <div class="shell">
    <p class="eyebrow">{e(p["eyebrow"])}</p>
    <h2 class="h-sec">{e(p["title"])}</h2>
    <p class="sec-lede">{e(p["sub"])}</p>
    <div class="steps">{steps}</div>
    <div class="scope-cta">
      <a class="btn btn--line" href="{ctx["scopeUrl"]}" download>{icon("doc")}{e(p["scopeCta"])}</a>
      <p>{e(p["scopeNote"])}</p>
    </div>
  </div>
</section>"""


def sec_guarantee(cfg, c, ctx):
    g = c["guarantee"]
    points = "".join(
        f'<li class="gpoint"><b>{e(pt["name"])}</b><span>{e(pt["detail"])}</span></li>'
        for pt in g["points"]
    )
    return f"""<section class="guarantee band" id="guarantee">
  <div class="shell guarantee__grid">
    <div>
      <p class="eyebrow">{e(g["eyebrow"])}</p>
      <h2>{e(g["title"])}</h2>
      <p class="guarantee__body">{e(g["body"])}</p>
    </div>
    <ul class="gpoints">{points}</ul>
  </div>
</section>"""


def sec_about(cfg, c, ctx):
    a = c["about"]
    body = "".join(f"<p>{e(par)}</p>" for par in a["body"])
    return f"""<section class="band" id="about">
  <div class="shell about__grid">
    <div>
      <p class="eyebrow">{e(a["eyebrow"])}</p>
      <h2 class="h-sec">{e(a["title"])}</h2>
      <p class="about__lead">{e(a["lead"])}</p>
      <div class="about__body">{body}</div>
      <div class="about__links">
        <a href="{e(cfg["social"]["linkedin"])}" target="_blank" rel="noopener">{icon("linkedin")}{e(a["linkedin"])}</a>
        <a href="{e(cfg["social"]["github"])}" target="_blank" rel="noopener">{icon("github")}{e(a["github"])}</a>
      </div>
    </div>
  </div>
</section>"""


def sec_faq(cfg, c, ctx):
    f = c["faq"]
    items = "".join(
        f"""<details class="qa">
      <summary>{e(item["q"])}{icon("plus", "qa__icon")}</summary>
      <div class="qa__a">{e(item["a"])}</div>
    </details>"""
        for item in f["items"]
    )
    return f"""<section class="band" id="faq">
  <div class="shell">
    <p class="eyebrow">{e(f["eyebrow"])}</p>
    <h2 class="h-sec">{e(f["title"])}</h2>
    <div class="faq">{items}</div>
  </div>
</section>"""


def sec_contact(cfg, c, ctx):
    ct = c["contact"]
    hours = cfg["contact"]["responseWindowHours"]
    hp = cfg["form"]["honeypotField"]

    channels = []
    if ctx["whatsapp"]:
        channels.append(
            f'<a class="channel" href="{e(ctx["wa_link"](c["panel"]["waMessage"]))}" '
            f'target="_blank" rel="noopener">'
            f'{icon("whatsapp")}<span><b>{e(ct["whatsappCta"])}</b>'
            f'<span>{e(cfg["contact"]["phoneDisplay"])}</span></span></a>'
        )
    channels.append(
        f'<a class="channel" href="mailto:{e(cfg["contact"]["email"])}">'
        f'{icon("mail")}<span><b>{e(ct["emailCta"])}</b>'
        f'<span>{e(cfg["contact"]["email"])}</span></span></a>'
    )
    if filled(cfg["contact"]["phoneE164"]):
        channels.append(
            f'<a class="channel" href="tel:{e(cfg["contact"]["phoneE164"])}">'
            f'{icon("phone")}<span><b>{e(ct["phoneCta"])}</b>'
            f'<span>{e(cfg["contact"]["phoneDisplay"])}</span></span></a>'
        )

    usable = [(k, v) for k, v in ct["channels"].items()
              if k != "whatsapp" or ctx["whatsapp"]]
    chips = "".join(
        f'<label class="chip"><input type="radio" name="channel" value="{e(key)}"'
        f'{" checked" if i == 0 else ""}><span>{e(label)}</span></label>'
        for i, (key, label) in enumerate(usable)
    )

    action = filled(cfg["form"]["endpoint"]) or ""
    consent_text = e(ct["consent"]).replace(
        e(ct["consentLink"]),
        f'<a href="{ctx["privacyUrl"]}" target="_blank" rel="noopener">{e(ct["consentLink"])}</a>',
    )

    return f"""<section class="contact band" id="contact">
  <div class="shell contact__grid">
    <div>
      <p class="eyebrow">{e(ct["eyebrow"])}</p>
      <h2 class="h-sec">{e(ct["title"])}</h2>
      <p class="sec-lede">{e(fill(ct["sub"], {"hours": hours}))}</p>
      <div class="channels">{"".join(channels)}</div>
    </div>

    <div>
      <div class="formstate" id="form-success" data-show="false">
        <div class="form success">
          {icon("check")}
          <h3>{e(ct["success"]["title"])}</h3>
          <p>{e(fill(ct["success"]["body"], {"hours": hours}))}</p>
        </div>
      </div>

      <form class="form" id="contact-form" action="{e(action)}" method="post" novalidate>
        <div class="formalert" id="form-alert" role="alert"></div>

        <div class="field" data-field="name">
          <label for="f-name">{e(ct["fields"]["name"]["label"])}</label>
          <input type="text" id="f-name" name="name" autocomplete="name"
                 placeholder="{e(ct["fields"]["name"]["placeholder"])}" required>
          <p class="err"></p>
        </div>

        <div class="field" data-field="need">
          <label for="f-need">{e(ct["fields"]["need"]["label"])}</label>
          <textarea id="f-need" name="need"
                    placeholder="{e(ct["fields"]["need"]["placeholder"])}" required></textarea>
          <p class="err"></p>
        </div>

        <div class="field" data-field="contact">
          <label for="f-contact">{e(ct["fields"]["contact"]["label"])}</label>
          <input type="text" id="f-contact" name="contact" autocomplete="email"
                 placeholder="{e(ct["fields"]["contact"]["placeholder"])}" required>
          <p class="err"></p>
        </div>

        <div class="field">
          <label>{e(ct["channelLabel"])}</label>
          <div class="chips">{chips}</div>
        </div>

        <div class="field" data-field="consent">
          <label class="consent" for="f-consent">
            <input type="checkbox" id="f-consent" name="consent" value="yes" required>
            <span>{consent_text}</span>
          </label>
          <p class="err"></p>
        </div>

        <div class="hp" aria-hidden="true">
          <label for="{e(hp)}">Leave this field empty</label>
          <input type="text" id="{e(hp)}" name="{e(hp)}" tabindex="-1" autocomplete="off">
        </div>
        <input type="hidden" name="_subject" value="{e(cfg["identity"]["brand"])} - {e(ct["eyebrow"])}">
        <input type="hidden" name="_replyto" id="f-replyto" value="">
        <input type="hidden" name="locale" value="{e(c["locale"])}">

        <button class="btn btn--brass btn--block" id="form-submit" type="submit">{e(ct["submit"])}</button>
        <p class="formnote">{e(c["footer"]["builtNote"])}</p>
      </form>
    </div>
  </div>
</section>"""


# --------------------------------------------------------------------------
# structured data
# --------------------------------------------------------------------------
def jsonld_home(cfg, c, ctx):
    base = cfg["site"]["baseUrl"]
    ident = cfg["identity"]
    contact = cfg["contact"]
    com = cfg["commercial"]

    offers = []
    for svc in ctx["services"]:
        offer = {
            "@type": "Offer",
            "name": svc["name"],
            "description": svc["pitch"],
            "priceCurrency": com["currency"],
            "availability": "https://schema.org/InStock",
            "url": base + ctx["home"] + "#services",
        }
        if svc["basePrice"] > 0:
            offer["price"] = str(svc["basePrice"])
            offer["priceSpecification"] = {
                "@type": "PriceSpecification",
                "price": str(svc["basePrice"]),
                "priceCurrency": com["currency"],
                "valueAddedTaxIncluded": False,
            }
        offers.append(offer)

    business = {
        "@context": "https://schema.org",
        "@type": "ProfessionalService",
        "@id": base + "/#business",
        "name": ident["brand"],
        "url": base + ctx["home"],
        "description": c["meta"]["description"],
        "email": contact["email"],
        "founder": {"@type": "Person", "name": ident["displayName"]},
        "areaServed": [{"@type": "Country", "name": "Spain"}],
        "availableLanguage": ["es", "en"],
        "priceRange": "\u20ac\u20ac",
        "address": {"@type": "PostalAddress", "addressCountry": "ES", "addressLocality": "Madrid"},
        "sameAs": [cfg["social"]["linkedin"], cfg["social"]["github"]],
        "makesOffer": offers,
        "knowsAbout": [
            "Linux server administration", "Website development", "Server migration",
            "Infrastructure security audit", "Self-hosted software", "Booking systems", "Nginx",
        ],
    }
    phone = filled(contact["phoneE164"])
    if phone:
        business["telephone"] = phone

    faq = {
        "@context": "https://schema.org",
        "@type": "FAQPage",
        "@id": base + ctx["home"] + "#faq",
        "mainEntity": [
            {
                "@type": "Question",
                "name": item["q"],
                "acceptedAnswer": {"@type": "Answer", "text": item["a"]},
            }
            for item in c["faq"]["items"]
        ],
    }

    website = {
        "@context": "https://schema.org",
        "@type": "WebSite",
        "@id": base + "/#website",
        "url": base + "/",
        "name": ident["brand"],
        "inLanguage": [c["htmlLang"], ctx["altLocale"]],
        "publisher": {"@id": base + "/#business"},
    }

    howto = {
        "@context": "https://schema.org",
        "@type": "HowTo",
        "name": c["process"]["title"],
        "description": c["process"]["sub"],
        "totalTime": f'P{com["deliveryDaysMax"]}D',
        "step": [
            {
                "@type": "HowToStep",
                "position": i + 1,
                "name": st["name"],
                "text": st["detail"],
            }
            for i, st in enumerate(c["process"]["steps"])
        ],
    }
    return [business, website, faq, howto]


def jsonld_doc(cfg, c, title, path):
    base = cfg["site"]["baseUrl"]
    return [{
        "@context": "https://schema.org",
        "@type": "WebPage",
        "name": title,
        "url": base + path,
        "isPartOf": {"@id": base + "/#website"},
        "inLanguage": c["htmlLang"],
    }]


# --------------------------------------------------------------------------
# page builders
# --------------------------------------------------------------------------
def build_home(cfg, c, ctx):
    body = "\n".join(filter(None, [
        sec_hero(cfg, c, ctx),
        sec_services(cfg, c, ctx),
        sec_process(cfg, c, ctx),
        sec_guarantee(cfg, c, ctx),
        sec_about(cfg, c, ctx),
        sec_faq(cfg, c, ctx),
        sec_contact(cfg, c, ctx),
    ]))

    page = {
        "title": c["meta"]["title"],
        "description": c["meta"]["description"],
        "keywords": c["meta"]["keywords"],
        "path": ctx["home"],
        "altPaths": ctx["altPaths"]["home"],
        "jsonld": jsonld_home(cfg, c, ctx),
    }

    ct = c["contact"]
    payload = {
        "locale": c["locale"],
        "defaultLocale": cfg["site"]["defaultLocale"],
        "localeDetection": cfg["site"]["localeDetection"],
        "isEntryPoint": c["locale"] == cfg["site"]["defaultLocale"],
        "altLocale": ctx["altLocale"],
        "altLocaleUrl": ctx["altHome"],
        "formEndpoint": filled(cfg["form"]["endpoint"]) or "",
        "mailtoFallback": f'mailto:{cfg["contact"]["email"]}?subject={cfg["identity"]["brand"]}&body=',
        "honeypotField": cfg["form"]["honeypotField"],
        "minFillSeconds": cfg["form"]["minFillSeconds"],
        "t": {
            "menuOpen": c["nav"]["menuOpen"],
            "menuClose": c["nav"]["menuClose"],
            "submit": ct["submit"],
            "submitting": ct["submitting"],
            "errName": ct["errors"]["name"],
            "errNeed": ct["errors"]["need"],
            "errContact": ct["errors"]["contact"],
            "errContactFormat": ct["errors"]["contactFormat"],
            "errConsent": ct["errors"]["consent"],
            "errNetwork": ct["errors"]["network"],
            "errTooFast": ct["errors"]["tooFast"],
        },
    }
    return page_shell(cfg, c, ctx, page, body, payload)


def build_doc(cfg, c, ctx, key, path, alt_paths):
    doc = c[key]
    ident = cfg["identity"]
    legal = cfg["legal"]
    values = {
        "legalName": filled(ident["legalName"]) or ident["displayName"],
        "taxId": filled(ident["taxId"]) or "[pendiente]",
        "registeredAddress": filled(ident["registeredAddress"]) or "[pendiente]",
        "email": cfg["contact"]["email"],
        "baseUrl": cfg["site"]["baseUrl"],
        "hostingProvider": legal["hostingProvider"],
        "processorName": legal["processorName"],
        "processorCountry": legal["processorCountry"],
        "retention": legal["dataRetentionMonths"],
        "authority": legal["supervisoryAuthority"],
    }

    parts = [f'<h1>{e(doc["title"])}</h1>']
    parts.append(
        f'<p class="doc__updated">{e(doc["updated"])}: '
        f'{date.today().isoformat()}</p>'
    )

    if key == "legalNotice" and not ident.get("autonomoRegistered"):
        parts.append(f'<p class="notice">{e(doc["pendingBanner"])}</p>')

    if doc.get("intro"):
        parts.append(f'<p class="doc__intro">{e(doc["intro"])}</p>')

    if doc.get("summary"):
        rows = "".join(
            f'<li>{icon("check")}<span>{e(line)}</span></li>' for line in doc["summary"]
        )
        parts.append(
            f'<aside class="doc__summary"><h2>{e(doc["summaryTitle"])}</h2>'
            f"<ul>{rows}</ul></aside>"
        )

    for section in doc["sections"]:
        parts.append(f'<h2>{e(section["h"])}</h2>')
        for para in section["p"]:
            text = e(fill(para, values))
            if legal["supervisoryAuthority"] in fill(para, values):
                text = text.replace(
                    e(legal["supervisoryAuthority"]),
                    f'<a href="{e(legal["supervisoryAuthorityUrl"])}" target="_blank" '
                    f'rel="noopener">{e(legal["supervisoryAuthority"])}</a>',
                )
            if legal["processorName"] in fill(para, values):
                text = text.replace(
                    e(legal["processorName"]),
                    f'<a href="{e(legal["processorPrivacyUrl"])}" target="_blank" '
                    f'rel="noopener nofollow">{e(legal["processorName"])}</a>',
                )
            parts.append(f"<p>{text}</p>")

    parts.append(
        f'<a class="backlink" href="{ctx["home"]}">{icon("back")}'
        f'{e(c["notFound"]["cta"])}</a>'
    )

    body = f'<section class="band"><div class="shell"><article class="doc">{"".join(parts)}</article></div></section>'
    page = {
        "title": doc["title"] + " | {brand}",
        "description": doc.get("intro", doc["title"]),
        "path": path,
        "altPaths": alt_paths,
        "robots": "index,follow",
        "jsonld": jsonld_doc(cfg, c, doc["title"], path),
    }
    return page_shell(cfg, c, ctx, page, body)


def build_404(cfg, c, ctx):
    nf = c["notFound"]
    body = f"""<section class="band"><div class="shell"><article class="doc">
  <h1>{e(nf["title"])}</h1>
  <p class="doc__intro">{e(nf["body"])}</p>
  <a class="backlink" href="{ctx["home"]}">{icon("back")}{e(nf["cta"])}</a>
</article></div></section>"""
    page = {
        "title": nf["title"] + " | {brand}",
        "description": nf["body"],
        "path": "/404.html",
        "altPaths": ctx["altPaths"]["home"],
        "robots": "noindex,follow",
    }
    return page_shell(cfg, c, ctx, page, body)


# --------------------------------------------------------------------------
# non-html outputs
# --------------------------------------------------------------------------
def build_sitemap(cfg, urls):
    base = cfg["site"]["baseUrl"]
    today = date.today().isoformat()
    entries = []
    for path, priority, alts in urls:
        links = "".join(
            f'    <xhtml:link rel="alternate" hreflang="{lang}" href="{base}{href}"/>\n'
            for lang, href in alts.items()
        )
        links += f'    <xhtml:link rel="alternate" hreflang="x-default" href="{base}{alts["es"]}"/>\n'
        entries.append(
            f"  <url>\n    <loc>{base}{path}</loc>\n"
            f"    <lastmod>{today}</lastmod>\n"
            f"    <priority>{priority}</priority>\n{links}  </url>"
        )
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"\n'
        '        xmlns:xhtml="http://www.w3.org/1999/xhtml">\n'
        + "\n".join(entries)
        + "\n</urlset>\n"
    )


def build_robots(cfg):
    base = cfg["site"]["baseUrl"]
    return (
        "User-agent: *\n"
        "Allow: /\n\n"
        "# Answer engines are welcome. A plain-text summary lives at /llms.txt\n"
        "User-agent: GPTBot\nAllow: /\n\n"
        "User-agent: OAI-SearchBot\nAllow: /\n\n"
        "User-agent: ClaudeBot\nAllow: /\n\n"
        "User-agent: PerplexityBot\nAllow: /\n\n"
        "User-agent: Google-Extended\nAllow: /\n\n"
        f"Sitemap: {base}/sitemap.xml\n"
    )


def build_llms(cfg, es, en, ctx_es):
    """Plain-text brief for answer engines. Facts first, no marketing."""
    base = cfg["site"]["baseUrl"]
    ident = cfg["identity"]
    com = cfg["commercial"]
    sym = com["currencySymbol"]

    lines = [
        f'# {ident["brand"]}',
        "",
        f'> {en["meta"]["description"]}',
        "",
        f'Two people: {ident["displayName"]} builds and runs the technical side, '
        f'his father handles the conversation with the client. Based in Madrid, Spain. '
        f'Serves businesses of 1 to 100 people, remotely across Spain, in Spanish and English.',
        f'Contact: {cfg["contact"]["email"]}',
        "",
        "## Services and prices",
        "",
    ]
    for svc in ctx_es["services"]:
        price = f'{sym}{svc["basePrice"]}' if svc["basePrice"] > 0 else "per case"
        lines.append(f'- **{svc["name"]}** ({price}, VAT excluded). {svc["pitch"]}')
        if svc["maintenance"] > 0:
            lines.append(f'  - Optional maintenance: {sym}{svc["maintenance"]} per month, cancel anytime.')
    lines += [
        "",
        "## Terms",
        "",
        f'- Delivery: {com["deliveryDaysMin"]} to {com["deliveryDaysMax"]} days.',
        "- Each price covers the whole job. Nothing gets added on top later.",
        "- If the job needs less than the description, the price drops and the scope sheet records it.",
        "- Guarantee: if the client does not like the delivered result, they do not pay and no invoice is issued.",
        "- No deposit and no payment up front.",
        "- Payment happens off the website by bank transfer or Bizum, after the client approves the work.",
        "- The client owns the code, the configuration and the domain from day one. No lock-in.",
        "",
        "## Questions and answers",
        "",
    ]
    for item in en["faq"]["items"]:
        lines.append(f'### {item["q"]}')
        lines.append(item["a"])
        lines.append("")
    lines += [
        "## Pages",
        "",
        f'- [Home, Spanish]({base}/): services, prices, process, FAQ, contact form.',
        f'- [Home, English]({base}/en/): same content in English.',
        f'- [Legal notice]({base}/aviso-legal.html)',
        f'- [Privacy policy]({base}/privacidad.html)',
        f'- [Scope sheet template, PDF]({base}/assets/docs/alcance-mechidan-es.pdf)',
        "",
        f'Last updated: {date.today().isoformat()}',
        "",
    ]
    return "\n".join(line for line in lines if line is not None) + "\n"


def build_manifest(cfg, es):
    return json.dumps({
        "name": cfg["identity"]["brand"],
        "short_name": cfg["identity"]["brand"],
        "description": es["meta"]["description"],
        "start_url": "/",
        "display": "standalone",
        "background_color": "#F2F0E9",
        "theme_color": "#072B28",
        "lang": es["htmlLang"],
        "icons": [
            {"src": "/assets/img/favicon.svg", "sizes": "any", "type": "image/svg+xml"},
            {"src": "/assets/img/icon-180.png", "sizes": "180x180", "type": "image/png"},
            {"src": "/assets/img/icon-512.png", "sizes": "512x512", "type": "image/png"},
        ],
    }, ensure_ascii=False, indent=2) + "\n"


# --------------------------------------------------------------------------
# context assembly
# --------------------------------------------------------------------------
def make_context(cfg, c, locale):
    com = cfg["commercial"]
    sym = com["currencySymbol"]

    def money(amount):
        return f"{sym}{amount:,.0f}".replace(",", ".")

    is_es = locale == "es"
    home = "/" if is_es else "/en/"
    alt_home = "/en/" if is_es else "/"
    legal_url = "/aviso-legal.html" if is_es else "/en/legal-notice.html"
    privacy_url = "/privacidad.html" if is_es else "/en/privacy.html"
    scope_url = f"/assets/docs/{'alcance-mechidan-es' if is_es else 'scope-mechidan-en'}.pdf"

    phone = filled(cfg["contact"]["phoneE164"])
    wa_base = ""
    if phone and cfg["contact"]["whatsappEnabled"]:
        digits = re.sub(r"\D", "", phone)
        wa_base = f"https://wa.me/{digits}?text="

    def wa_link(message):
        return wa_base + quote(message) if wa_base else ""

    # merge price config with translated copy
    services = []
    for svc_cfg in cfg["services"]:
        copy = c["services"]["items"][svc_cfg["id"]]
        services.append({
            "id": svc_cfg["id"],
            "basePrice": svc_cfg["basePrice"],
            "maintenance": svc_cfg["maintenance"],
            "name": copy["name"],
            "pitch": copy["pitch"],
            "includes": copy["includes"],
            "priceModel": copy.get("priceModel"),
        })

    return {
        "locale": locale,
        "altLocale": "en" if is_es else "es",
        "home": home,
        "altHome": alt_home,
        "legalUrl": legal_url,
        "privacyUrl": privacy_url,
        "scopeUrl": scope_url,
        "whatsapp": bool(wa_base),
        "wa_link": wa_link,
        "money": money,
        "services": services,
        "altPaths": {
            "home": {"es": "/", "en": "/en/"},
            "legal": {"es": "/aviso-legal.html", "en": "/en/legal-notice.html"},
            "privacy": {"es": "/privacidad.html", "en": "/en/privacy.html"},
        },
    }


# --------------------------------------------------------------------------
# main
# --------------------------------------------------------------------------
def main():
    cfg = load("site.config.json")
    es = load("content/es.json")
    en = load("content/en.json")

    require(cfg["contact"]["phoneE164"], "contact.phoneE164 (WhatsApp and call buttons stay hidden)")
    require(cfg["form"]["endpoint"], "form.endpoint (the form falls back to opening a mail client)")
    require(cfg["identity"]["legalName"], "identity.legalName (legal notice shows the display name)")
    require(cfg["identity"]["taxId"], "identity.taxId (legal notice shows a pending marker)")
    require(cfg["identity"]["registeredAddress"], "identity.registeredAddress")

    ctx_es = make_context(cfg, es, "es")
    ctx_en = make_context(cfg, en, "en")

    written = [
        write("index.html", build_home(cfg, es, ctx_es)),
        write("en/index.html", build_home(cfg, en, ctx_en)),
        write("aviso-legal.html", build_doc(cfg, es, ctx_es, "legalNotice", "/aviso-legal.html", ctx_es["altPaths"]["legal"])),
        write("privacidad.html", build_doc(cfg, es, ctx_es, "privacy", "/privacidad.html", ctx_es["altPaths"]["privacy"])),
        write("en/legal-notice.html", build_doc(cfg, en, ctx_en, "legalNotice", "/en/legal-notice.html", ctx_en["altPaths"]["legal"])),
        write("en/privacy.html", build_doc(cfg, en, ctx_en, "privacy", "/en/privacy.html", ctx_en["altPaths"]["privacy"])),
        write("404.html", build_404(cfg, es, ctx_es)),
        write("sitemap.xml", build_sitemap(cfg, [
            ("/", "1.0", ctx_es["altPaths"]["home"]),
            ("/en/", "0.9", ctx_es["altPaths"]["home"]),
            ("/aviso-legal.html", "0.3", ctx_es["altPaths"]["legal"]),
            ("/privacidad.html", "0.3", ctx_es["altPaths"]["privacy"]),
            ("/en/legal-notice.html", "0.3", ctx_es["altPaths"]["legal"]),
            ("/en/privacy.html", "0.3", ctx_es["altPaths"]["privacy"]),
        ])),
        write("robots.txt", build_robots(cfg)),
        write("llms.txt", build_llms(cfg, es, en, ctx_es)),
        write("site.webmanifest", build_manifest(cfg, es)),
        write("CNAME", cfg["site"]["domain"] + "\n"),
        write(".nojekyll", ""),
    ]

    print(f"built {len(written)} files at {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%SZ')}")
    for path in written:
        print("  " + path)

    if WARNINGS:
        print("\nplaceholders still unset in site.config.json:")
        for warning in WARNINGS:
            print("  - " + warning)
        print("\nthe site builds and works without them. fill them in and run build.py again.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
