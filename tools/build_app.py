"""Build the app from data/vocab-final.json + app/template.html.

Run from the repo root:  python3 tools/build_app.py
Produces:
  app/data.json      readable copy of the word payload (one word per line)
  app/index.html     standalone page for any web server / Docker (full document)
  app/artifact.html  same page as a fragment, for publishing as a Claude Artifact
                     (the Artifact tool adds the document skeleton itself)
"""
import json, re

final = json.load(open('data/vocab-final.json'))
rows = []
for e in final:
    ex = e['ex']; marked = ''; exid = ''
    if ex:
        exid = ex['id']
        forms = sorted(set(e['forms']), key=len, reverse=True)
        pat = '|'.join(re.escape(f) for f in forms)
        # [[...]] marks the word to highlight inside the example sentence
        marked = re.sub(r'(?i)(?<!\w)(' + pat + r')(?!\w)', r'[[\1]]', ex['text']) if pat else ex['text']
    rows.append([e['head'], e['pos'], e['en'], e['ru'], e['note'] or '', marked, exid, e['q']])

payload = json.dumps(rows, ensure_ascii=False, separators=(',', ':')).replace('<', '\\u003c')
# app/data.json is the readable copy (one word per line); index.html embeds the compact payload
pretty = '[\n' + ',\n'.join('  ' + json.dumps(r, ensure_ascii=False, separators=(', ', ': ')).replace('<', '\\u003c') for r in rows) + '\n]\n'
assert json.loads(pretty) == json.loads(payload)
open('app/data.json', 'w').write(pretty)
tpl = open('app/template.html').read()
assert tpl.count('/*DATA*/') == 1
fragment = tpl.replace('/*DATA*/', payload)
open('app/artifact.html', 'w').write(fragment)

# Same skeleton the Artifact host wraps around the fragment: charset, viewport and a small reset.
# The page relies on [hidden]{display:none!important}, so the reset is required.
SKELETON_HEAD = (
    '<!doctype html>\n<html lang="en">\n<head>\n<meta charset="utf-8">\n'
    '<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">\n'
    '<style>:root{color-scheme:light;padding-top:env(safe-area-inset-top,0px);padding-bottom:env(safe-area-inset-bottom,0px)}'
    'body{margin:0;font:14px system-ui,sans-serif}img{max-width:100%}[hidden]{display:none!important}</style>\n'
    '</head>\n<body>\n'
)
open('app/index.html', 'w').write(SKELETON_HEAD + fragment + '\n</body>\n</html>\n')
print(f'{len(rows)} words; app/index.html (standalone) and app/artifact.html (fragment) written')
