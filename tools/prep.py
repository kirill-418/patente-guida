import json, re, collections
v = json.load(open('out/vocab.json')); q = v['qcount']; r = v['rank']; f = v['forms']
lines = [l.strip() for l in open('../quiz/quiz-patente-AB.md') if l.startswith('- **') and '→' in l and ' — ' in l]
Q = []
for l in lines:
    m = re.match(r'^- \*\*(\d+)\*\* — (.*) → \*\*.*$', l); Q.append((m.group(1), m.group(2)))
tok = lambda s: re.findall(r"[a-zA-Zàèéìòóùç]+", s.lower())
form2q = collections.defaultdict(set)
for i, (_, t) in enumerate(Q):
    for w in set(tok(t)): form2q[w].add(i)
cands = [L for L in q if (r[L] is None or r[L] > 5000)]
cands.sort(key=lambda L: (-q[L], L))
print('candidates', len(cands))
items = []
for L in cands:
    idx = set()
    for w in f[L]: idx |= form2q[w]
    ex = sorted(idx, key=lambda i: len(Q[i][1]))[:2]
    items.append(dict(lemma=L, questions=q[L], forms=sorted(f[L], key=lambda w: -f[L][w]), examples=[dict(id=Q[i][0], text=Q[i][1]) for i in ex]))
json.dump(items, open('vocab/all_items.json', 'w'), ensure_ascii=False, indent=0)
N = 9; size = -(-len(items) // N)
for k in range(N):
    chunk = items[k*size:(k+1)*size]
    json.dump(chunk, open(f'vocab/in/chunk{k+1}.json', 'w'), ensure_ascii=False, indent=0)
    print(k+1, len(chunk), chunk[0]['lemma'], chunk[0]['questions'], '...', chunk[-1]['lemma'], chunk[-1]['questions'])
