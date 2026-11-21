import json, sys
d = json.load(open(sys.argv[1]))
paths = d.get("paths", {})
print("n paths", len(paths))
for p in sorted(paths):
    if any(k in p for k in ("speech-to-text", "forced-alignment", "audio-isolation", "audio-native", "music", "sound")):
        print(p, list(paths[p].keys()))
def resolve(ref):
    node = d
    for part in ref.lstrip("#/").split("/"):
        node = node[part]
    return node
def show_schema(s, indent=0, depth=0):
    if "$ref" in s:
        s = resolve(s["$ref"])
    props = s.get("properties", {})
    for k, v in props.items():
        vv = v
        if "$ref" in vv:
            vv = resolve(vv["$ref"])
        desc = (vv.get("description") or "").replace("\n", " ")[:600]
        print(" " * indent + f"- {k}: type={vv.get('type')} enum={vv.get('enum')} default={vv.get('default')} anyOf={[a.get('type') or a.get('$ref') for a in vv.get('anyOf', [])] if 'anyOf' in vv else None}")
        if desc:
            print(" " * indent + "    " + desc)
for p in ("/v1/speech-to-text", "/v1/forced-alignment"):
    if p in paths:
        post = paths[p].get("post", {})
        print("=====", p, post.get("summary"))
        print((post.get("description") or "")[:1500])
        for prm in post.get("parameters", []):
            print("param", prm.get("name"), prm.get("in"), (prm.get("description") or "")[:300])
        rb = post.get("requestBody", {}).get("content", {})
        for ct, c in rb.items():
            print("content-type", ct)
            show_schema(c.get("schema", {}), 2)
        for code, r in post.get("responses", {}).items():
            print("response", code, json.dumps(r)[:400])
