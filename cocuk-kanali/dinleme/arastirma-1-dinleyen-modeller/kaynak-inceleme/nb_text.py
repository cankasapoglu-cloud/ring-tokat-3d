import json, sys
nb = json.load(open(sys.argv[1]))
for c in nb["cells"]:
    src = "".join(c["source"])
    print(f"--- [{c['cell_type']}]")
    print(src[:1500])
