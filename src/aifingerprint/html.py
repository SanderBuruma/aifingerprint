"""Markdown-to-HTML converter with dark theme styling. Pure stdlib."""

import re

CSS = """
:root {
    --bg: #0d1117;
    --bg-card: #161b22;
    --bg-elevated: #1c2333;
    --border: #30363d;
    --text: #e6edf3;
    --text-dim: #8b949e;
    --text-bright: #ffffff;
    --accent-blue: #58a6ff;
    --accent-purple: #bc8cff;
    --accent-cyan: #79c0ff;
    --accent-green: #3fb950;
    --accent-yellow: #d29922;
    --accent-orange: #f0883e;
    --accent-red: #f85149;
    --accent-pink: #f778ba;
    --gradient-score: linear-gradient(135deg, #58a6ff, #bc8cff);
}
* { box-sizing: border-box; }
body {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    max-width: 920px;
    margin: 0 auto;
    padding: 2rem 1.5rem;
    background: var(--bg);
    color: var(--text);
    line-height: 1.7;
}
h1 {
    font-size: 1.8rem;
    background: var(--gradient-score);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    border-bottom: 2px solid var(--border);
    padding-bottom: 0.75rem;
    margin-top: 0;
    margin-bottom: 1.5rem;
}
h2 {
    color: var(--accent-cyan);
    font-size: 1.3rem;
    border-bottom: 1px solid var(--border);
    padding-bottom: 0.4rem;
    margin-top: 2.5rem;
    margin-bottom: 1rem;
    letter-spacing: 0.02em;
}
h3 {
    color: var(--accent-purple);
    font-size: 1.1rem;
    margin-top: 1.8rem;
    margin-bottom: 0.5rem;
}
table {
    border-collapse: collapse;
    width: 100%;
    margin: 1rem 0;
    border-radius: 8px;
    overflow: hidden;
    border: 1px solid var(--border);
}
th, td {
    padding: 0.6rem 1rem;
    text-align: left;
    border-bottom: 1px solid var(--border);
}
th {
    background: var(--bg-elevated);
    color: var(--accent-cyan);
    font-weight: 600;
    font-size: 0.85em;
    text-transform: uppercase;
    letter-spacing: 0.05em;
}
tr:hover {
    background: rgba(88, 166, 255, 0.05);
}
td:first-child {
    color: var(--text-bright);
    font-weight: 500;
}
code {
    background: var(--bg-elevated);
    border: 1px solid var(--border);
    padding: 0.15rem 0.5rem;
    border-radius: 4px;
    font-size: 0.88em;
    font-family: 'JetBrains Mono', 'Fira Code', 'Consolas', monospace;
    color: var(--accent-orange);
}
pre {
    background: var(--bg-card);
    border: 1px solid var(--border);
    padding: 1.2rem;
    border-radius: 8px;
    overflow-x: auto;
}
pre code {
    background: none;
    border: none;
    padding: 0;
    color: var(--text);
}
ul, ol {
    padding-left: 1.5rem;
}
li {
    margin-bottom: 0.5rem;
    line-height: 1.6;
}
li code {
    word-break: break-all;
    color: var(--text-dim);
    font-size: 0.85em;
    border-color: transparent;
    background: rgba(110, 118, 129, 0.1);
}
li strong {
    color: var(--accent-pink);
    font-weight: 600;
}
hr {
    border: none;
    height: 1px;
    background: linear-gradient(90deg, transparent, var(--border), transparent);
    margin: 2.5rem 0;
}
em {
    color: var(--text-dim);
    font-style: italic;
}
strong {
    color: var(--text-bright);
}
p strong:first-child {
    font-size: 1.4rem;
}
blockquote {
    border-left: 3px solid var(--accent-purple);
    margin: 1rem 0;
    padding: 0.5rem 1rem;
    background: var(--bg-card);
    border-radius: 0 6px 6px 0;
}
blockquote p {
    margin: 0;
    color: var(--text-dim);
}
.score-clean { color: var(--accent-green) !important; -webkit-text-fill-color: var(--accent-green) !important; }
.score-mild { color: var(--accent-yellow) !important; -webkit-text-fill-color: var(--accent-yellow) !important; }
.score-noticeable { color: var(--accent-orange) !important; -webkit-text-fill-color: var(--accent-orange) !important; }
.score-obvious { color: var(--accent-red) !important; -webkit-text-fill-color: var(--accent-red) !important; }
.score-blatant { color: #ff4466 !important; -webkit-text-fill-color: #ff4466 !important; text-shadow: 0 0 20px rgba(255, 68, 102, 0.3); }
footer, p:last-child em {
    color: var(--text-dim);
    font-size: 0.85em;
}
p code:only-child {
    display: inline-block;
    font-size: 1.1em;
    padding: 0.3rem 0.8rem;
    letter-spacing: 0.1em;
    background: var(--bg-card);
    border-color: var(--border);
}
::-webkit-scrollbar { width: 8px; height: 8px; }
::-webkit-scrollbar-track { background: var(--bg); }
::-webkit-scrollbar-thumb { background: var(--border); border-radius: 4px; }
::-webkit-scrollbar-thumb:hover { background: var(--text-dim); }
"""


def _escape_html(text: str) -> str:
    """Escape HTML-special characters to prevent XSS from user content."""
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


def _inline(text: str) -> str:
    """Convert inline markdown (code, bold, italic) to HTML."""
    text = _escape_html(text)
    text = re.sub(r"`([^`]+)`", r"<code>\1</code>", text)
    text = re.sub(r"\*\*\*(.+?)\*\*\*", r"<strong><em>\1</em></strong>", text)
    text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)
    text = re.sub(r"\*(.+?)\*", r"<em>\1</em>", text)
    text = re.sub(r"_(.+?)_", r"<em>\1</em>", text)
    return text


def md_to_html(md: str) -> str:
    """Convert markdown to HTML. Handles headings, bold, italic, code,
    tables, lists, blockquotes, horizontal rules, and paragraphs."""
    lines = md.split("\n")
    html = []
    in_table = False
    in_list = False
    list_type = None
    in_paragraph = False

    def close_list():
        nonlocal in_list, list_type
        if in_list:
            html.append(f"</{list_type}>")
            in_list = False
            list_type = None

    def close_paragraph():
        nonlocal in_paragraph
        if in_paragraph:
            html.append("</p>")
            in_paragraph = False

    def close_table():
        nonlocal in_table
        if in_table:
            html.append("</tbody></table>")
            in_table = False

    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        if not stripped:
            close_paragraph()
            close_list()
            i += 1
            continue

        if re.match(r"^---+$", stripped):
            close_paragraph()
            close_list()
            close_table()
            html.append("<hr>")
            i += 1
            continue

        # Headings
        m = re.match(r"^(#{1,6})\s+(.+)$", stripped)
        if m:
            close_paragraph()
            close_list()
            close_table()
            level = len(m.group(1))
            text = _inline(m.group(2))
            score_class = ""
            if level == 2:  # Only apply score classes to h2 score headings
                for label, cls in [("CLEAN", "clean"), ("MILD", "mild"),
                                   ("NOTICEABLE", "noticeable"), ("OBVIOUS", "obvious"),
                                   ("BLATANT", "blatant")]:
                    if f"[{label}]" in text:
                        score_class = f' class="score-{cls}"'
            html.append(f"<h{level}{score_class}>{text}</h{level}>")
            i += 1
            continue

        # Table
        if "|" in stripped and stripped.startswith("|"):
            close_paragraph()
            close_list()
            cells = [c.strip() for c in stripped.split("|")[1:-1]]

            if not in_table:
                if i + 1 < len(lines) and re.match(r"^\|[\s\-:|]+\|$", lines[i + 1].strip()):
                    html.append("<table><thead><tr>")
                    for c in cells:
                        html.append(f"<th>{_inline(c)}</th>")
                    html.append("</tr></thead><tbody>")
                    in_table = True
                    i += 2
                    continue
                else:
                    html.append("<table><thead><tr>")
                    for c in cells:
                        html.append(f"<th>{_inline(c)}</th>")
                    html.append("</tr></thead><tbody>")
                    in_table = True
                    i += 1
                    continue

            html.append("<tr>")
            for c in cells:
                html.append(f"<td>{_inline(c)}</td>")
            html.append("</tr>")
            i += 1
            continue

        if in_table and "|" not in stripped:
            close_table()

        # Unordered list
        m = re.match(r"^[-*]\s+(.+)$", stripped)
        if m:
            close_paragraph()
            close_table()
            if not in_list or list_type != "ul":
                close_list()
                html.append("<ul>")
                in_list = True
                list_type = "ul"
            html.append(f"<li>{_inline(m.group(1))}</li>")
            i += 1
            continue

        # Ordered list
        m = re.match(r"^\d+\.\s+(.+)$", stripped)
        if m:
            close_paragraph()
            close_table()
            if not in_list or list_type != "ol":
                close_list()
                html.append("<ol>")
                in_list = True
                list_type = "ol"
            html.append(f"<li>{_inline(m.group(1))}</li>")
            i += 1
            continue

        # Blockquote
        if stripped.startswith(">"):
            close_paragraph()
            close_list()
            close_table()
            text = _inline(stripped.lstrip("> "))
            html.append(f"<blockquote><p>{text}</p></blockquote>")
            i += 1
            continue

        # Regular paragraph text
        close_list()
        close_table()
        if not in_paragraph:
            html.append("<p>")
            in_paragraph = True
            html.append(_inline(stripped))
        else:
            html.append("<br>" + _inline(stripped))
        i += 1

    close_paragraph()
    close_list()
    close_table()
    return "\n".join(html)


def wrap_html(body: str, title: str = "AI Fingerprint Report") -> str:
    safe_title = _escape_html(title)
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{safe_title}</title>
<style>
{CSS}
</style>
</head>
<body>
{body}
</body>
</html>"""
