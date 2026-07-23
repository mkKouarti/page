#!/usr/bin/env python3
"""
Mechidan checks.

  python3 check.py         verify the built site
  python3 check.py dns     print the DNS records to enter at Porkbun

Stdlib only. Exits non-zero when a check fails, so `make deploy` stops
before pushing a broken build.
"""

import glob
import io
import json
import os
import re
import sys
import xml.dom.minidom as minidom

ROOT = os.path.dirname(os.path.abspath(__file__))

# GitHub Pages apex addresses, per GitHub's own documentation
PAGES_A = ["185.199.108.153", "185.199.109.153", "185.199.110.153", "185.199.111.153"]
PAGES_AAAA = ["2606:50c0:8000::153", "2606:50c0:8001::153",
              "2606:50c0:8002::153", "2606:50c0:8003::153"]


def config():
    with open(os.path.join(ROOT, "site.config.json"), encoding="utf-8") as fh:
        return json.load(fh)


def pages():
    os.chdir(ROOT)
    return sorted(glob.glob("*.html") + glob.glob("en/*.html"))


def check():
    failures = []
    notes = []
    os.chdir(ROOT)

    html_files = pages()
    if not html_files:
        failures.append("no HTML found, run build.py first")
        return failures, notes

    for path in html_files:
        source = io.open(path, encoding="utf-8").read()

        # structured data must parse
        for block in re.findall(r'<script type="application/ld\+json">(.*?)</script>',
                                source, re.S):
            try:
                json.loads(block)
            except json.JSONDecodeError as exc:
                failures.append(f"{path}: broken JSON-LD, {exc}")

        # the runtime payload must parse
        payload = re.search(r'<script type="application/json" id="site-data">(.*?)</script>',
                            source, re.S)
        if payload:
            try:
                json.loads(payload.group(1))
            except json.JSONDecodeError as exc:
                failures.append(f"{path}: broken site-data payload, {exc}")

        # every root-relative reference must resolve on disk
        for href in re.findall(r'(?:href|src)="(/[^"#?]*)"', source):
            target = href.lstrip("/") or "index.html"
            if target.endswith("/"):
                target += "index.html"
            if not os.path.exists(target):
                failures.append(f"{path}: {href} points at nothing")

        # accessibility and SEO essentials
        if len(re.findall(r"<h1[\s>]", source)) != 1:
            failures.append(f"{path}: needs exactly one h1")
        if 'rel="canonical"' not in source:
            failures.append(f"{path}: missing canonical link")
        if 'hreflang="x-default"' not in source:
            failures.append(f"{path}: missing x-default hreflang")
        if re.search(r"<img(?![^>]*\balt=)", source):
            failures.append(f"{path}: an img tag has no alt attribute")

    for path in ("sitemap.xml", "site.webmanifest", "robots.txt", "llms.txt", "CNAME"):
        if not os.path.exists(path):
            failures.append(f"{path} is missing")

    if os.path.exists("sitemap.xml"):
        try:
            minidom.parse("sitemap.xml")
        except Exception as exc:
            failures.append(f"sitemap.xml does not parse, {exc}")

    if os.path.exists("site.webmanifest"):
        try:
            json.load(io.open("site.webmanifest", encoding="utf-8"))
        except json.JSONDecodeError as exc:
            failures.append(f"site.webmanifest does not parse, {exc}")

    cfg = config()
    if os.path.exists("CNAME"):
        declared = io.open("CNAME", encoding="utf-8").read().strip()
        if declared != cfg["site"]["domain"]:
            failures.append(f"CNAME says {declared}, config says {cfg['site']['domain']}")

    # the two locales must describe the same services
    es = json.load(io.open("content/es.json", encoding="utf-8"))
    en = json.load(io.open("content/en.json", encoding="utf-8"))
    for svc in cfg["services"]:
        for locale, content in (("es", es), ("en", en)):
            item = content["services"]["items"].get(svc["id"])
            if item is None:
                failures.append(f"content/{locale}.json has no copy for service '{svc['id']}'")
                continue
            for addon in svc["addons"]:
                if addon["id"] not in item.get("addons", {}):
                    failures.append(
                        f"content/{locale}.json: service '{svc['id']}' has no copy "
                        f"for add-on '{addon['id']}'"
                    )

    # placeholders are worth flagging but do not fail the build
    def unset(value):
        return isinstance(value, str) and value.startswith("FILL_ME")

    for label, value in (
        ("contact.phoneE164", cfg["contact"]["phoneE164"]),
        ("form.endpoint", cfg["form"]["endpoint"]),
        ("identity.legalName", cfg["identity"]["legalName"]),
        ("identity.taxId", cfg["identity"]["taxId"]),
        ("identity.registeredAddress", cfg["identity"]["registeredAddress"]),
    ):
        if unset(value):
            notes.append(label)

    return failures, notes


def dns():
    cfg = config()
    domain = cfg["site"]["domain"]
    user = cfg["site"]["githubRepo"].split("/")[0]

    print(f"DNS records for {domain}")
    print("Porkbun -> your domain -> Details -> DNS Records\n")
    print(f'{"TYPE":<7}{"HOST":<10}{"ANSWER"}')
    print("-" * 46)
    for address in PAGES_A:
        print(f'{"A":<7}{"(blank)":<10}{address}')
    for address in PAGES_AAAA:
        print(f'{"AAAA":<7}{"(blank)":<10}{address}')
    print(f'{"CNAME":<7}{"www":<10}{user}.github.io')
    print("\nDelete any parking or forwarding records Porkbun added by default,")
    print("or the apex will not resolve to GitHub.\n")
    print("Verify once propagated:")
    print(f"  dig {domain} +noall +answer -t A")
    print(f"  dig www.{domain} +noall +answer -t CNAME")


def main():
    if len(sys.argv) > 1 and sys.argv[1] == "dns":
        dns()
        return 0

    failures, notes = check()

    if failures:
        print(f"{len(failures)} problem(s) found:")
        for item in failures:
            print("  " + item)
        return 1

    print(f"checks passed across {len(pages())} pages")
    if notes:
        print("\nplaceholders still unset in site.config.json:")
        for item in notes:
            print("  - " + item)
    return 0


if __name__ == "__main__":
    sys.exit(main())
