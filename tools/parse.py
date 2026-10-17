import pymupdf, re, sys, json, os

SKIP = {'Numero', 'domanda', 'Testo domanda', 'Risposta Corretta', 'Immagine', 'Numero domanda'}

def norm(s): return re.sub(r'\s+', ' ', s).strip()

def parse(pdf, imgdir, imgprefix):
    d = pymupdf.open(pdf)
    os.makedirs(imgdir, exist_ok=True)
    rows = []
    chapter = group = None
    seen, hash2file = {}, {}
    def save_img(xref):
        if xref in seen: return seen[xref]
        info = d.extract_image(xref)
        h = hash(info['image'])
        if h not in hash2file:
            fn = f"{imgprefix}{len(hash2file)+1:04d}.{info['ext']}"
            with open(os.path.join(imgdir, fn), 'wb') as f: f.write(info['image'])
            hash2file[h] = fn
        seen[xref] = hash2file[h]
        return seen[xref]
    pending = None  # row awaiting continuation across page
    for pno, page in enumerate(d):
        lines = []
        for b in page.get_text('dict')['blocks']:
            if b.get('type') != 0: continue
            for l in b['lines']:
                # split a line into column segments (text column vs answer column)
                left_spans = [s for s in l['spans'] if s['bbox'][0] < 330]
                right_spans = [s for s in l['spans'] if s['bbox'][0] >= 330]
                for spans in (left_spans, right_spans):
                    t = norm(''.join(s['text'] for s in spans))
                    if t: lines.append((l['bbox'][1], spans[0]['bbox'][0], t))
        lines.sort()
        imgs = [i for i in page.get_image_info(xrefs=True) if i.get('xref')]
        # events: heads (with continuation), ids
        events = []  # (y, kind, payload)
        i = 0
        left = [l for l in lines if l[1] < 60]
        # build headings
        j = 0
        while j < len(left):
            y, x, t = left[j]
            if t.startswith('Quesito n'):
                full = t; k = j + 1
                while k < len(left) and left[k][2] not in SKIP and not re.fullmatch(r'\d{3,6}', left[k][2]) and not left[k][2].startswith('Quesito n'):
                    full += ' ' + left[k][2]; k += 1
                m = re.match(r'Quesito n° (\d+) - (.*)', full)
                events.append((y, 'head', (m.group(1), m.group(2).strip())))
                j = k; continue
            if re.fullmatch(r'\d{3,6}', t): events.append((y, 'id', t))
            j += 1
        events.sort(key=lambda e: e[0])
        # create rows in order
        page_rows = []
        for y, kind, payload in events:
            if kind == 'head': group, chapter = payload; continue
            r = dict(id=payload, y=y, text=[], answer=None, chapter=chapter, group=group, image=None, page=pno+1)
            page_rows.append(r)
        for y, x, t in lines:
            if x < 60 or t in SKIP: continue
            owner = None
            for r in page_rows:
                if r['y'] <= y + 3: owner = r
            if owner is None: owner = pending
            if owner is None: continue
            if x >= 330:
                if t in ('VERO', 'FALSO'): owner['answer'] = t
            else:
                owner['text'].append((y, x, t))
        # images
        for k, r in enumerate(page_rows):
            top = r['y'] - 4
            bot = page_rows[k+1]['y'] - 4 if k + 1 < len(page_rows) else 1e9
            # next heading may sit between rows; also bound by following head
            im = [i for i in imgs if top <= (i['bbox'][1] + i['bbox'][3]) / 2 < bot]
            if im: r['image'] = save_img(im[0]['xref'])
        for r in page_rows:
            r['text'] = norm(' '.join(t for _, _, t in sorted(r['text'])))
            del r['y']
            rows.append(r)
        pending = rows[-1] if rows else None
    return rows

if __name__ == '__main__':
    pdf, imgdir, prefix, out = sys.argv[1:5]
    rows = parse(pdf, imgdir, prefix)
    json.dump(rows, open(out, 'w'), ensure_ascii=False, indent=2)
    ids = [r['id'] for r in rows]
    print(pdf, 'rows', len(rows), 'unique', len(set(ids)),
          'noanswer', sum(r['answer'] is None for r in rows),
          'notext', sum(not r['text'] for r in rows),
          'nochapter', sum(r['chapter'] is None for r in rows),
          'withimg', sum(r['image'] is not None for r in rows),
          'imgfiles', len(set(r['image'] for r in rows if r['image'])))
