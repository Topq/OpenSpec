import io, re, sys, collections

sys.stdout.reconfigure(encoding='utf-8')
path = sys.argv[1]
text = io.open(path, encoding='utf-8').read()

marks = [(int(m.group(1)), int(m.group(2)), m.start()) for m in re.finditer(r'^--- !u!(\d+) &(\d+)', text, re.M)]
marks.append((0, 0, len(text)))

go_name = {}      # go fid -> name
go_active = {}    # go fid -> active
go_comps = collections.defaultdict(list)  # go fid -> [(cls, fid)]
tr2go = {}        # tr fid -> go fid
tr_father = {}    # tr fid -> father tr fid
script_guid = {}  # go fid -> [guids]

for i in range(len(marks) - 1):
    cls, fid, start = marks[i]
    end = marks[i + 1][2]
    body = text[start:end]

    if cls == 1:
        m = re.search(r'^  m_Name: (.*)$', body, re.M)
        a = re.search(r'^  m_IsActive: (\d)', body, re.M)
        go_name[fid] = m.group(1).strip() if m else '?'
        go_active[fid] = (a.group(1) == '1') if a else True
        for cm in re.finditer(r'component: \{fileID: (\d+)\}', body):
            go_comps[fid].append(cm.group(1))
    elif cls in (4, 224):
        g = re.search(r'm_GameObject: \{fileID: (\d+)\}', body)
        f = re.search(r'm_Father: \{fileID: (\d+)\}', body)
        if g:
            tr2go[fid] = int(g.group(1))
            tr_father[fid] = int(f.group(1)) if f else 0
    elif cls == 114:
        g = re.search(r'm_GameObject: \{fileID: (\d+)\}', body)
        s = re.search(r'm_Script: \{fileID: \d+, guid: ([0-9a-f]+)', body)
        if g and s:
            script_guid.setdefault(int(g.group(1)), []).append(s.group(1))

children = collections.defaultdict(list)
for fid, father in tr_father.items():
    children[father].append(fid)

def dump(tr, depth=0):
    g = tr2go.get(tr)
    nm = go_name.get(g, '?')
    suffix = '' if go_active.get(g, True) else ' [inactive]'
    print('  ' * depth + nm + suffix)
    for ch in sorted(children.get(tr, [])):
        dump(ch, depth + 1)

roots = [f for f, fa in tr_father.items() if fa == 0]
for r in sorted(roots):
    dump(r)
