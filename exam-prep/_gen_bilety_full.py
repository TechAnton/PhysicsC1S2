# -*- coding: utf-8 -*-
"""Generate билеты.html with full lecture content."""
import html as html_mod
import re
from pathlib import Path

ROOT = Path(__file__).parent.parent
LECTURES = sorted((ROOT / "lectures").glob("*.md"))

PRIORITY = {1,2,3,5,7,8,9,10,12,13,20,22,29,32,35,36,38,39,41,42}

CSS = """
:root { --bg:#f0f4f8; --card:#fff; --accent:#1e40af; --red:#b91c1c; --text:#111827; --muted:#6b7280; --border:#d1d5db; --hover:#dbeafe; }
* { box-sizing:border-box; margin:0; padding:0; }
body { font:14px/1.6 'Segoe UI',system-ui,sans-serif; background:var(--bg); color:var(--text); }
header { background:var(--card); border-bottom:1px solid var(--border); padding:14px 20px; text-align:center; position:sticky; top:0; z-index:100; box-shadow:0 1px 4px rgba(0,0,0,.06); }
header h1 { font-size:1.15rem; margin-bottom:4px; }
header p { font-size:.8rem; color:var(--muted); }
header a { color:var(--accent); }
.layout { display:flex; max-width:1280px; margin:0 auto; min-height:calc(100vh - 70px); }
.topics { width:38%; max-width:440px; border-right:1px solid var(--border); background:var(--card); overflow-y:auto; max-height:calc(100vh - 70px); position:sticky; top:70px; flex-shrink:0; }
.topics h2 { font-size:.75rem; text-transform:uppercase; letter-spacing:.05em; color:var(--muted); padding:12px 14px 6px; }
.topic-btn { display:flex; gap:8px; width:100%; text-align:left; padding:10px 14px; border:none; border-bottom:1px solid var(--border); background:transparent; cursor:pointer; font:inherit; line-height:1.35; transition:background .15s; }
.topic-btn:hover { background:var(--hover); }
.topic-btn.active { background:var(--hover); border-left:3px solid var(--accent); padding-left:11px; }
.topic-btn .num { flex-shrink:0; font-weight:800; color:var(--red); min-width:22px; }
.topic-btn .title { font-size:.8rem; }
.topic-btn .tag { flex-shrink:0; font-size:.6rem; background:#fee2e2; color:var(--red); padding:1px 5px; border-radius:3px; height:fit-content; margin-top:2px; }
.content { flex:1; padding:20px 28px 40px; overflow-y:auto; min-width:0; }
.placeholder { color:var(--muted); text-align:center; padding:60px 20px; }
.answer { display:none; }
.answer.active { display:block; }
.answer-body { background:var(--card); border:1px solid var(--border); border-radius:8px; padding:20px 24px; }
.answer-body h2 { font-size:1.1rem; color:var(--accent); margin-bottom:16px; line-height:1.4; border-bottom:2px solid var(--border); padding-bottom:10px; }
.answer-body h2 .num { color:var(--red); font-weight:800; }
.answer-body h3 { font-size:1rem; color:var(--accent); margin:18px 0 8px; }
.answer-body h4 { font-size:.92rem; color:#374151; margin:14px 0 6px; }
.answer-body p { margin:8px 0; font-size:.9rem; }
.answer-body ul, .answer-body ol { margin:8px 0 8px 20px; font-size:.88rem; }
.answer-body li { margin-bottom:4px; }
.answer-body blockquote { background:#ecfdf5; border-left:4px solid #10b981; padding:10px 14px; margin:12px 0; font-size:.9rem; border-radius:0 6px 6px 0; }
.answer-body table { width:100%; border-collapse:collapse; margin:10px 0; font-size:.85rem; }
.answer-body th, .answer-body td { border:1px solid var(--border); padding:6px 10px; text-align:left; }
.answer-body th { background:#f3f4f6; }
.answer-body hr { border:none; border-top:1px solid var(--border); margin:16px 0; }
.answer-body code { background:#e5e7eb; padding:1px 5px; border-radius:3px; font-size:.85em; }
.answer-body pre { background:#1e293b; color:#e2e8f0; padding:12px; border-radius:6px; overflow-x:auto; margin:10px 0; font-size:.82rem; white-space:pre; }
.answer-body strong { color:#1f2937; }
.mjx-block { margin:12px 0; overflow-x:auto; }
@media (max-width:768px) {
  .layout { flex-direction:column; }
  .topics { width:100%; max-width:none; max-height:38vh; position:relative; top:0; }
  .content { padding:14px; }
}
@media print { .topics, header p { display:none; } .answer { display:block!important; page-break-after:always; } }
"""


def protect_math(text: str) -> tuple[str, dict]:
    store = {}
    n = 0

    def repl_display(m):
        nonlocal n
        key = f'%%MATHD{n}%%'
        inner = m.group(1).strip()
        store[key] = f'<div class="mjx-block">\\[{inner}\\]</div>'
        n += 1
        return key

    def repl_inline(m):
        nonlocal n
        key = f'%%MATHI{n}%%'
        store[key] = f'\\({m.group(1)}\\)'
        n += 1
        return key

    text = re.sub(r'\$\$(.+?)\$\$', repl_display, text, flags=re.DOTALL)
    text = re.sub(r'(?<!\$)\$(?!\$)(.+?)(?<!\$)\$(?!\$)', repl_inline, text)
    return text, store


def restore_math(text: str, store: dict) -> str:
    for k, v in store.items():
        text = text.replace(k, v)
    return text


def inline_fmt(text: str) -> str:
    text = html_mod.escape(text)
    text = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', text)
    text = re.sub(r'`([^`]+)`', r'<code>\1</code>', text)
    return text


def md_to_html(md: str) -> str:
    md, math_store = protect_math(md)
    lines = md.split('\n')
    out = []
    i = 0
    in_table = False
    table_rows = []

    def flush_table():
        nonlocal table_rows, in_table
        if not table_rows:
            return
        out.append('<table>')
        for ri, row in enumerate(table_rows):
            tag = 'th' if ri == 0 else 'td'
            out.append('<tr>' + ''.join(f'<{tag}>{inline_fmt(c)}</{tag}>' for c in row) + '</tr>')
        out.append('</table>')
        table_rows = []
        in_table = False

    while i < len(lines):
        line = lines[i]

        if re.match(r'^#\s+\d+\.', line):
            i += 1
            continue

        if '|' in line and line.strip().startswith('|'):
            if re.match(r'^\|[\s\-:|]+\|$', line.strip()):
                i += 1
                continue
            cells = [c.strip() for c in line.strip().strip('|').split('|')]
            table_rows.append(cells)
            in_table = True
            i += 1
            continue
        elif in_table:
            flush_table()

        if line.strip() == '---':
            out.append('<hr>')
            i += 1
            continue

        if line.startswith('```'):
            lang = line[3:].strip()
            i += 1
            buf = []
            while i < len(lines) and not lines[i].startswith('```'):
                buf.append(lines[i])
                i += 1
            out.append('<pre>' + html_mod.escape('\n'.join(buf)) + '</pre>')
            i += 1
            continue

        if line.startswith('## '):
            out.append(f'<h3>{inline_fmt(line[3:].strip())}</h3>')
            i += 1
            continue

        if line.startswith('### '):
            out.append(f'<h4>{inline_fmt(line[4:].strip())}</h4>')
            i += 1
            continue

        if line.startswith('> '):
            out.append(f'<blockquote>{inline_fmt(line[2:].strip())}</blockquote>')
            i += 1
            continue

        if re.match(r'^[\-\*]\s+', line):
            out.append('<ul>')
            while i < len(lines) and re.match(r'^[\-\*]\s+', lines[i]):
                out.append(f'<li>{inline_fmt(lines[i][2:].strip())}</li>')
                i += 1
            out.append('</ul>')
            continue

        if re.match(r'^\d+\.\s+', line):
            out.append('<ol>')
            while i < len(lines) and re.match(r'^\d+\.\s+', lines[i]):
                item = re.sub(r'^\d+\.\s+', '', lines[i]).strip()
                out.append(f'<li>{inline_fmt(item)}</li>')
                i += 1
            out.append('</ol>')
            continue

        if line.strip():
            para = line.strip()
            i += 1
            while i < len(lines):
                nxt = lines[i]
                if not nxt.strip():
                    break
                if nxt.startswith('#') or nxt.startswith('>') or nxt.startswith('|') or nxt.strip() == '---' or nxt.startswith('```'):
                    break
                if re.match(r'^[\-\*]\s+', nxt) or re.match(r'^\d+\.\s+', nxt):
                    break
                para += ' ' + nxt.strip()
                i += 1
            restored = restore_math(inline_fmt(para), math_store)
            if restored.strip().startswith('<div class="mjx-block">') and restored.count('<div') == 1:
                out.append(restored)
            else:
                out.append(f'<p>{restored}</p>')
            continue

        i += 1

    flush_table()
    return restore_math('\n'.join(out), math_store)


def extract_title(md: str) -> str:
    m = re.search(r'^#\s+\d+\.\s+(.+)$', md, re.MULTILINE)
    return m.group(1).strip() if m else "Билет"


def main():
    tickets = []
    for path in LECTURES:
        num = int(path.name[:2])
        md = path.read_text(encoding='utf-8')
        title = extract_title(md)
        body = md_to_html(md)
        tickets.append((num, title, body))

    tickets.sort(key=lambda x: x[0])

    parts = [
        '<!DOCTYPE html><html lang="ru"><head><meta charset="UTF-8">',
        '<meta name="viewport" content="width=device-width,initial-scale=1">',
        '<title>Физика C1S2 — полные ответы по билетам</title>',
        f'<style>{CSS}</style>',
        '<script>window.MathJax={tex:{inlineMath:[["\\\\(","\\\\)"]],displayMath:[["\\\\[","\\\\]"]]},startup:{typeset:false}};</script>',
        '<script src="https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-chtml.js" async></script>',
        '</head><body>',
        '<header><h1>Физика C1S2 — полные ответы по билетам</h1>',
        '<p>Нажми тему слева · полный готовый ответ · <a href="шпаргалка.html">Шпаргалка</a></p></header>',
        '<div class="layout"><aside class="topics"><h2>Все 42 билета</h2>',
    ]

    for num, title, _ in tickets:
        tag = '<span class="tag">!</span>' if num in PRIORITY else ''
        parts.append(
            f'<button class="topic-btn" data-n="{num}" onclick="show({num})">'
            f'<span class="num">{num}</span>'
            f'<span class="title">{html_mod.escape(title)}</span>{tag}</button>'
        )

    parts.append('</aside><main class="content" id="content">')
    parts.append('<div class="placeholder" id="placeholder">← Выбери билет из списка слева</div>')

    for num, title, body in tickets:
        parts.append(f'<div class="answer" id="a{num}"><div class="answer-body">')
        parts.append(f'<h2><span class="num">{num}.</span> {html_mod.escape(title)}</h2>')
        parts.append(body)
        parts.append('</div></div>')

    parts.append('''</main></div>
<script>
function show(n) {
  document.querySelectorAll('.topic-btn').forEach(b => b.classList.toggle('active', +b.dataset.n === n));
  document.querySelectorAll('.answer').forEach(a => a.classList.remove('active'));
  document.getElementById('placeholder').style.display = 'none';
  const el = document.getElementById('a' + n);
  el.classList.add('active');
  if (window.MathJax && MathJax.typesetPromise) MathJax.typesetPromise([el]);
  if (window.innerWidth <= 768) document.getElementById('content').scrollIntoView({behavior:'smooth'});
}
const m = location.hash.match(/^#b(\\d+)$/);
if (m) show(+m[1]); else show(1);
</script></body></html>''')

    out_path = Path(__file__).parent / 'билеты.html'
    content = ''.join(parts)
    out_path.write_text(content, encoding='utf-8')
    print(f'OK: {len(content)} chars, {len(tickets)} tickets -> {out_path}')


if __name__ == '__main__':
    main()
