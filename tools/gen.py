import json, collections, os, shutil
S = '.'
OUT = '../quiz'
B = 'https://www.ilportaledellautomobilista.it/documents/56611'
LISTS = [
 ('ab',    'Patente A e B (conseguimento)',            'AB',          'Patenti A1, A2, A, B1, B, BE — esame di teoria',
  f'{B}/57319/210926_Conseguimento+A-B+italiano.pdf/07091bb8-a16b-4fa1-b921-4fd21fa5b650', '30 domande V/F, 20 min, max 3 errori'),
 ('am',    'Patente AM (ciclomotori)',                  'AM',          'Patente AM — esame di teoria',
  f'{B}/57321/Domande+AM+italiano+04+04+2025/ad547e38-92c7-4f92-850d-487be020ccc3', ''),
 ('sup',   'Patenti superiori (C, D, CE, DE ...)',      'Superiori',   'Patenti C1, C, D1, D, C1E, CE, D1E, DE — esame di teoria',
  f'{B}/57321/Domande+Superiori+italiano+04+04+2025/7763ce74-4de6-4ad9-9129-7a7c21efd1fb', ''),
 ('revab', 'Revisione patente A e B',                   'Revisione-AB','Esame di revisione (patente A/B)',
  f'{B}/57321/domande+revisione+AB+italiano+23+04+2025/f06e544b-db67-40f4-a5db-2a21f5896521', ''),
 ('revam', 'Revisione patente AM',                      'Revisione-AM','Esame di revisione (patente AM)',
  f'{B}/57321/Domande+Revisione+AM+italiano+04+04+2025/4f244772-9daf-4ffd-91e4-a60707127f98', ''),
 ('revsup','Revisione patenti superiori',               'Revisione-Superiori','Esame di revisione (patenti superiori)',
  f'{B}/57321/Domande+Revisione+Superiore+Italiano+04+04+2025/43dea719-a62a-4d69-97fd-131c64276490', ''),
]

def merge_titles(rows):
    titles = sorted({r['chapter'] for r in rows}, key=len, reverse=True)
    m = {}
    for t in titles:
        longer = [u for u in titles if len(u) > len(t) and u.startswith(t)]
        m[t] = longer[0] if longer else t
    return m

os.makedirs(f'{OUT}/images', exist_ok=True)
index = []
for key, title, fname, desc, url, extra in LISTS:
    rows = json.load(open(f'{S}/out/{key}.json'))
    m = merge_titles(rows)
    for r in rows: r['chapter'] = m[r['chapter']]
    # copy images
    imgsrc = f'{S}/out/img_{key}'
    for f in os.listdir(imgsrc): shutil.copy(f'{imgsrc}/{f}', f'{OUT}/images/{f}')
    chapters = collections.OrderedDict()
    for r in rows: chapters.setdefault(r['chapter'], []).append(r)
    vero = sum(r['answer'] == 'VERO' for r in rows)
    L = [f'# Quiz teoria — {title}', '',
         f'- **Fonte ufficiale:** Ministero delle Infrastrutture e dei Trasporti — [Il Portale dell\'Automobilista, "Quiz per le patenti AM, B, superiori e CQC"](https://www.ilportaledellautomobilista.it/web/portale-automobilista/-/quiz-per-le-patenti-am-b-superiori-e-cqc)',
         f'- **File originale (PDF):** {url}',
         f'- **Scaricato:** 2026-10-17 (listato in vigore, valido per il 2026)',
         f'- **Ambito:** {desc}',
         f'- **Domande:** {len(rows)} ({vero} VERO / {len(rows)-vero} FALSO), {len(chapters)} sezioni, {len(set(r["image"] for r in rows if r["image"]))} figure']
    if extra: L.append(f'- **Formato esame:** {extra}')
    L += ['', 'Ogni domanda: `numero` — testo → risposta corretta. Le figure si trovano in `images/`.', '', '## Indice', '']
    for i, c in enumerate(chapters, 1):
        L.append(f'{i}. [{c}](#sezione-{i}) ({len(chapters[c])})')
    L.append('')
    for i, (c, rs) in enumerate(chapters.items(), 1):
        L += [f'<a id="sezione-{i}"></a>', f'## {i}. {c}', '']
        for r in rs:
            mark = '✅ VERO' if r['answer'] == 'VERO' else '❌ FALSO'
            L.append(f'- **{r["id"]}** — {r["text"]} → **{mark}**')
            if r['image']: L.append(f'  <br><img src="images/{r["image"]}" width="110" alt="figura">')
        L.append('')
    fn = f'quiz-patente-{fname}.md'
    open(f'{OUT}/{fn}', 'w').write('\n'.join(L))
    index.append((fn, title, len(rows), len(chapters)))
    print(fn, len(rows), len(chapters), os.path.getsize(f'{OUT}/{fn}')//1024, 'KB')
