#!/usr/bin/env python3
"""02_calistir.py bitene kadar bekler, sonra ikinci asamayi (gercek kanallar) calistirir: ayni anda iki agir is kosmasin diye."""
import subprocess, sys, time, os
while subprocess.run(["pgrep", "-f", "02_calistir.py"], capture_output=True).stdout.strip():
    time.sleep(15)
subprocess.run([sys.executable, os.path.join(os.path.dirname(os.path.abspath(__file__)), "08_gercek_kanallar.py"), sys.argv[1]])
print("IKINCI ASAMA BITTI", flush=True)
