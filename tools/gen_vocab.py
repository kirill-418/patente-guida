import json, re, collections
OUT = '../vocab/vocabolario-rare-patente-B.md'
ins = []; outs = []
for k in range(1, 10):
    ins += json.load(open(f'vocab/in/chunk{k}.json')); outs += json.load(open(f'vocab/out/chunk{k}.json'))
# question index
Q = []
for l in open('../quiz/quiz-patente-AB.md'):
    m = re.match(r'^- \*\*(\d+)\*\* — (.*) → \*\*(.*)\*\*$', l.strip())
    if m: Q.append((m.group(1), m.group(2)))
tok = lambda s: re.findall(r"[a-zA-Zàèéìòóùç]+", s.lower())
form2q = collections.defaultdict(set)
for i, (_, t) in enumerate(Q): 
    for w in set(tok(t)): form2q[w].add(i)

# manual additions for skipped-but-meaningful abbreviations / terms
manual = {
 'asl': dict(head='ASL', pos='abbr.', en='ASL — local health authority (Azienda Sanitaria Locale)', ru='ASL — местное управление здравоохранения', ex=0),
 'lsd': dict(head='LSD', pos='abbr.', en='LSD (lysergic acid diethylamide, a hallucinogenic drug)', ru='ЛСД (галлюциногенный наркотик)', ex=0),
 'bull': dict(head='bull bar', pos='n.m.', en='bull bar (reinforced front bumper on SUVs)', ru='кенгурятник', ex=0),
}
entries = []
dropped_proper = []
for i, o in zip(ins, outs):
    L = i['lemma']
    if L in manual: o = dict(o, **manual[L], skip=False)
    elif L == 'bars': continue                      # merged into 'bull'
    if o.get('skip'): continue
    head = o['head'].strip()
    if head[:1].isupper() and o['pos'] != 'abbr.': dropped_proper.append(head); continue
    entries.append(dict(lemma=L, head=head, pos=o['pos'], en=o['en'], ru=o['ru'], note=o.get('note', ''),
                        forms=list(i['forms']) + (['bars'] if L == 'bull' else []), examples=i['examples'], ex=o.get('ex', 0), q=i['questions']))
# merge by head
groups = collections.OrderedDict()
for e in entries: groups.setdefault(e['head'].lower(), []).append(e)
final = []
for h, es in groups.items():
    es.sort(key=lambda e: -e['q']); p = es[0]
    def merge(key):
        items = [x.strip() for x in p[key].split(';')]
        for e in es[1:]:
            for x in e[key].split(';'):
                x = x.strip()
                if x and x.lower() not in [y.lower() for y in items]: items.append(x)
        return '; '.join(items[:4])
    forms = []
    for e in es:
        for f in e['forms']:
            if f not in forms: forms.append(f)
    idx = set()
    for f in forms: idx |= form2q.get(f, set())
    ex = p['examples'][p['ex']] if p['examples'] else None
    final.append(dict(head=p['head'], pos=p['pos'], en=merge('en'), ru=merge('ru'), note=('' if 'emmatiz' in p['note'] else p['note']), forms=forms, ex=ex, q=len(idx) or p['q']))
final.sort(key=lambda e: (-e['q'], e['head'].lower()))
print('entries', len(entries), 'merged', len(final), 'dropped proper nouns', len(dropped_proper), dropped_proper)

esc = lambda s: s.replace('|', '\\|')
def hl(text, forms):
    for f in sorted(forms, key=len, reverse=True):
        text = re.sub(r'(?i)\b(' + re.escape(f) + r')\b', r'**\1**', text)
    return text
tiers = [('A', 'Molto frequenti — 50+ domande', 50, 10**9), ('B', 'Frequenti — 10–49 domande', 10, 49),
         ('C', 'Medie — 3–9 domande', 3, 9), ('D', 'Rare — 1–2 domande', 1, 2)]
L = ['# Vocabolario raro — Patente B (Italiano → English / Русский)', '',
     'Parole rare dei quiz ufficiali per la **patente B** (7.020 domande, MIT), con traduzione nel contesto della guida e dell\'esame.', '',
     '## Come è stato costruito', '',
     f'- **Fonte:** `quiz-patente-AB.md` — lista ufficiale MIT, categoria B.',
     '- **Definizione di "rara":** il lemma NON è tra i 5.000 lemmi più frequenti dell\'italiano (lista di frequenza OpenSubtitles 2018, `hermitdave/FrequencyWords`) oppure non compare affatto in quella lista, **e** appare in almeno 1 domanda. Sono incluse anche parole senza significato stradale. Esclusi: nomi propri (città, regioni, paesi) e frammenti.',
     '- **Lemmatizzazione:** `simplemma` (correzioni manuali dove sbagliava, p.es. *carreggiare* → *carreggiata*). Forme diverse della stessa parola sono unite in una voce.',
     '- **Traduzioni:** prima il senso stradale/d\'esame, poi eventuali altri sensi. Generate da modello e non verificate parola per parola da un madrelingua.',
     '- **Colonna "Dom."** = numero di domande del quiz che contengono la parola (tutte le sue forme). Esempi in grassetto con numero domanda ufficiale.',
     f'- **Voci totali:** {len(final)}', '', '## Indice', '']
for t, name, lo, hi in tiers:
    n = sum(1 for e in final if lo <= e['q'] <= hi)
    L.append(f'- [{t}. {name}](#livello-{t.lower()}) — {n} parole')
L.append('')
for t, name, lo, hi in tiers:
    es = [e for e in final if lo <= e['q'] <= hi]
    L += [f'<a id="livello-{t.lower()}"></a>', f'## {t}. {name} ({len(es)})', '',
          '| # | Italiano | English | Русский | Dom. | Esempio dal quiz |', '|---:|---|---|---|---:|---|']
    for n, e in enumerate(es, 1):
        forms = ', '.join([f for f in e['forms'] if f != e['head'].lower()][:5])
        it = f'**{esc(e["head"])}** <sub>{e["pos"]}</sub>' + (f'<br><sub>({esc(forms)})</sub>' if forms else '')
        en = esc(e['en']) + (f'<br><sub><i>{esc(e["note"])}</i></sub>' if e['note'] else '')
        ex = f'{esc(hl(e["ex"]["text"], e["forms"]))} <sub>#{e["ex"]["id"]}</sub>' if e['ex'] else ''
        L.append(f'| {n} | {it} | {en} | {esc(e["ru"])} | {e["q"]} | {ex} |')
    L.append('')
open(OUT, 'w').write('\n'.join(L))
import os; print(os.path.getsize(OUT)//1024, 'KB')
# verify user's test words
for w in ['allorché','restringimento','omologare','sovraccarico','sovrannumero','risarcimento','smaltimento']:
    hit = [e for e in final if e['head'].lower()==w or w in [f.lower() for f in e['forms']]]
    print(w, [(e['head'], e['q'], e['en'], e['ru']) for e in hit])
json.dump(final, open('vocab/final.json','w'), ensure_ascii=False)
