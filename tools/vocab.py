import re, collections, simplemma
lines = [l for l in open('../quiz/quiz-patente-AB.md') if l.startswith('- **') and ' — ' in l and '→' in l]
qs = [re.sub(r'^- \*\*\d+\*\* — (.*) → \*\*.*$', r'\1', l.strip()) for l in lines]
print('questions', len(qs))
tok = lambda s: re.findall(r"[a-zA-Zàèéìòóùç]+", s.lower())
lem = lambda w: simplemma.lemmatize(w, lang='it')
# general-language rank by lemma
rank = {}; r = 0
for l in open('dl/freq/it_50k.txt'):
    w = l.split()[0]
    for x in {w, lem(w)}:
        pass
    L = lem(w)
    if L not in rank: r += 1; rank[L] = r
qcount = collections.Counter(); forms = collections.defaultdict(collections.Counter)
for q in qs:
    seen = set()
    for w in tok(q):
        if len(w) < 3: continue
        L = lem(w); forms[L][w] += 1
        if L not in seen: qcount[L] += 1; seen.add(L)
print('distinct lemmas', len(qcount))
import json
json.dump({'qcount': qcount, 'rank': {k: rank.get(k) for k in qcount}, 'forms': {k: dict(v) for k, v in forms.items()}}, open('out/vocab.json', 'w'), ensure_ascii=False)
def bucket(L):
    r = rank.get(L); return 'absent' if r is None else ('<=3000' if r<=3000 else '<=5000' if r<=5000 else '<=10000' if r<=10000 else '<=20000' if r<=20000 else '<=50000')
b = collections.Counter(bucket(L) for L in qcount); print(b)
for name in ['absent','<=50000','<=20000']:
    xs = sorted([L for L in qcount if bucket(L)==name], key=lambda L: -qcount[L])
    print(name, len(xs), xs[:60])
