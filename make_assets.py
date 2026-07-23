#!/usr/bin/env python3
"""
Mechidan asset builder.

Generates, from site.config.json and content/<locale>.json:
  assets/docs/alcance-mechidan-es.pdf   scope of work template, Spanish
  assets/docs/scope-mechidan-en.pdf     scope of work template, English
  assets/img/favicon.svg
  assets/img/icon-180.png, icon-512.png
  assets/img/og.png                     1200x630 social card

Needs:  pip install reportlab pillow fonttools brotli
Run:    python3 make_assets.py
Idempotent. Safe to run repeatedly.
"""

import io
import json
import os
import sys
from datetime import date

from fontTools.ttLib import TTFont
from fontTools.varLib import instancer
from PIL import Image, ImageDraw, ImageFont
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont as RLTTFont
from reportlab.platypus import (
    BaseDocTemplate, Frame, PageTemplate, Paragraph, Spacer, Table, TableStyle,
)

ROOT = os.path.dirname(os.path.abspath(__file__))
FONT_DIR = os.path.join(ROOT, "assets", "fonts")
BUILD_DIR = os.path.join(ROOT, ".fontcache")

PAPER = colors.HexColor("#F2F0E9")
INK = colors.HexColor("#12211D")
SLATE = colors.HexColor("#55645E")
PETROL = colors.HexColor("#0D4A45")
PETROL_DEEP = colors.HexColor("#072B28")
BRASS = colors.HexColor("#9A6E06")
RULE = colors.HexColor("#CFD4CB")


def load(path):
    with open(os.path.join(ROOT, path), encoding="utf-8") as fh:
        return json.load(fh)


# --------------------------------------------------------------------------
# variable woff2 -> static ttf, so the PDF and the site share one typeface
# --------------------------------------------------------------------------
def static_ttf(source, out_name, axes):
    os.makedirs(BUILD_DIR, exist_ok=True)
    out = os.path.join(BUILD_DIR, out_name)
    if os.path.exists(out):
        return out
    font = TTFont(os.path.join(FONT_DIR, source))
    font = instancer.instantiateVariableFont(font, axes, inplace=False)
    font.flavor = None
    font.save(out)
    return out


def register_fonts():
    faces = {
        "Brand": static_ttf("archivo-var.woff2", "archivo-700.ttf", {"wght": 700, "wdth": 105}),
        "Body": static_ttf("publicsans-var.woff2", "publicsans-400.ttf", {"wght": 400}),
        "Body-Bold": static_ttf("publicsans-var.woff2", "publicsans-650.ttf", {"wght": 650}),
        "Data": static_ttf("jetbrainsmono-var.woff2", "jbmono-500.ttf", {"wght": 500}),
        "Data-Bold": static_ttf("jetbrainsmono-var.woff2", "jbmono-700.ttf", {"wght": 700}),
    }
    for name, path in faces.items():
        pdfmetrics.registerFont(RLTTFont(name, path))
    pdfmetrics.registerFontFamily("Body", normal="Body", bold="Body-Bold",
                                  italic="Body", boldItalic="Body-Bold")
    return faces


# --------------------------------------------------------------------------
# scope of work pdf
# --------------------------------------------------------------------------
def scope_pdf(cfg, c, out_path):
    doc_copy = c["scopeDoc"]
    ident = cfg["identity"]
    com = cfg["commercial"]

    styles = {
        "h1": ParagraphStyle("h1", fontName="Brand", fontSize=21, leading=24,
                             textColor=INK, spaceAfter=3),
        "sub": ParagraphStyle("sub", fontName="Body", fontSize=9.5, leading=13,
                              textColor=SLATE, spaceAfter=12),
        "intro": ParagraphStyle("intro", fontName="Body", fontSize=10, leading=15,
                                textColor=INK, spaceAfter=4),
        "h2": ParagraphStyle("h2", fontName="Body-Bold", fontSize=10.5, leading=14,
                             textColor=PETROL, spaceBefore=11, spaceAfter=3),
        "p": ParagraphStyle("p", fontName="Body", fontSize=9.5, leading=14,
                            textColor=SLATE, alignment=TA_LEFT),
        "meta": ParagraphStyle("meta", fontName="Data", fontSize=8, leading=11,
                               textColor=SLATE),
        "metaVal": ParagraphStyle("metaVal", fontName="Data-Bold", fontSize=8.5,
                                  leading=11, textColor=INK),
        "foot": ParagraphStyle("foot", fontName="Data", fontSize=7.2, leading=10,
                               textColor=SLATE),
    }

    page_w, page_h = A4
    margin = 20 * mm

    def decorate(canvas, _doc):
        canvas.saveState()
        # top rule in brand colours
        canvas.setFillColor(PETROL_DEEP)
        canvas.rect(0, page_h - 9 * mm, page_w, 9 * mm, stroke=0, fill=1)
        canvas.setFillColor(BRASS)
        canvas.rect(0, page_h - 10.6 * mm, page_w, 1.6 * mm, stroke=0, fill=1)
        # wordmark
        canvas.setFillColor(PAPER)
        canvas.setFont("Brand", 9.5)
        canvas.drawString(margin, page_h - 6.4 * mm, ident["brand"].upper())
        canvas.setFont("Data", 7.5)
        canvas.drawRightString(page_w - margin, page_h - 6.3 * mm, cfg["site"]["domain"])
        # footer
        canvas.setFillColor(SLATE)
        canvas.setFont("Data", 7)
        canvas.drawString(margin, 11 * mm, doc_copy["footerNote"])
        canvas.drawRightString(page_w - margin, 11 * mm, f"{_doc.page}")
        canvas.setStrokeColor(RULE)
        canvas.setLineWidth(0.5)
        canvas.line(margin, 15 * mm, page_w - margin, 15 * mm)
        canvas.restoreState()

    frame = Frame(margin, 19 * mm, page_w - 2 * margin, page_h - margin - 19 * mm,
                  leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0)
    pdf = BaseDocTemplate(
        out_path, pagesize=A4,
        title=f'{doc_copy["docTitle"]} | {ident["brand"]}',
        author=ident["displayName"],
        subject=doc_copy["subtitle"],
        creator=cfg["site"]["baseUrl"],
    )
    pdf.addPageTemplates([PageTemplate(id="main", frames=[frame], onPage=decorate)])

    story = [
        Spacer(1, 6 * mm),
        Paragraph(doc_copy["docTitle"], styles["h1"]),
        Paragraph(doc_copy["subtitle"], styles["sub"]),
    ]

    meta = [
        [Paragraph(doc_copy["preparedBy"].upper(), styles["meta"]),
         Paragraph(doc_copy["preparedFor"].upper(), styles["meta"]),
         Paragraph(doc_copy["date"].upper(), styles["meta"])],
        [Paragraph(ident["displayName"], styles["metaVal"]),
         Paragraph(doc_copy["placeholderClient"], styles["metaVal"]),
         Paragraph(date.today().isoformat(), styles["metaVal"])],
    ]
    col = (page_w - 2 * margin) / 3.0
    meta_table = Table(meta, colWidths=[col] * 3)
    meta_table.setStyle(TableStyle([
        ("LINEABOVE", (0, 0), (-1, 0), 1.1, INK),
        ("LINEBELOW", (0, -1), (-1, -1), 0.5, RULE),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]))
    story += [meta_table, Spacer(1, 6 * mm),
              Paragraph(doc_copy["intro"], styles["intro"]), Spacer(1, 2 * mm)]

    for section in doc_copy["sections"]:
        story.append(Paragraph(section["h"], styles["h2"]))
        for para in section["p"]:
            story.append(Paragraph(para.replace("{baseUrl}", cfg["site"]["baseUrl"]), styles["p"]))

    story.append(Spacer(1, 9 * mm))
    sign = Table(
        [[Paragraph(doc_copy["signature"] + " " + ident["displayName"], styles["meta"]),
          Paragraph(doc_copy["signature"] + " " + doc_copy["placeholderClient"], styles["meta"])]],
        colWidths=[(page_w - 2 * margin) / 2.0] * 2, rowHeights=[16 * mm],
    )
    sign.setStyle(TableStyle([
        ("LINEBELOW", (0, 0), (-1, -1), 0.8, INK),
        ("VALIGN", (0, 0), (-1, -1), "BOTTOM"),
        ("LEFTPADDING", (0, 0), (0, 0), 0),
        ("LEFTPADDING", (1, 0), (1, 0), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    story.append(sign)

    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    pdf.build(story)
    return out_path


# --------------------------------------------------------------------------
# images
# --------------------------------------------------------------------------
FAVICON = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32">
  <rect width="32" height="32" rx="7" fill="#072B28"/>
  <path d="M9 11.5 13.6 16 9 20.5" stroke="#F2F0E9" stroke-width="2.6"
        stroke-linecap="round" stroke-linejoin="round" fill="none"/>
  <path d="M16.8 21h6.4" stroke="#C9930E" stroke-width="2.6" stroke-linecap="round"/>
</svg>
"""


def icon_png(size, out_path):
    scale = 4
    img = Image.new("RGBA", (size * scale, size * scale), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    s = size * scale
    d.rounded_rectangle([0, 0, s - 1, s - 1], radius=int(s * 0.22), fill="#072B28")
    lw = max(2, int(s * 0.082))
    x0, y0 = s * 0.28, s * 0.36
    d.line([(x0, y0), (x0 + s * 0.145, s * 0.5), (x0, s * 0.64)],
           fill="#F2F0E9", width=lw, joint="curve")
    d.line([(s * 0.525, s * 0.655), (s * 0.725, s * 0.655)], fill="#C9930E", width=lw)
    img = img.resize((size, size), Image.LANCZOS)
    img.save(out_path)
    return out_path


def og_png(cfg, c, faces, out_path):
    W, H = 1200, 630
    img = Image.new("RGB", (W, H), "#072B28")
    d = ImageDraw.Draw(img)

    # faint diagonal texture
    for x in range(-H, W, 14):
        d.line([(x, 0), (x + H, H)], fill="#0B322E", width=2)

    d.rectangle([0, 0, W, 10], fill="#C9930E")

    brand = ImageFont.truetype(faces["Brand"], 74)
    brand_sm = ImageFont.truetype(faces["Brand"], 27)
    body = ImageFont.truetype(faces["Body"], 25)
    data = ImageFont.truetype(faces["Data"], 20)

    pad = 74
    d.text((pad, 62), cfg["identity"]["brand"].upper(), font=brand_sm, fill="#F2F0E9")
    d.text((W - pad, 66), cfg["site"]["domain"], font=data, fill="#8FA9A2", anchor="ra")

    h = c["hero"]
    d.text((pad, 170), h["h1Lead"], font=brand, fill="#F2F0E9")
    d.text((pad, 258), h["h1Accent"], font=brand, fill="#E8B93A")

    d.line([(pad, 386), (pad + 92, 386)], fill="#C9930E", width=4)

    # wrap the subtitle on word boundaries within the card width
    max_w = W - pad * 2
    words, line, rows = h["sub"].split(), "", []
    for word in words:
        trial = (line + " " + word).strip()
        if d.textlength(trial, font=body) <= max_w:
            line = trial
        else:
            rows.append(line)
            line = word
        if len(rows) == 2:
            break
    if line and len(rows) < 2:
        rows.append(line)
    for i, row in enumerate(rows):
        d.text((pad, 412 + i * 36), row, font=body, fill="#B9CCC6")

    y = 530
    for item in h["trust"][:3]:
        d.ellipse([pad, y + 7, pad + 9, y + 16], fill="#C9930E")
        d.text((pad + 22, y), item, font=data, fill="#8FA9A2")
        y += 34

    img.save(out_path, quality=92)
    return out_path


# --------------------------------------------------------------------------
def main():
    cfg = load("site.config.json")
    es = load("content/es.json")
    en = load("content/en.json")
    faces = register_fonts()

    made = [
        scope_pdf(cfg, es, os.path.join(ROOT, "assets/docs/alcance-mechidan-es.pdf")),
        scope_pdf(cfg, en, os.path.join(ROOT, "assets/docs/scope-mechidan-en.pdf")),
    ]

    img_dir = os.path.join(ROOT, "assets", "img")
    os.makedirs(img_dir, exist_ok=True)
    with open(os.path.join(img_dir, "favicon.svg"), "w", encoding="utf-8") as fh:
        fh.write(FAVICON)
    made.append(os.path.join(img_dir, "favicon.svg"))
    made.append(icon_png(180, os.path.join(img_dir, "icon-180.png")))
    made.append(icon_png(512, os.path.join(img_dir, "icon-512.png")))
    made.append(og_png(cfg, es, faces, os.path.join(img_dir, "og.png")))

    print(f"built {len(made)} assets")
    for path in made:
        print("  " + os.path.relpath(path, ROOT))
    return 0


if __name__ == "__main__":
    sys.exit(main())
