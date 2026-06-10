"""Build the GDPR RAG Pipeline presentation."""

from pptx import Presentation
from pptx.util import Inches, Pt, Emu
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
import os

HERE = os.path.dirname(os.path.abspath(__file__))

# ── Color palette ───────────────────────────────────────────────────────────
DARK_BG    = RGBColor(0x0D, 0x1B, 0x2A)   # deep navy
ACCENT     = RGBColor(0x00, 0xC8, 0xFF)   # electric cyan
ACCENT2    = RGBColor(0xFF, 0x6B, 0x35)   # orange (warnings/highlights)
WHITE      = RGBColor(0xFF, 0xFF, 0xFF)
LIGHT_GREY = RGBColor(0xB0, 0xBE, 0xC5)
MID_GREY   = RGBColor(0x37, 0x47, 0x4F)
GREEN      = RGBColor(0x00, 0xE5, 0x76)
RED        = RGBColor(0xFF, 0x3B, 0x3B)

# ── Slide dimensions (16:9 widescreen) ──────────────────────────────────────
SLIDE_W = Inches(13.33)
SLIDE_H = Inches(7.5)

prs = Presentation()
prs.slide_width  = SLIDE_W
prs.slide_height = SLIDE_H

blank_layout = prs.slide_layouts[6]   # completely blank


# ── Helper utilities ────────────────────────────────────────────────────────

def add_rect(slide, x, y, w, h, fill_rgb=None, alpha=None, line_rgb=None, line_w=Pt(0)):
    shape = slide.shapes.add_shape(1, x, y, w, h)   # MSO_SHAPE.RECTANGLE = 1
    shape.line.width = line_w
    if line_rgb:
        shape.line.color.rgb = line_rgb
    else:
        shape.line.fill.background()
    if fill_rgb:
        shape.fill.solid()
        shape.fill.fore_color.rgb = fill_rgb
    else:
        shape.fill.background()
    return shape


def add_text(slide, text, x, y, w, h,
             font_size=18, bold=False, italic=False,
             color=WHITE, align=PP_ALIGN.LEFT,
             word_wrap=True):
    txBox = slide.shapes.add_textbox(x, y, w, h)
    txBox.word_wrap = word_wrap
    tf = txBox.text_frame
    tf.word_wrap = word_wrap
    p = tf.paragraphs[0]
    p.alignment = align
    run = p.add_run()
    run.text = text
    run.font.size  = Pt(font_size)
    run.font.bold  = bold
    run.font.italic = italic
    run.font.color.rgb = color
    return txBox


def add_multiline(slide, lines, x, y, w, h,
                  font_size=16, color=WHITE, bold=False,
                  line_spacing=1.2, align=PP_ALIGN.LEFT):
    """Each item in lines is either a string or (text, color, bold) tuple."""
    from pptx.util import Pt
    from pptx.oxml.ns import qn
    from lxml import etree

    txBox = slide.shapes.add_textbox(x, y, w, h)
    txBox.word_wrap = True
    tf = txBox.text_frame
    tf.word_wrap = True

    first = True
    for item in lines:
        if isinstance(item, str):
            txt, clr, bld = item, color, bold
        else:
            txt, clr, bld = item

        if first:
            p = tf.paragraphs[0]
            first = False
        else:
            p = tf.add_paragraph()

        p.alignment = align
        run = p.add_run()
        run.text = txt
        run.font.size  = Pt(font_size)
        run.font.bold  = bld
        run.font.color.rgb = clr

    return txBox


def fill_background(slide, color=DARK_BG):
    add_rect(slide, 0, 0, SLIDE_W, SLIDE_H, fill_rgb=color)


def add_top_bar(slide, height=Inches(0.08)):
    add_rect(slide, 0, 0, SLIDE_W, height, fill_rgb=ACCENT)


def add_slide_number(slide, n, total=12):
    add_text(slide, f"{n} / {total}",
             SLIDE_W - Inches(1.2), SLIDE_H - Inches(0.45),
             Inches(1.0), Inches(0.35),
             font_size=11, color=LIGHT_GREY, align=PP_ALIGN.RIGHT)


def section_label(slide, text, x=Inches(0.55), y=Inches(0.18)):
    add_text(slide, text.upper(), x, y, Inches(4), Inches(0.35),
             font_size=10, color=ACCENT, bold=True)


# ════════════════════════════════════════════════════════════════════════════
# SLIDE 1 — COVER
# ════════════════════════════════════════════════════════════════════════════
s = prs.slides.add_slide(blank_layout)
fill_background(s)

# left accent bar
add_rect(s, 0, 0, Inches(0.18), SLIDE_H, fill_rgb=ACCENT)

# bottom strip
add_rect(s, 0, SLIDE_H - Inches(0.9), SLIDE_W, Inches(0.9), fill_rgb=MID_GREY)

# title
add_text(s, "GDPR Intelligence Platform",
         Inches(0.55), Inches(1.6), Inches(8.5), Inches(1.5),
         font_size=46, bold=True, color=WHITE)

add_text(s, "AI-Powered Legal Document Retrieval at Scale",
         Inches(0.55), Inches(3.15), Inches(9), Inches(0.8),
         font_size=22, color=ACCENT)

add_text(s, "Retrieval-Augmented Generation · Azure · Databricks · GDPR Compliance",
         Inches(0.55), Inches(4.0), Inches(9.5), Inches(0.6),
         font_size=14, color=LIGHT_GREY)

# team / date bottom strip
add_text(s, "Team 6  |  Accenture 2026  |  June 2026",
         Inches(0.55), SLIDE_H - Inches(0.78), Inches(7), Inches(0.55),
         font_size=13, color=LIGHT_GREY)

add_slide_number(s, 1)


# ════════════════════════════════════════════════════════════════════════════
# SLIDE 2 — THE HOOK  (Zuckerberg + GDPR fine)
# ════════════════════════════════════════════════════════════════════════════
s = prs.slides.add_slide(blank_layout)
fill_background(s)
add_top_bar(s)

# dark overlay on right side for image area
add_rect(s, Inches(6.5), 0, Inches(6.83), SLIDE_H, fill_rgb=RGBColor(0x07, 0x11, 0x1A))

# image
img_path = os.path.join(HERE, "zuckeberg_eu_court.jpg")
if os.path.exists(img_path):
    s.shapes.add_picture(img_path, Inches(6.7), Inches(0.4),
                         Inches(6.2), Inches(6.5))

# red badge
add_rect(s, Inches(0.45), Inches(0.8), Inches(5.7), Inches(0.7),
         fill_rgb=RED)
add_text(s, "€1,200,000,000 FINE",
         Inches(0.5), Inches(0.82), Inches(5.5), Inches(0.62),
         font_size=28, bold=True, color=WHITE, align=PP_ALIGN.CENTER)

add_text(s, '"He got it wrong."',
         Inches(0.45), Inches(1.7), Inches(5.8), Inches(1.0),
         font_size=32, bold=True, italic=True, color=WHITE)

add_text(s, "Meta was fined €1.2B by the Irish DPC in 2023 — the largest GDPR\npenalty ever issued. The violation? Transferring EU user data to US servers\nwithout adequate safeguards.",
         Inches(0.45), Inches(2.85), Inches(5.8), Inches(1.8),
         font_size=15, color=LIGHT_GREY)

add_text(s, "GDPR compliance is not optional. It is existential.",
         Inches(0.45), Inches(4.8), Inches(5.8), Inches(0.7),
         font_size=17, bold=True, color=ACCENT)

add_text(s, "Our platform makes regulatory intelligence instant and auditable.",
         Inches(0.45), Inches(5.55), Inches(5.8), Inches(0.7),
         font_size=14, color=LIGHT_GREY)

add_slide_number(s, 2)


# ════════════════════════════════════════════════════════════════════════════
# SLIDE 3 — WHO WE ARE
# ════════════════════════════════════════════════════════════════════════════
s = prs.slides.add_slide(blank_layout)
fill_background(s)
add_top_bar(s)
section_label(s, "About the Team")

add_text(s, "Who We Are",
         Inches(0.55), Inches(0.55), Inches(9), Inches(0.8),
         font_size=34, bold=True, color=WHITE)

cards = [
    ("Team 6", "Accenture Data & AI Practice", ACCENT),
    ("Domain", "Regulatory Intelligence & Compliance Tech", GREEN),
    ("Context", "Built during the Accenture 2026 AI Bootcamp", ACCENT2),
    ("Mission", "Reduce compliance risk through AI-powered document retrieval", WHITE),
]

card_w = Inches(2.8)
card_h = Inches(3.8)
gap    = Inches(0.35)
start_x = Inches(0.55)
start_y = Inches(1.6)

for i, (title, body, accent_clr) in enumerate(cards):
    cx = start_x + i * (card_w + gap)
    add_rect(s, cx, start_y, card_w, card_h, fill_rgb=MID_GREY)
    add_rect(s, cx, start_y, card_w, Inches(0.08), fill_rgb=accent_clr)
    add_text(s, title, cx + Inches(0.2), start_y + Inches(0.25),
             card_w - Inches(0.4), Inches(0.55),
             font_size=17, bold=True, color=accent_clr)
    add_text(s, body, cx + Inches(0.2), start_y + Inches(0.95),
             card_w - Inches(0.4), Inches(2.5),
             font_size=14, color=LIGHT_GREY)

add_slide_number(s, 3)


# ════════════════════════════════════════════════════════════════════════════
# SLIDE 4 — THE PROBLEM
# ════════════════════════════════════════════════════════════════════════════
s = prs.slides.add_slide(blank_layout)
fill_background(s)
add_top_bar(s)
section_label(s, "Problem Statement")

add_text(s, "The Compliance Challenge",
         Inches(0.55), Inches(0.55), Inches(9), Inches(0.8),
         font_size=34, bold=True, color=WHITE)

problems = [
    ("99 Articles + 173 Recitals", "GDPR alone is 88 pages of dense legal text. Add NIS2, DORA, AI Act..."),
    ("Manual Search Fails", "Legal teams spend hours searching documents for a single clause reference."),
    ("Fines Are Escalating", "Over €4.5B in GDPR fines issued since 2018. Ignorance is no defence."),
    ("No Audit Trail", "When regulators ask how you interpreted an article, you need to show your work."),
]

for i, (title, desc) in enumerate(problems):
    row = i // 2
    col = i % 2
    bx = Inches(0.55) + col * Inches(6.25)
    by = Inches(1.65) + row * Inches(2.35)
    bw = Inches(5.85)
    bh = Inches(2.0)
    add_rect(s, bx, by, bw, bh, fill_rgb=MID_GREY)
    add_rect(s, bx, by, Inches(0.08), bh, fill_rgb=RED)
    add_text(s, title, bx + Inches(0.25), by + Inches(0.2),
             bw - Inches(0.35), Inches(0.5),
             font_size=17, bold=True, color=WHITE)
    add_text(s, desc, bx + Inches(0.25), by + Inches(0.75),
             bw - Inches(0.35), Inches(1.1),
             font_size=13, color=LIGHT_GREY)

add_slide_number(s, 4)


# ════════════════════════════════════════════════════════════════════════════
# SLIDE 5 — OUR SOLUTION
# ════════════════════════════════════════════════════════════════════════════
s = prs.slides.add_slide(blank_layout)
fill_background(s)
add_top_bar(s)
section_label(s, "Solution")

add_text(s, "GDPR Intelligence Platform",
         Inches(0.55), Inches(0.55), Inches(9), Inches(0.8),
         font_size=34, bold=True, color=WHITE)

add_text(s, "Ask any GDPR question in plain English. Get a grounded, source-cited answer in seconds.",
         Inches(0.55), Inches(1.45), Inches(12), Inches(0.6),
         font_size=16, color=LIGHT_GREY)

features = [
    (ACCENT,  "Natural Language Q&A",      "Type any regulatory question — no legal jargon required."),
    (GREEN,   "Source-Cited Answers",       "Every answer links back to the exact article and page."),
    (ACCENT2, "Enterprise-Grade Pipeline",  "Azure AI Search + Databricks Vector Search at scale."),
    (WHITE,   "Full Audit Logging",         "Every query and answer is logged to Delta Lake for compliance review."),
    (ACCENT,  "Multi-Format Ingestion",     "PDF, DOCX, TXT, CSV, HTML — all ingested automatically."),
    (GREEN,   "Smart Article Chunking",     "GDPR articles are segmented by structure, not arbitrary character counts."),
]

col_w = Inches(4.1)
col_gap = Inches(0.25)
row_h = Inches(1.85)
sx = Inches(0.45)
sy = Inches(2.25)

for i, (clr, title, desc) in enumerate(features):
    col = i % 3
    row = i // 3
    fx = sx + col * (col_w + col_gap)
    fy = sy + row * row_h
    add_rect(s, fx, fy, col_w, row_h - Inches(0.1), fill_rgb=MID_GREY)
    add_rect(s, fx, fy, col_w, Inches(0.06), fill_rgb=clr)
    add_text(s, title, fx + Inches(0.2), fy + Inches(0.18),
             col_w - Inches(0.3), Inches(0.5),
             font_size=15, bold=True, color=clr)
    add_text(s, desc, fx + Inches(0.2), fy + Inches(0.72),
             col_w - Inches(0.3), Inches(1.0),
             font_size=12, color=LIGHT_GREY)

add_slide_number(s, 5)


# ════════════════════════════════════════════════════════════════════════════
# SLIDE 6 — PROJECT ARCHITECTURE
# ════════════════════════════════════════════════════════════════════════════
s = prs.slides.add_slide(blank_layout)
fill_background(s)
add_top_bar(s)
section_label(s, "Architecture")

add_text(s, "Project Architecture",
         Inches(0.55), Inches(0.55), Inches(9), Inches(0.8),
         font_size=34, bold=True, color=WHITE)

# Pipeline layers — left to right
layers = [
    ("SOURCES",        "EUR-Lex\nOfficial PDFs\nDatabricks Volume", ACCENT2),
    ("INGESTION",      "Auto-Ingestion\nPipeline\n(EUR-Lex API)", ACCENT),
    ("BRONZE",         "Delta Table\nRaw Chunks\nMetadata preserved", LIGHT_GREY),
    ("SILVER",         "Delta Table\nEnriched +\nEmbedded chunks", LIGHT_GREY),
    ("GOLD",           "Delta Table\nIndex-ready\nrecords", LIGHT_GREY),
    ("VECTOR SEARCH",  "Databricks\nVector Search\nIndex", GREEN),
    ("RAG API",        "FastAPI\n/query\n/query-databricks", ACCENT),
    ("FRONTEND",       "Browser UI\nAudit Logs\nDelta Lake", ACCENT2),
]

box_w  = Inches(1.45)
box_h  = Inches(3.2)
gap    = Inches(0.065)
total  = len(layers) * box_w + (len(layers) - 1) * gap
start_x = (SLIDE_W - total) / 2
start_y = Inches(1.75)

arrow_y = start_y + box_h / 2

for i, (label, body, clr) in enumerate(layers):
    bx = start_x + i * (box_w + gap)
    add_rect(s, bx, start_y, box_w, box_h, fill_rgb=MID_GREY)
    add_rect(s, bx, start_y, box_w, Inches(0.08), fill_rgb=clr)
    add_text(s, label, bx + Inches(0.07), start_y + Inches(0.15),
             box_w - Inches(0.14), Inches(0.45),
             font_size=9, bold=True, color=clr, align=PP_ALIGN.CENTER)
    add_text(s, body, bx + Inches(0.07), start_y + Inches(0.7),
             box_w - Inches(0.14), Inches(2.2),
             font_size=10, color=LIGHT_GREY, align=PP_ALIGN.CENTER)
    if i < len(layers) - 1:
        ax = bx + box_w
        ay = arrow_y - Inches(0.08)
        add_rect(s, ax, ay, gap, Inches(0.16), fill_rgb=ACCENT)

# Azure AI Search side note
add_rect(s, Inches(0.3), Inches(5.5), Inches(5.5), Inches(0.85), fill_rgb=RGBColor(0x1A, 0x2B, 0x3C))
add_text(s, "Local / Azure path:  Azure AI Search Index  →  FastAPI /query  (parallel retrieval backend)",
         Inches(0.5), Inches(5.55), Inches(5.1), Inches(0.7),
         font_size=11, color=ACCENT, italic=True)

add_slide_number(s, 6)


# ════════════════════════════════════════════════════════════════════════════
# SLIDE 7 — TECHNOLOGIES
# ════════════════════════════════════════════════════════════════════════════
s = prs.slides.add_slide(blank_layout)
fill_background(s)
add_top_bar(s)
section_label(s, "Tech Stack")

add_text(s, "Technologies Used",
         Inches(0.55), Inches(0.55), Inches(9), Inches(0.8),
         font_size=34, bold=True, color=WHITE)

tech_groups = [
    ("AI & LLM", ACCENT, [
        "Azure OpenAI — GPT-4 for answer generation",
        "Azure OpenAI Embeddings — text-embedding-3-large",
        "SentenceTransformers — local fallback (all-MiniLM-L6-v2)",
    ]),
    ("Storage & Search", GREEN, [
        "Azure AI Search — primary vector index",
        "Databricks Vector Search — enterprise retrieval",
        "ChromaDB — local development fallback",
    ]),
    ("Data Platform", ACCENT2, [
        "Databricks Unity Catalog — governance layer",
        "Delta Lake — Bronze / Silver / Gold pipeline",
        "Apache Spark — distributed ingestion jobs",
    ]),
    ("Application", WHITE, [
        "FastAPI — REST API (Python)",
        "Docker — containerised deployment",
        "EUR-Lex API — automated regulatory ingestion",
    ]),
]

gw = Inches(3.05)
gh = Inches(4.5)
gx_start = Inches(0.45)
gy = Inches(1.65)
gg = Inches(0.2)

for i, (group, clr, items) in enumerate(tech_groups):
    gx = gx_start + i * (gw + gg)
    add_rect(s, gx, gy, gw, gh, fill_rgb=MID_GREY)
    add_rect(s, gx, gy, gw, Inches(0.08), fill_rgb=clr)
    add_text(s, group, gx + Inches(0.18), gy + Inches(0.18),
             gw - Inches(0.3), Inches(0.5),
             font_size=15, bold=True, color=clr)
    for j, item in enumerate(items):
        add_text(s, f"• {item}",
                 gx + Inches(0.18), gy + Inches(0.85) + j * Inches(0.95),
                 gw - Inches(0.3), Inches(0.85),
                 font_size=12, color=LIGHT_GREY)

add_slide_number(s, 7)


# ════════════════════════════════════════════════════════════════════════════
# SLIDE 8 — HOW IT WORKS  (flow demo)
# ════════════════════════════════════════════════════════════════════════════
s = prs.slides.add_slide(blank_layout)
fill_background(s)
add_top_bar(s)
section_label(s, "How It Works")

add_text(s, "Query Flow — Step by Step",
         Inches(0.55), Inches(0.55), Inches(9), Inches(0.8),
         font_size=34, bold=True, color=WHITE)

steps = [
    ("1", "User asks a\nnatural-language\nGDPR question",  ACCENT),
    ("2", "Question is\nembedded into\na vector",          ACCENT),
    ("3", "Vector Search\nfinds top-5\nrelevant chunks",   GREEN),
    ("4", "Chunks are\nformatted as\nLLM context",         ACCENT2),
    ("5", "Azure OpenAI\ngenerates a\ngrounded answer",    ACCENT),
    ("6", "Answer + sources\nreturned + query\nlogged",    GREEN),
]

bw = Inches(1.95)
bh = Inches(3.5)
bg = Inches(0.15)
total_w = len(steps) * bw + (len(steps) - 1) * bg
sx = (SLIDE_W - total_w) / 2
sy = Inches(1.7)

for i, (num, txt, clr) in enumerate(steps):
    bx = sx + i * (bw + bg)
    add_rect(s, bx, sy, bw, bh, fill_rgb=MID_GREY)
    add_rect(s, bx, sy, bw, Inches(0.06), fill_rgb=clr)
    # number circle
    add_rect(s, bx + bw/2 - Inches(0.35), sy + Inches(0.2),
             Inches(0.7), Inches(0.7), fill_rgb=clr)
    add_text(s, num,
             bx + bw/2 - Inches(0.35), sy + Inches(0.2),
             Inches(0.7), Inches(0.7),
             font_size=20, bold=True, color=DARK_BG, align=PP_ALIGN.CENTER)
    add_text(s, txt,
             bx + Inches(0.1), sy + Inches(1.15),
             bw - Inches(0.2), Inches(2.1),
             font_size=13, color=WHITE, align=PP_ALIGN.CENTER)
    if i < len(steps) - 1:
        add_rect(s, bx + bw, sy + bh/2 - Inches(0.07),
                 bg, Inches(0.14), fill_rgb=ACCENT)

add_slide_number(s, 8)


# ════════════════════════════════════════════════════════════════════════════
# SLIDE 9 — KEY METRICS / BUSINESS VALUE
# ════════════════════════════════════════════════════════════════════════════
s = prs.slides.add_slide(blank_layout)
fill_background(s)
add_top_bar(s)
section_label(s, "Business Value")

add_text(s, "Why This Matters",
         Inches(0.55), Inches(0.55), Inches(9), Inches(0.8),
         font_size=34, bold=True, color=WHITE)

metrics = [
    ("< 3 sec",  "Answer latency\nfor any GDPR question",        ACCENT),
    ("€4.5B+",   "Total GDPR fines issued\nsince 2018",          RED),
    ("99",        "GDPR articles indexed\nand searchable",        GREEN),
    ("100%",      "Answers grounded\nin source documents",        ACCENT2),
]

mw = Inches(2.9)
mh = Inches(2.5)
mg = Inches(0.3)
mx = Inches(0.6)
my = Inches(1.75)

for i, (val, label, clr) in enumerate(metrics):
    bx = mx + i * (mw + mg)
    add_rect(s, bx, my, mw, mh, fill_rgb=MID_GREY)
    add_rect(s, bx, my, mw, Inches(0.06), fill_rgb=clr)
    add_text(s, val, bx, my + Inches(0.3), mw, Inches(1.0),
             font_size=38, bold=True, color=clr, align=PP_ALIGN.CENTER)
    add_text(s, label, bx + Inches(0.15), my + Inches(1.4),
             mw - Inches(0.3), Inches(0.9),
             font_size=13, color=LIGHT_GREY, align=PP_ALIGN.CENTER)

# value props
vx = Inches(0.55)
vy = Inches(4.6)
props = [
    "Hours of manual legal research  →  seconds",
    "Every answer is traceable to a source article and page",
    "Query audit log satisfies internal compliance review requirements",
    "Scales to any EU regulation: NIS2 · DORA · AI Act · ePrivacy",
]
for j, prop in enumerate(props):
    add_text(s, f"✓  {prop}", vx, vy + j * Inches(0.47),
             Inches(12), Inches(0.42),
             font_size=14, color=WHITE)

add_slide_number(s, 9)


# ════════════════════════════════════════════════════════════════════════════
# SLIDE 10 — FEATURE IMPROVEMENTS / ROADMAP
# ════════════════════════════════════════════════════════════════════════════
s = prs.slides.add_slide(blank_layout)
fill_background(s)
add_top_bar(s)
section_label(s, "Roadmap")

add_text(s, "Feature Improvements",
         Inches(0.55), Inches(0.55), Inches(9), Inches(0.8),
         font_size=34, bold=True, color=WHITE)

roadmap = [
    ("Short-term", ACCENT, [
        ("Automated EUR-Lex ingestion",     "Daily sync of new regulations via EUR-Lex API — zero manual uploads."),
        ("Multi-language support",           "Query in Greek, German, French; answers in the user's language."),
        ("Evaluation dashboard",             "Automated retrieval quality scoring (precision@k, MRR) in the UI."),
    ]),
    ("Medium-term", GREEN, [
        ("Multi-regulation support",         "Extend beyond GDPR → NIS2, DORA, AI Act in a single unified index."),
        ("Fine-tracker feed",                "Live feed of GDPR enforcement decisions; link chunks to real cases."),
        ("Role-based access",               "Per-team document permissions via Databricks Unity Catalog groups."),
    ]),
    ("Long-term", ACCENT2, [
        ("Compliance gap analyser",          "Upload a policy document; the system highlights GDPR conflicts."),
        ("Agent-based regulatory assistant", "Multi-step reasoning over cross-regulation questions."),
        ("On-prem / air-gapped deployment",  "Run entirely within enterprise perimeter with local models."),
    ]),
]

col_w = Inches(4.0)
col_h = Inches(5.0)
col_gap = Inches(0.22)
cx_start = Inches(0.45)
cy = Inches(1.6)

for i, (phase, clr, items) in enumerate(roadmap):
    cx = cx_start + i * (col_w + col_gap)
    add_rect(s, cx, cy, col_w, col_h, fill_rgb=MID_GREY)
    add_rect(s, cx, cy, col_w, Inches(0.08), fill_rgb=clr)
    add_text(s, phase, cx + Inches(0.18), cy + Inches(0.18),
             col_w - Inches(0.3), Inches(0.5),
             font_size=15, bold=True, color=clr)
    for j, (title, desc) in enumerate(items):
        iy = cy + Inches(0.9) + j * Inches(1.3)
        add_rect(s, cx + Inches(0.12), iy, col_w - Inches(0.24), Inches(1.15),
                 fill_rgb=RGBColor(0x1E, 0x2E, 0x3E))
        add_text(s, title, cx + Inches(0.25), iy + Inches(0.07),
                 col_w - Inches(0.5), Inches(0.4),
                 font_size=12, bold=True, color=WHITE)
        add_text(s, desc, cx + Inches(0.25), iy + Inches(0.5),
                 col_w - Inches(0.5), Inches(0.6),
                 font_size=11, color=LIGHT_GREY)

add_slide_number(s, 10)


# ════════════════════════════════════════════════════════════════════════════
# SLIDE 11 — LIVE DEMO / API
# ════════════════════════════════════════════════════════════════════════════
s = prs.slides.add_slide(blank_layout)
fill_background(s)
add_top_bar(s)
section_label(s, "Demo")

add_text(s, "See It In Action",
         Inches(0.55), Inches(0.55), Inches(9), Inches(0.8),
         font_size=34, bold=True, color=WHITE)

# Mock terminal / request-response
add_rect(s, Inches(0.45), Inches(1.6), Inches(12.4), Inches(4.7),
         fill_rgb=RGBColor(0x0A, 0x0A, 0x12))
add_rect(s, Inches(0.45), Inches(1.6), Inches(12.4), Inches(0.35),
         fill_rgb=RGBColor(0x22, 0x22, 0x33))
add_text(s, "  POST  /query",
         Inches(0.55), Inches(1.62), Inches(5), Inches(0.32),
         font_size=11, color=LIGHT_GREY, bold=True)

code_lines = [
    ('// Request', LIGHT_GREY, False),
    ('{ "question": "What are the rights of data subjects under GDPR?" }', ACCENT, False),
    ('', WHITE, False),
    ('// Response  200 OK', LIGHT_GREY, False),
    ('{', WHITE, False),
    ('  "answer": "Under GDPR, data subjects have: the right to access (Art.15),', WHITE, False),
    ('             the right to erasure (Art.17), the right to portability (Art.20)...',WHITE, False),
    ('             Sources: 32016R0679_EN (pages 42, 44, 47)",', WHITE, False),
    ('  "retrieved_chunks": [ { "chunk_id": "a3f9...", "distance": 0.187, ... } ]', GREEN, False),
    ('}', WHITE, False),
]

add_multiline(s, [(txt, clr, bld) for txt, clr, bld in code_lines],
              Inches(0.65), Inches(2.05), Inches(12.0), Inches(4.1),
              font_size=11, align=PP_ALIGN.LEFT)

add_text(s, "Interactive docs:  http://127.0.0.1:8080/docs  |  Frontend UI:  GET /",
         Inches(0.45), Inches(6.45), Inches(10), Inches(0.5),
         font_size=12, color=LIGHT_GREY, italic=True)

add_slide_number(s, 11)


# ════════════════════════════════════════════════════════════════════════════
# SLIDE 12 — CLOSING / Q&A
# ════════════════════════════════════════════════════════════════════════════
s = prs.slides.add_slide(blank_layout)
fill_background(s)

# full-width top accent
add_rect(s, 0, 0, SLIDE_W, Inches(0.12), fill_rgb=ACCENT)
add_rect(s, 0, SLIDE_H - Inches(0.12), SLIDE_W, Inches(0.12), fill_rgb=ACCENT)

add_text(s, "Thank You",
         0, Inches(1.8), SLIDE_W, Inches(1.4),
         font_size=60, bold=True, color=WHITE, align=PP_ALIGN.CENTER)

add_text(s, "GDPR Intelligence Platform  ·  Team 6  ·  Accenture 2026",
         0, Inches(3.35), SLIDE_W, Inches(0.7),
         font_size=18, color=ACCENT, align=PP_ALIGN.CENTER)

add_text(s, "Questions?",
         0, Inches(4.3), SLIDE_W, Inches(0.8),
         font_size=28, bold=True, color=LIGHT_GREY, align=PP_ALIGN.CENTER)

add_text(s, "GitHub  ·  FastAPI /docs  ·  Databricks Unity Catalog",
         0, Inches(5.5), SLIDE_W, Inches(0.5),
         font_size=14, color=MID_GREY, align=PP_ALIGN.CENTER)

add_slide_number(s, 12)


# ── Save ────────────────────────────────────────────────────────────────────
out = os.path.join(HERE, "GDPR_Intelligence_Platform.pptx")
prs.save(out)
print(f"Saved → {out}")
