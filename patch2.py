"""Correctness fixes: duplicate PLACE tasks, final-day shed run."""
b = open("agent_brain.py").read()
orig = b

# 1. one PLACE task per empty structure, not one per matching animal species
b = b.replace('''        idle_struct = 0
        for (x, y, kind) in scan["empty_struct"]:
            placed = False
            for aname, ad in ANIMALS.items():
                if ad["structure"] == kind and (held.get(aname, 0) or shed.get(aname, 0)):
                    tasks.append((220.0, x, y, "PLACE_" + aname, None))
                    placed = True
            if not placed:
                idle_struct += 1''', '''        idle_struct = 0
        for (x, y, kind) in scan["empty_struct"]:
            best = None
            for aname, ad in ANIMALS.items():
                if ad["structure"] != kind:
                    continue
                if not (held.get(aname, 0) or shed.get(aname, 0)):
                    continue
                if best is None or ad["cost"] > ANIMALS[best]["cost"]:
                    best = aname
            if best is None:
                idle_struct += 1
            else:
                tasks.append((220.0, x, y, "PLACE_" + best, None))''')

# 2. on the final day nothing auto-drops, so carried goods must reach the shed in time
b = b.replace('''    "hold_bonus": 1.0,''', '''    "hold_bonus": 1.0,
    "final_run_slack": 3,''')
b = b.replace('''        out = []
        for ui, upos in enumerate(units):
            inv = invs[ui] if ui < len(invs) else {}
            carry = sum(inv.values())
            ti = assigned[ui]
            if ti is not None:''', '''        out = []
        for ui, upos in enumerate(units):
            inv = invs[ui] if ui < len(invs) else {}
            carry = sum(inv.values())
            ti = assigned[ui]
            if self._final_day and carry > 0:
                dsh = min(manhattan(upos, sp) for sp in shed_set)
                if turns_left <= dsh + P["final_run_slack"]:
                    ti = None
            if ti is not None:''')

# 3. skip the fertilise scan entirely when fertilising is disabled
b = b.replace('''        fert_targets = 0
        for (x, y, t) in scan["plants"]:
            crop = t["crop"]
            cd = CROPS[crop]
            if cd["ongoing"]:
                continue''', '''        fert_targets = 0
        for (x, y, t) in (scan["plants"] if P["fert_min_gain"] < 1e6 else ()):
            crop = t["crop"]
            cd = CROPS[crop]
            if cd["ongoing"]:
                continue''')

assert b != orig, "no changes applied"
open("agent_brain.py", "w").write(b)
print("patch2 applied")

# 4. separate flag for fertiliser fetch trips, so FERTILIZE can be tested without them
b = open("agent_brain.py").read()
if '"fert_fetch"' not in b:
    b = b.replace('''    "final_run_slack": 3,''', '''    "final_run_slack": 3,
    "fert_fetch": 1,''')
    b = b.replace('''        if fert_targets and shed.get("FERTILIZER", 0) > 0 and carried_fert < fert_targets:''',
                  '''        if (P["fert_fetch"] and fert_targets and shed.get("FERTILIZER", 0) > 0
                and carried_fert < fert_targets):''')
    open("agent_brain.py", "w").write(b)
    print("patch2 step 4 applied")
