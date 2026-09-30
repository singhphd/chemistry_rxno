#!/usr/bin/env python3
"""Build the RXNO name-reaction reagent list.

Sources per reaction:
  ontology  - has_catalyst (RXNO:0000425) relationships in rxno.obo
  curated   - curated_reagents.tsv (standard literature reagents)
Parent-class reagents are listed for context only (parent_class_reagents_unverified) and
never count as a reaction's own reagents. Reactions without curated reagents (including
catalyst-only ontology records) are written to unresolved.tsv.
Run from the repo root:  python3 reagents/build_reagents.py
"""
import csv, json, re, collections, pathlib

root = pathlib.Path(__file__).resolve().parent
obo = root.parent / 'rxno.obo'
NAME_RE = re.compile(r'^(\[?[\d,]*\]?-?[A-Z0-9][^ ]*.*)$')

terms = {}
for blk in obo.read_text().split('\n['):
    if not blk.startswith('Term]'):
        continue
    d = dict(id=None, name='', defn='', isa=[], cat=[], xref=[], syn=[], obs=False)
    for line in blk.split('\n')[1:]:
        k, _, v = line.partition(': ')
        if k == 'id': d['id'] = v
        elif k == 'name': d['name'] = v
        elif k == 'def':
            m = re.match(r'"(.*)" \[', v); d['defn'] = m.group(1) if m else v
        elif k == 'is_a': d['isa'].append(v.split(' !')[0])
        elif k == 'xref': d['xref'].append(v)
        elif k == 'synonym': d['syn'].append(v.split('"')[1])
        elif k == 'is_obsolete': d['obs'] = True
        elif k == 'relationship' and v.startswith('RXNO:0000425'):
            d['cat'].append(v.split('! has_catalyst ')[1])
    if d['id'] and d['id'].startswith('RXNO:') and not d['obs']:
        terms[d['id']] = d

cur = {}
for r in csv.reader((l for l in open(root / 'curated_reagents.tsv') if not l.startswith('#')), delimiter='\t'):
    r += [''] * (4 - len(r))
    cur['RXNO:' + r[0]] = dict(reagents=r[1], catalyst=r[2], conditions=r[3])

# name reactions: explicit rule (any of)
#  - Merck Index xref (RXNO xref to rsc.org/Merck-Index)
#  - an entry in curated_reagents.tsv
#  - proper-name term (capitalised name, not an N-/O- acylation class)
def is_named(t):
    n = t['name']
    if t['id'] in cur or any('Merck' in x for x in t['xref']):
        return True
    return bool(re.search(r'[A-Z]', n[:1] if n[:1].isalpha() else n)) and not n.startswith(('N-', 'O-'))
named = {i: t for i, t in terms.items() if is_named(t) and i != 'RXNO:0000001'}

def ancestors(i, seen=None):
    seen = seen or set()
    for p in terms.get(i, {}).get('isa', []):
        if p in terms and p not in seen:
            seen.add(p); yield p; yield from ancestors(p, seen)

rows, unresolved = [], []
for i in sorted(named):
    t = named[i]
    reag, cat, cond, parent = '', '; '.join(t['cat']), '', ''
    if i in cur:
        c = cur[i]; reag, cond = c['reagents'], c['conditions']
        cat = '; '.join(x for x in [c['catalyst'], cat] if x)
    else:
        # parent-class reagents are shown for context only; never counted as this reaction's reagents
        for a in ancestors(i):
            if a in cur and a in named:
                parent = f"{terms[a]['name']}: {cur[a]['reagents']}"; break
    src = '+'.join(x for x, ok in (('curated', i in cur), ('ontology', bool(t['cat']))) if ok)
    row = dict(id=i, name=t['name'], reagents=reag, catalyst=cat, conditions=cond,
               source=src, parent_class_reagents_unverified=parent,
               merck_index=next((x for x in t['xref'] if 'Merck' in x), ''),
               wikidata=next((x for x in t['xref'] if 'wikidata' in x), ''),
               definition=t['defn'])
    (rows if reag else unresolved).append(row)

fields = list(rows[0].keys())
def dump(path, data):
    with open(root / path, 'w', newline='') as f:
        w = csv.DictWriter(f, fields, delimiter='\t'); w.writeheader(); w.writerows(data)
dump('name_reaction_reagents.tsv', rows)
dump('unresolved.tsv', unresolved)
json.dump(rows, open(root / 'name_reaction_reagents.json', 'w'), indent=1, ensure_ascii=False)

def split_top(text):
    """Split on semicolons that are not inside parentheses."""
    out, depth, cur_ = [], 0, ''
    for ch in text:
        depth += ch == '('; depth -= ch == ')'
        if ch == ';' and depth == 0:
            out.append(cur_); cur_ = ''
        else:
            cur_ += ch
    return out + [cur_]

# reagent index (reagent -> reactions)
idx = collections.defaultdict(list)
for r in rows:
    for part in split_top(r['reagents']):
        p = part.strip()
        if p: idx[p.lower()].append(r['name'])
with open(root / 'reagent_index.md', 'w') as f:
    f.write('# Reagent index\n\nReagent (as written in the list) -> name reactions using it.\n\n')
    for k in sorted(idx): f.write(f'- **{k}**: {", ".join(idx[k])}\n')

with open(root / 'name_reaction_reagents.md', 'w') as f:
    f.write('# Organic name reactions and their reagents (RXNO)\n\n')
    f.write(f'{len(rows)} name reactions with reagents; {len(unresolved)} in `unresolved.tsv` (no curated reagents yet). '
            'Source: `curated` = literature reagents, `ontology` = has_catalyst in rxno.obo.\n\n')
    f.write('| RXNO | Name reaction | Reagents | Catalyst / promoter | Conditions | Source |\n|---|---|---|---|---|---|\n')
    for r in rows:
        f.write('| {} | {} | {} | {} | {} | {}{} |\n'.format(
            r['id'], r['name'], r['reagents'], r['catalyst'], r['conditions'], r['source'], ''))
print(len(named), 'named;', len(rows), 'with reagents;', len(unresolved), 'unresolved')
