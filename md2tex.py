#!/usr/bin/env python3
"""Convert src.md to main.tex using config.yaml settings.

src.md is the source of truth. Edit config.yaml to change document styling.
Do not edit main.tex directly — it is regenerated on every build.
"""

import re
import sys
from pathlib import Path

import yaml

CONFIG_PATH = Path("config.yaml")
SRC_PATH = Path("src.md")
OUT_PATH = Path("main.tex")


def load_config():
    with open(CONFIG_PATH) as f:
        return yaml.safe_load(f)


def escape_tex(text):
    """Escape LaTeX special chars, handling markdown escape sequences first."""
    # Preserve markdown escape sequences via placeholders
    text = text.replace("\\-", "\x00EM\x00")
    text = text.replace("\\!", "!")
    # Strip markdown heading anchors like {#poem-id}
    text = re.sub(r"\s*\{#[^}]+\}", "", text)
    # Escape backslash before other substitutions
    text = text.replace("\\", r"\textbackslash{}")
    # Standard LaTeX special characters
    text = text.replace("&", r"\&")
    text = text.replace("%", r"\%")
    text = text.replace("$", r"\$")
    text = text.replace("#", r"\#")
    text = text.replace("_", r"\_")
    text = text.replace("^", r"\^{}")
    text = text.replace("~", r"\textasciitilde{}")
    # Restore placeholders
    text = text.replace("\x00EM\x00", "--")
    return text


def smart_quotes(text):
    """Convert straight double quotes to LaTeX directional quotes.

    Opening quote: preceded by whitespace, open bracket, em-dash, or start of text.
    Closing quote: everything else (letters, !, ?, ., etc.).
    Using prev_char avoids the ?`` and !`` ligatures that produce ¿ and ¡.
    """
    result = []
    prev_char = " "  # treat start of text as after a space
    for c in text:
        if c == '"':
            result.append("``" if prev_char in " \t\n([—" else "''")
        else:
            result.append(c)
        prev_char = c
    return "".join(result)


def process_text(text):
    return smart_quotes(escape_tex(text))


# ---------------------------------------------------------------------------
# Parsing
# ---------------------------------------------------------------------------


def parse_document(content):
    """Parse src.md into a structured dict."""
    lines = content.split("\n")
    doc = {"title": "", "front_matter": [], "parts": []}

    current_fm = None
    current_part = None
    current_poem = None
    current_stanza = []
    in_body = False
    skip_section = False

    def close_poem():
        nonlocal current_stanza
        if current_poem is not None:
            if current_stanza:
                current_poem["stanzas"].append(current_stanza)
                current_stanza = []
            current_part["poems"].append(current_poem)

    for line in lines:
        stripped = line.strip()

        # --- Title (first heading) ---
        if not doc["title"]:
            if stripped.startswith("# ") and not stripped.startswith("## "):
                doc["title"] = stripped[2:].strip()
            continue

        # --- Part headers: ## but not ### ---
        if stripped.startswith("##") and not stripped.startswith("###"):
            part_title = stripped[2:].strip()
            if not part_title:
                continue  # blank ## divider between parts
            close_poem()
            current_poem = None
            current_stanza = []
            current_part = {"title": part_title, "poems": []}
            doc["parts"].append(current_part)
            in_body = True
            skip_section = False
            continue

        # --- Front matter section headers ---
        if not in_body and stripped.startswith("### "):
            section_title = stripped[4:].strip()
            if section_title == "Table of Contents":
                skip_section = True
                current_fm = None
            else:
                skip_section = False
                current_fm = {"title": section_title, "lines": []}
                doc["front_matter"].append(current_fm)
            continue

        if not in_body and skip_section:
            continue

        if not in_body:
            if current_fm is not None:
                current_fm["lines"].append(line)
            continue

        # --- Poem headers: ### in body ---
        if stripped.startswith("### "):
            poem_title = re.sub(r"\s*\{#[^}]+\}", "", stripped[4:]).strip()
            close_poem()
            current_poem = {"title": poem_title, "stanzas": []}
            current_stanza = []
            continue

        if current_poem is None:
            continue

        # --- Poem lines ---
        # Trailing spaces are markdown line-break syntax; strip them.
        poem_line = line.rstrip()
        stripped_poem = poem_line.strip()
        if stripped_poem == "<!-- page break -->":
            if current_stanza:
                current_poem["stanzas"].append(current_stanza)
                current_stanza = []
            current_poem["stanzas"].append([stripped_poem])
        elif poem_line:
            current_stanza.append(poem_line)
        elif current_stanza:
            current_poem["stanzas"].append(current_stanza)
            current_stanza = []

    close_poem()
    return doc


# ---------------------------------------------------------------------------
# Rendering helpers
# ---------------------------------------------------------------------------


def render_fm_lines(lines):
    """Convert front matter content lines to LaTeX."""
    output = []
    in_list = False

    for line in lines:
        stripped = line.strip()
        is_list_item = bool(re.match(r"^[-*]\s+", stripped))

        if stripped == "<!-- page break -->":
            if in_list:
                output.append("\\end{itemize}")
                in_list = False
            output.append("\\clearpage")
            continue

        if is_list_item:
            if not in_list:
                output.append("\\begin{itemize}")
                output.append(
                    "  \\setlength{\\itemsep}{0pt}\\setlength{\\parskip}{0pt}"
                )
                in_list = True
            item = re.sub(r"^[-*]\s+", "", stripped).rstrip()
            output.append(f"  \\item {process_text(item)}")
        else:
            if in_list:
                if not stripped:
                    output.append("\\end{itemize}")
                    in_list = False
                    output.append("")
                else:
                    # continuation text after list — unlikely here but safe
                    output.append(f"  \\item {process_text(stripped)}")
            else:
                output.append(process_text(line.rstrip()) if stripped else "")

    if in_list:
        output.append("\\end{itemize}")
    return output


# ---------------------------------------------------------------------------
# LaTeX generation
# ---------------------------------------------------------------------------


def make_preamble(config, doc):
    c_doc = config.get("document", {})
    c_geo = config.get("geometry", {})
    c_style = config.get("style", {})
    c_layout = config.get("layout", {})

    font_size = c_doc.get("font_size", 12)
    paper = c_doc.get("paper", "letterpaper")
    font = c_style.get("font", "default")
    spread = c_style.get("spread", 1.1)
    poem_title_align = c_style.get("poem_title_align", "left")
    stanza_skip = c_style.get("stanza_skip", None)

    twoside = c_layout.get("twoside", False)
    trim_w = c_layout.get("trim_width")
    trim_h = c_layout.get("trim_height")

    side_opt = "twoside" if twoside else "oneside"

    top = c_geo.get("top", "1.25in")
    bottom = c_geo.get("bottom", "1.25in")
    inner = c_geo.get("inner", "1.25in")
    outer = c_geo.get("outer", "1in")

    # Paper: explicit trim dimensions override the paper key
    if trim_w and trim_h:
        geo_paper = f"paperwidth={trim_w}, paperheight={trim_h}"
    else:
        geo_paper = paper

    title = process_text(c_doc.get("title", doc["title"]))
    author = process_text(c_doc.get("author", ""))

    font_pkg = {
        "palatino": "\\usepackage{newpxtext}",
        "garamond": "\\usepackage[lf]{ebgaramond}",
        "times": "\\usepackage{newtxtext}",
        "courier": "\\usepackage{courier}",
    }.get(font, "")

    align_decl = (
        "\\centering" if poem_title_align == "center" else "\\raggedright"
    )

    stanza_skip_line = (
        f"\\setlength{{\\stanzaskip}}{{{stanza_skip}}}" if stanza_skip else ""
    )

    return f"""\
% Generated by md2tex.py — edit src.md or config.yaml, not this file
\\documentclass[{font_size}pt,{side_opt},openany]{{book}}
\\usepackage[utf8]{{inputenc}}
\\usepackage[T1]{{fontenc}}
{font_pkg}
\\usepackage[{geo_paper}, top={top}, bottom={bottom}, inner={inner}, outer={outer}]{{geometry}}
\\usepackage{{potterybook}}

\\setstretch{{{spread}}}
{stanza_skip_line}
\\renewcommand{{\\poemtitlefont}}{{\\normalfont\\large\\bfseries {align_decl}}}

\\title{{\\Huge\\bfseries {title}}}
\\author{{{author}}}
\\date{{}}

"""


def _longest_in(stanzas):
    """Return the escaped text of the longest line across a list of stanzas."""
    lines = [l for s in stanzas for l in s]
    return process_text(max(lines, key=len)) if lines else ""


def _render_poem_section(stanzas, out):
    """Emit one page-section of a poem sized to its own longest line."""
    out.append(f"\\settowidth{{\\versewidth}}{{{_longest_in(stanzas)}}}")
    out.append("\\begin{verse}[\\versewidth]")
    for i, stanza in enumerate(stanzas):
        if i > 0:
            out.append("")  # blank line = stanza break in verse env
        for j, verse_line in enumerate(stanza):
            tex = process_text(verse_line)
            if j < len(stanza) - 1:
                tex += " \\\\*"  # keep stanza together across lines
            out.append(tex)
    out.append("\\end{verse}")


def _render_poem(poem, out):
    """Emit a complete poem: title then one verse section per page."""
    out.append(f"\\poemtitle{{{process_text(poem['title'])}}}")

    # Partition stanzas into page-sections at each <!-- page break --> marker.
    sections: list[list] = []
    current: list = []
    for stanza in poem["stanzas"]:
        if stanza == ["<!-- page break -->"]:
            sections.append(current)
            current = []
        else:
            current.append(stanza)
    sections.append(current)

    for i, section in enumerate(sections):
        if i > 0:
            out.append("\\clearpage")
        if section:
            _render_poem_section(section, out)

    out.append("\\clearpage")
    out.append("")


def make_body(doc, config):
    include_toc = config.get("style", {}).get("include_toc", True)
    out = ["\\begin{document}", "\\frontmatter", "\\maketitle", "\\newpage", ""]

    for i, section in enumerate(doc["front_matter"]):
        if i > 0:
            out.append("\\bigskip")
        out.append(f"\\fmsection{{{process_text(section['title'])}}}")
        out.append("")
        out.extend(render_fm_lines(section["lines"]))
        out.append("")

    if include_toc:
        out += [
            "\\newpage",
            "\\begin{adjustwidth}{0.167\\textwidth}{0.167\\textwidth}",
            "\\tableofcontents",
            "\\end{adjustwidth}",
            "\\newpage",
            "",
        ]

    out += ["\\mainmatter", ""]

    for part in doc["parts"]:
        out.append(f"\\part*{{{process_text(part['title'])}}}")
        out.append("")
        for poem in part["poems"]:
            _render_poem(poem, out)

    out.append("\\end{document}")
    return "\n".join(out)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main():
    config = load_config()
    src = SRC_PATH.read_text()
    doc = parse_document(src)

    if not doc["title"]:
        print("Warning: no title found in src.md", file=sys.stderr)
    if not doc["parts"]:
        print("Warning: no parts found in src.md", file=sys.stderr)

    tex = make_preamble(config, doc) + make_body(doc, config) + "\n"
    OUT_PATH.write_text(tex)
    print(
        f"Written {OUT_PATH}  ({len(doc['parts'])} parts, "
        f"{sum(len(p['poems']) for p in doc['parts'])} poems)"
    )


if __name__ == "__main__":
    main()
