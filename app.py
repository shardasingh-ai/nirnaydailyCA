import re
import sys
import tempfile
import subprocess
from pathlib import Path

import streamlit as st
import markdown as mdlib
from bs4 import BeautifulSoup


# ============================================================
# Streamlit config
# ============================================================
st.set_page_config(page_title="Nirnay MD → HTML/PDF", layout="centered")


# ============================================================
# 1) STANDARD CSS (updated to support new 10 headers + image safety + sharp print)
# ============================================================
STANDARD_CSS = r"""
@page { size: A4; margin: 10mm 9mm; }   /* per-page margins (page 2+ safe) */
body { margin: 0; }
html, body { height: 100%; }

.page { padding: 0; }                  /* default */
@media screen { .page { padding: 10mm 9mm; } }  /* screen-only padding */

body{
  font-family: ui-sans-serif, system-ui, -apple-system, "Segoe UI", Roboto, Arial, sans-serif;
  color: #0f2433;
  text-rendering: geometricPrecision;
  -webkit-font-smoothing: antialiased;
}

.book{ width: 100%; }

.prose{
  column-count: 2;
  column-gap: 18mm;
  column-fill: auto;
  column-rule: 1px solid rgba(15,36,51,.10);
  font-size: 12.2px;
  line-height: 1.55;
}

.prose *{ box-sizing: border-box; }
.prose p{ margin: 0 0 8px 0; }
.prose strong{ font-weight: 800; }

/* ---------- Image safety (NO overlap, avoid blur) ---------- */
.prose img{
  max-width: 100% !important;
  height: auto !important;
  display: block;
  margin: 8px 0 10px 0;
  border-radius: 10px;
  width: auto; /* do NOT upscale small images */
}

.prose img, .prose figure{
  break-inside: avoid;
  page-break-inside: avoid;
}

/* Print stability: avoid forced blank pages */
@media print{
  html, body { height: auto !important; }
  .page, .book, .prose { height: auto !important; min-height: auto !important; }
  .prose > *:last-child { margin-bottom: 0 !important; break-after: auto !important; page-break-after: auto !important; }
  h1 { break-after: avoid-page; page-break-after: avoid; }
}

/* ---------- H1 ribbon ---------- */
.prose h1{
  column-span: all;
  -webkit-column-span: all;
  margin: 0 0 18px 0;
  padding: 26px 20px;
  min-height: 104px;
  display:flex;
  align-items:center;
  justify-content:center;
  text-align:center;

  background: linear-gradient(180deg, rgba(74,107,135,.22) 0%, rgba(74,107,135,.10) 100%);
  border: 1px solid rgba(15,36,51,.12);
  border-left: 12px solid rgba(74,107,135,.86);
  border-radius: 16px;

  font-weight: 950;
  letter-spacing: .12em;
  text-transform: uppercase;
  font-size: 34px;
  line-height: 1.12;

  box-shadow: 0 12px 26px rgba(15,36,51,.12);
}

/* ---------- Default headings ---------- */
.prose h2{
  column-span: none !important;
  -webkit-column-span: none !important;
  display:block;
  margin: 14px 0 10px 0;
  padding: 10px 12px;

  background: rgba(74,107,135,.10);
  border: 1px solid rgba(15,36,51,.10);
  border-left: 8px solid rgba(74,107,135,.70);
  border-radius: 12px;

  font-weight: 900;
  letter-spacing: .01em;
}
.prose h3{ margin: 12px 0 8px 0; font-weight: 900; }
.prose h4{ margin: 10px 0 6px 0; font-weight: 900; }
.prose h5{ margin: 9px 0 6px 0; font-weight: 900; }
.prose h6{ margin: 9px 0 6px 0; font-weight: 900; }

/* ---------- Topic titles: strong differentiator ---------- */
.prose h2.topic-title{
  padding: 16px 14px 14px 16px !important;
  margin: 14px 0 12px 0 !important;
  border-radius: 18px !important;
  border: 1px solid rgba(15,36,51,.12) !important;

  background: linear-gradient(135deg, rgba(26,152,202,.16) 0%, rgba(47,125,74,.10) 55%, rgba(92,56,181,.10) 100%) !important;
  box-shadow: 0 14px 28px rgba(15,36,51,.10) !important;

  border-left: 0 !important;
  font-weight: 950 !important;
  font-size: 18.2px !important;
  line-height: 1.22 !important;
  position: relative;
}
.prose h2.topic-title::before{
  content: "TOPIC";
  display:inline-block;
  font-size: 10px;
  letter-spacing: .20em;
  font-weight: 900;
  color: rgba(15,36,51,.60);
  background: rgba(255,255,255,.55);
  border: 1px solid rgba(15,36,51,.10);
  padding: 4px 8px;
  border-radius: 999px;
  margin-right: 10px;
  vertical-align: middle;
}
.prose h2.topic-title::after{
  content:"";
  position:absolute;
  left:16px;
  right:16px;
  bottom:10px;
  height:2px;
  background: rgba(15,36,51,.18);
  border-radius: 999px;
}

/* ---------- Lists ---------- */
.prose ul{ margin: 6px 0 8px 0; padding-left: 16px; }
.prose li{ margin: 4px 0; }
.prose li::marker{ color: rgba(15,36,51,.55); }

.prose hr{
  border: none;
  height: 1px;
  background: rgba(15,36,51,.18);
  margin: 18px 0;
}

/* ---------- Premium palette ---------- */
:root{
  --blue-bg:  rgba(43,106,164,.10);
  --blue-bar: rgba(43,106,164,.80);

  --teal-bg: rgba(0,128,128,.10);
  --teal-top: rgba(0,128,128,.35);

  --green-bg: rgba(47,125,74,.10);
  --green-top: rgba(47,125,74,.35);

  --amber-bg: rgba(176,106,0,.11);
  --amber-top: rgba(176,106,0,.35);

  --violet-bg: rgba(92,56,181,.10);
  --violet-top: rgba(92,56,181,.35);

  --rose-bg: rgba(166,53,92,.10);
  --rose-top: rgba(166,53,92,.35);

  --slate-bg: rgba(70,80,95,.10);
  --slate-top: rgba(70,80,95,.35);

  --sky-bg: rgba(40,120,160,.10);
  --sky-top: rgba(40,120,160,.35);
}

/* ---------- Section Boxes ---------- */
.colorbox{
  padding: 10px 12px;
  border-radius: 16px;
  margin: 8px 0 10px 0;
  border: 1px solid rgba(15,36,51,.10);
  box-shadow: 0 10px 24px rgba(15,36,51,.08);
  -webkit-box-decoration-break: clone;
  box-decoration-break: clone;

  print-color-adjust: exact;
  -webkit-print-color-adjust: exact;

  background-image: radial-gradient(rgba(255,255,255,.35) 1px, transparent 1px);
  background-size: 18px 18px;
}
.colorbox + .colorbox{ margin-top: 12px !important; }

/* Syllabus & Context: keep left accent */
.colorbox.syllabus, .colorbox.context{
  background-color: var(--blue-bg) !important;
  border-left: 10px solid var(--blue-bar) !important;
}

/* Others: shaded only (no dark margin) */
.colorbox.analysis{
  background-color: var(--teal-bg) !important;
  border-left: 0 !important;
  border-top: 6px solid var(--teal-top) !important;
}
.colorbox.beyond{
  background-color: var(--green-bg) !important;
  border-left: 0 !important;
  border-top: 6px solid var(--green-top) !important;
}
.colorbox.wayforward{
  background-color: var(--green-bg) !important;
  border-left: 0 !important;
  border-top: 6px solid var(--green-top) !important;
}
.colorbox.prelims{
  background-color: var(--amber-bg) !important;
  border-left: 0 !important;
  border-top: 6px solid var(--amber-top) !important;
}
.colorbox.exercise{
  background-color: var(--rose-bg) !important;
  border-left: 0 !important;
  border-top: 6px solid var(--rose-top) !important;
}
.colorbox.mains{
  background-color: var(--violet-bg) !important;
  border-left: 0 !important;
  border-top: 6px solid var(--violet-top) !important;
}
.colorbox.recall{
  background-color: var(--slate-bg) !important;
  border-left: 0 !important;
  border-top: 6px solid var(--slate-top) !important;
}
.colorbox.recap{
  background-color: var(--sky-bg) !important;
  border-left: 0 !important;
  border-top: 6px solid var(--sky-top) !important;
}

/* Heading chips inside boxes */
.colorbox > h2, .colorbox > h3, .colorbox > h4, .colorbox > h5, .colorbox > h6{
  display:block;
  padding: 10px 12px;
  border-radius: 12px;
  margin: 0 0 8px 0;
  border: 1px solid rgba(15,36,51,.10);
  background: rgba(255,255,255,.60);
  box-shadow: inset 0 0 0 1px rgba(255,255,255,.40);
  font-weight: 950;
}

/* Subtle tint per section */
.colorbox.syllabus > h2, .colorbox.syllabus > h3, .colorbox.syllabus > h4,
.colorbox.context  > h2, .colorbox.context  > h3, .colorbox.context  > h4{
  background: rgba(43,106,164,.14) !important;
}
.colorbox.analysis > h2, .colorbox.analysis > h3, .colorbox.analysis > h4{
  background: rgba(0,128,128,.14) !important;
}
.colorbox.beyond > h2, .colorbox.beyond > h3, .colorbox.beyond > h4,
.colorbox.wayforward > h2, .colorbox.wayforward > h3, .colorbox.wayforward > h4{
  background: rgba(47,125,74,.14) !important;
}
.colorbox.prelims > h2, .colorbox.prelims > h3, .colorbox.prelims > h4, .colorbox.prelims > h5{
  background: rgba(176,106,0,.15) !important;
}
.colorbox.exercise > h2, .colorbox.exercise > h3, .colorbox.exercise > h4{
  background: rgba(166,53,92,.14) !important;
}
.colorbox.mains > h2, .colorbox.mains > h3, .colorbox.mains > h4, .colorbox.mains > h5, .colorbox.mains > h6{
  background: rgba(92,56,181,.14) !important;
}
.colorbox.recall > h2, .colorbox.recall > h3, .colorbox.recall > h4{
  background: rgba(70,80,95,.14) !important;
}
.colorbox.recap > h2, .colorbox.recap > h3, .colorbox.recap > h4{
  background: rgba(40,120,160,.14) !important;
}

/* ---------- Splittable table ---------- */
.gridtable{
  display:block;
  width: 100%;
  border: 1px solid rgba(15,36,51,.12);
  border-radius: 12px;
  background: rgba(255,255,255,.85);
  overflow: visible;
  -webkit-box-decoration-break: clone;
  box-decoration-break: clone;
}
.gridtable .gt-row{ display:block; }
.gridtable .gt-cell{
  display:inline-block;
  width: 34%;
  vertical-align: top;
  padding: 8px 10px;
  border-top: 1px solid rgba(15,36,51,.08);
  border-right: 1px solid rgba(15,36,51,.08);
  box-sizing: border-box;
  font-size: 0.95em;
}
.gridtable .gt-row .gt-cell:last-child{ width: 66%; border-right: none; }
.gridtable .gt-head .gt-cell{
  font-weight: 900;
  background: rgba(15,36,51,.04);
  border-top: none;
  letter-spacing: .02em;
}
"""


# ============================================================
# 2) Playwright setup (Streamlit Cloud)
# ============================================================
@st.cache_resource
def ensure_playwright_chromium():
    subprocess.run([sys.executable, "-m", "playwright", "install", "chromium"], check=True)


# ============================================================
# 3) Markdown → HTML (adaptive to new 10 headers)
# ============================================================
def cleanup_markdown(md: str) -> str:
    md = re.sub(r"(?m)^\s*#{1,6}\s*$\n?", "", md)  # remove empty headings
    md = re.sub(r"\\([\\`*_{}\[\]()#+\-.!|>~])", r"\1", md)  # unescape punctuation

    # ensure blank line after table row if next line is a heading
    lines = md.splitlines()
    out = []
    for i, line in enumerate(lines):
        out.append(line)
        if re.match(r"^\s*\|.*\|\s*$", line):
            if i + 1 < len(lines):
                nxt = lines[i + 1]
                if nxt.strip() and re.match(r"^\s*#{1,6}\s+\S", nxt):
                    out.append("")
    return "\n".join(out)

def heading_text(h) -> str:
    return re.sub(r"\s+", " ", h.get_text(" ", strip=True)).strip()

def is_heading(node) -> bool:
    return getattr(node, "name", None) in ("h1", "h2", "h3", "h4", "h5", "h6")

def normalize_heading(s: str) -> str:
    s = re.sub(r"\s+", " ", (s or "").strip())
    s = re.sub(r"^\(?\s*(\d{1,2}|[ivxlcdm]{1,6})\s*[\.\)\:\-]\s*", "", s, flags=re.I)
    return s.strip().lower()

def classify_section(title: str) -> str | None:
    t = normalize_heading(title)

    # Your new standard headers (robust keyword matching)
    if "syllabus mapping" in t:
        return "syllabus"
    if "the context" in t or "why in news" in t:
        return "context"
    if "key analysis" in t:
        return "analysis"
    if "beyond the news" in t or "faculty value addition" in t or "value addition" in t:
        return "beyond"
    if "way forward" in t:
        return "wayforward"
    if "prelims pointers" in t or "prelims pointer" in t:
        return "prelims"
    if "exercise" in t:
        return "exercise"
    if "mains practice question" in t:
        return "mains"
    if "recall" in t:
        return "recall"
    if "recap" in t:
        return "recap"
    return None

def is_topic_title_tag(h) -> bool:
    # Treat H2 as topic title if it is NOT one of the known section headings
    return h.name == "h2" and heading_text(h) != "" and classify_section(heading_text(h)) is None

def tables_to_gridtables(soup: BeautifulSoup) -> None:
    def append_fragment(tag, fragment_html: str):
        frag = BeautifulSoup(fragment_html or "", "html.parser")
        for child in list(frag.contents):
            tag.append(child)

    for tbl in soup.find_all("table"):
        headers = []
        thead = tbl.find("thead")
        if thead:
            headers = [th.get_text(" ", strip=True) for th in thead.find_all("th")]

        rows = []
        tbody = tbl.find("tbody")
        if tbody:
            for tr in tbody.find_all("tr"):
                cells = tr.find_all(["td", "th"])
                rows.append([c.decode_contents().strip() for c in cells])

        gt = soup.new_tag("div", **{"class": "gridtable"})
        head = soup.new_tag("div", **{"class": "gt-row gt-head"})

        use_headers = headers[:2] if headers else ["Category", "Fact / Detail"]
        for hh in use_headers:
            cell = soup.new_tag("div", **{"class": "gt-cell"})
            cell.string = hh
            head.append(cell)
        gt.append(head)

        for r in rows:
            if not r:
                continue
            while len(r) < 2:
                r.append("")
            row = soup.new_tag("div", **{"class": "gt-row"})
            c1 = soup.new_tag("div", **{"class": "gt-cell"})
            append_fragment(c1, r[0])
            c2 = soup.new_tag("div", **{"class": "gt-cell"})
            append_fragment(c2, r[1])
            row.append(c1)
            row.append(c2)
            gt.append(row)

        tbl.replace_with(gt)

def wrap_sections_and_tag_topics(soup: BeautifulSoup) -> None:
    # Tag topic titles
    for h2 in soup.find_all("h2"):
        if is_topic_title_tag(h2):
            h2["class"] = (h2.get("class", []) + ["topic-title"])

    headings = soup.find_all(["h1", "h2", "h3", "h4", "h5", "h6"])

    def already_in_box(h):
        return h.find_parent(class_="colorbox") is not None

    def is_topic_heading(h):
        return is_heading(h) and h.name == "h2" and classify_section(heading_text(h)) is None and heading_text(h) != ""

    def is_section_heading(h):
        return is_heading(h) and classify_section(heading_text(h)) is not None

    def wrap_from(start_h, class_name: str):
        if already_in_box(start_h):
            return

        box = soup.new_tag("div", **{"class": f"colorbox {class_name}"})
        start_h.insert_before(box)

        cur = start_h
        while cur is not None:
            nxt = cur.next_sibling

            if cur is not start_h:
                if getattr(cur, "name", None) == "hr":
                    break
                if is_heading(cur) and (is_topic_heading(cur) or is_section_heading(cur)):
                    break

            box.append(cur.extract())
            cur = nxt

    for h in headings:
        if not is_heading(h) or already_in_box(h):
            continue
        cls = classify_section(heading_text(h))
        if cls:
            wrap_from(h, cls)

def md_to_full_html(md_text: str, title_fallback: str) -> str:
    md_text = cleanup_markdown(md_text)
    body = mdlib.markdown(md_text, extensions=["tables"])
    body = re.sub(r"<p>\s*######\s*</p>\s*", "", body, flags=re.I)

    soup = BeautifulSoup(body, "html.parser")
    tables_to_gridtables(soup)
    wrap_sections_and_tag_topics(soup)

    h1 = soup.find("h1")
    doc_title = h1.get_text(" ", strip=True).upper() if h1 else title_fallback.upper()

    return f"""<!doctype html>
<html>
<head>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width,initial-scale=1"/>
  <title>{doc_title}</title>
  <style>{STANDARD_CSS}</style>
</head>
<body>
  <div class="page">
    <article class="book">
      <div class="prose">
        {str(soup)}
      </div>
    </article>
  </div>
</body>
</html>
"""


# ============================================================
# 4) HTML → PDF bytes (Playwright) — sharper output
# ============================================================
def html_to_pdf_bytes(full_html: str) -> bytes:
    from playwright.sync_api import sync_playwright

    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        html_path = td / "doc.html"
        html_path.write_text(full_html, encoding="utf-8")

        with sync_playwright() as p:
            browser = p.chromium.launch()
            context = browser.new_context(device_scale_factor=2)  # sharper images/text
            page = context.new_page()
            page.goto(html_path.as_uri(), wait_until="networkidle")
            page.emulate_media(media="print")

            pdf_bytes = page.pdf(
                format="A4",
                print_background=True,
                margin={"top": "10mm", "bottom": "10mm", "left": "9mm", "right": "9mm"},
                prefer_css_page_size=True,
            )
            browser.close()

        return pdf_bytes


# ============================================================
# 5) UI
# ============================================================
st.title("Nirnay Daily CA — Markdown to HTML + PDF")
st.caption("Upload a .md file → get consistent Nirnay 2-column HTML and PDF downloads.")

uploaded = st.file_uploader("Upload Markdown file", type=["md", "markdown"])

if uploaded:
    md_text = uploaded.read().decode("utf-8", errors="ignore")
    base_name = Path(uploaded.name).stem

    full_html = md_to_full_html(md_text, title_fallback=base_name)

    st.success("Rendered HTML successfully.")

    with st.expander("Preview (HTML)", expanded=False):
        st.components.v1.html(full_html, height=650, scrolling=True)

    st.download_button(
        "Download HTML",
        data=full_html.encode("utf-8"),
        file_name=f"{base_name}_nirnay.html",
        mime="text/html",
    )

    if st.button("Generate PDF"):
        try:
            with st.spinner("Preparing PDF engine (Chromium) ..."):
                ensure_playwright_chromium()

            with st.spinner("Rendering PDF ..."):
                pdf_bytes = html_to_pdf_bytes(full_html)

            st.download_button(
                "Download PDF",
                data=pdf_bytes,
                file_name=f"{base_name}_nirnay.pdf",
                mime="application/pdf",
            )
            st.success("PDF ready.")
        except subprocess.CalledProcessError as e:
            st.error(
                "Playwright could not install Chromium in this environment.\n\n"
                "Make sure your Streamlit Cloud repo includes:\n"
                "1) requirements.txt with 'playwright'\n"
                "2) packages.txt with required system libraries\n\n"
                f"Install error:\n{e}"
            )
        except Exception as e:
            st.error(
                "PDF generation failed.\n\n"
                "If running locally:\n"
                "python -m playwright install chromium\n\n"
                f"Error: {e}"
            )
