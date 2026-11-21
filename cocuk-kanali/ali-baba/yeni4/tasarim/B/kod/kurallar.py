#!/usr/bin/env python3
"""The progression rules of designer B (used by 03_tara.py and 04_olcum.py).

  G1  bar 6 ends on V, V7 or I                                                     (given by the task)
  G2  the chord right before a bar that is NOT sung (bars 1, 3, 7: loud answer / animal call, all starting on I)
      is I, IV, V or V7
  G3  the dominant goes home: V / V7 is followed by V, V7 or I (never by IV, ii, iii, vi); V7 does not drop its seventh
      G3t (rule set "turnaround"): as G3, but the plain V may also step down to IV when that IV goes straight to I
  G4  every fully sung bar has at least two beats of primary chords (I, IV, V, V7)
"""
from ortak import PRIMARY

DOM = ("V", "V7")


def changes(bar, seq, before="I"):
    """chord changes INSIDE the bar (bar 5: counted from the I of its beats 0-1)."""
    full = (["I", "I"] + list(seq)) if bar == 5 else list(seq)
    return sum(1 for a, b in zip(full[:-1], full[1:]) if a != b)


def odd_changes(bar, seq):
    full = (["I", "I"] + list(seq)) if bar == 5 else list(seq)
    return sum(1 for i in (1, 3) if full[i] != full[i - 1])


def chain_ok(chain, turnaround=False):
    """G3 (or G3t) for a chain of successive chords"""
    for i in range(len(chain) - 1):
        a, b = chain[i], chain[i + 1]
        if a == "V7" and b == "V":
            return False
        if a in DOM and b not in ("V", "V7", "I"):
            if turnaround and a == "V" and b == "IV":
                # V - IV is allowed only when the IV then goes straight to I
                j = i + 1
                while j < len(chain) and chain[j] == "IV":
                    j += 1
                if j < len(chain) and chain[j] == "I":
                    continue
            return False
    return True


def rules(bar, seq, before="I", turnaround=False):
    """-> dict of rule name -> bool for one bar. 'before' = the chord of the beat before the bar (bar 6: bar 5 beat 3).
    The chord after bars 0, 2, 6 is always I; after bar 5 comes bar 6 (checked jointly, see junction)."""
    full = (["I", "I"] + list(seq)) if bar == 5 else list(seq)
    out = {}
    out["G1"] = (bar != 6) or (full[-1] in ("V", "V7", "I"))
    out["G2"] = (bar == 5) or (full[-1] in ("I", "IV", "V", "V7"))
    nxt = [] if bar == 5 else ["I"]
    out["G3t" if turnaround else "G3"] = chain_ok([before] + full + nxt, turnaround)
    out["G4"] = (bar == 5) or (sum(1 for c in full if c in PRIMARY) >= 2)
    return out
