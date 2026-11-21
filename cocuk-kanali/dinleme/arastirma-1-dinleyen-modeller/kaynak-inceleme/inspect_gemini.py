import json, sys, re
d = json.load(open(sys.argv[1]))
print(d.get("title"), d.get("version"), d.get("revision"), d.get("rootUrl"), d.get("servicePath"))
def walk(res, prefix=""):
    for name, r in res.items():
        for mname, m in r.get("methods", {}).items():
            mu = m.get("mediaUpload")
            print(f"{prefix}{name}.{mname}: {m.get('httpMethod')} {m.get('flatPath') or m.get('path')}" + (f" | UPLOAD {json.dumps(mu)}" if mu else ""))
        if "resources" in r:
            walk(r["resources"], prefix + name + ".")
walk(d["resources"])
sch = d["schemas"]
for n in ("Blob", "FileData", "File", "Part", "GenerationConfig", "VideoMetadata"):
    if n in sch:
        print("##", n, "|", (sch[n].get("description") or "")[:300])
        for k, v in sch[n].get("properties", {}).items():
            print("  -", k, ":", v.get("type") or v.get("$ref"), v.get("enum"), "|", (v.get("description") or "")[:260].replace("\n", " "))
txt = json.dumps(d)
print("model ids mentioned:", sorted(set(re.findall(r"gemini-[0-9][\w.\-]*", txt))))
print("auth params:", {k: v.get("location") for k, v in d.get("parameters", {}).items()})
