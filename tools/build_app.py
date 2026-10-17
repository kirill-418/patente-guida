"""Build app/index.html from data/vocab-final.json + app/template.html.

Run from the repo root:  python3 tools/build_app.py
Produces app/data.json (compact payload) and app/index.html (single static file).
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
open('app/data.json', 'w').write(payload)
tpl = open('app/template.html').read()
assert tpl.count('/*DATA*/') == 1
open('app/index.html', 'w').write(tpl.replace('/*DATA*/', payload))
print(f'{len(rows)} words, index.html {len(tpl) + len(payload)} bytes')
