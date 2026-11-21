import json, sys, re
d = json.load(open(sys.argv[1]))
paths = d.get("paths", {})
comp = d["components"]["schemas"]
def resolve(s):
    while isinstance(s, dict) and "$ref" in s:
        s = comp[s["$ref"].split("/")[-1]]
    return s
def show(name, indent=0, seen=None):
    seen = seen or set()
    if name in seen: return
    seen.add(name)
    s = comp[name]
    print(" " * indent + "## " + name, "|", (s.get("description") or "")[:300].replace("\n", " "))
    for k, v in s.get("properties", {}).items():
        refs = re.findall(r'#/components/schemas/(\w+)', json.dumps(v))
        vv = resolve(v)
        print(" " * indent + f"- {k}: type={vv.get('type')} enum={vv.get('enum')} | {(v.get('description') or vv.get('description') or '')[:350]}".replace("\n", " "))
        for r in refs:
            if r in comp and comp[r].get("properties"):
                show(r, indent + 4, seen)
for n in ("SpeechToTextChunkResponseModel", "ForcedAlignmentResponseModel"):
    show(n)
# top-level path groups
groups = {}
for p in paths:
    parts = p.strip("/").split("/")
    g = "/".join(parts[:2])
    groups[g] = groups.get(g, 0) + 1
print("\nGROUPS:", ", ".join(f"{g}({n})" for g, n in sorted(groups.items())))
# search for audio-understanding style endpoints
for p in sorted(paths):
    for m, op in paths[p].items():
        if not isinstance(op, dict): continue
        text = (op.get("summary") or "") + " " + (op.get("description") or "")
        if re.search(r"classif|detect|similar|understand|analy[sz]e|quality|score|pronunc|caption|describe", text, re.I) and not p.startswith("/v1/convai"):
            print(m.upper(), p, "|", (op.get("summary") or ""), "|", (op.get("description") or "")[:200].replace("\n", " "))
# model id mentions
txt = json.dumps(d)
print("\nscribe ids:", sorted(set(re.findall(r"scribe_v\d[\w]*", txt))))
