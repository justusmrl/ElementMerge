#!/usr/bin/env python3
from pathlib import Path
p=Path('/tmp/acquire.py')
t=p.read_text(encoding='utf-8')
old='''    if not create_d8:\n        raise RuntimeError("Official Pump IDL has no create/create_v2 discriminator")\n\n    for wi, window in enumerate(windows, 1):\n'''
new='''    if not create_d8:\n        raise RuntimeError("Official Pump IDL has no create/create_v2 discriminator")\n    print("DEBUG_CONSTANTS", json.dumps({"pump_program": PUMP_PROGRAM, "create_d8": create_d8}), flush=True)\n\n    for wi, window in enumerate(windows, 1):\n'''
if old not in t: raise RuntimeError('constants marker not found')
t=t.replace(old,new,1)
old='''        matching_timestamps: list[int] = []\n        rows_before = len(launch_rows)\n        for block in client.iter_blocks(query):\n'''
new='''        matching_timestamps: list[int] = []\n        rows_before = len(launch_rows)\n        debug_block_count = 0\n        debug_instruction_count = 0\n        debug_program_match = 0\n        debug_d8_match = 0\n        debug_programs = defaultdict(int)\n        debug_d8s = defaultdict(int)\n        if wi == 1:\n            (out / "debug_first_launch_query.json").write_text(json.dumps(query, indent=2), encoding="utf-8")\n        for block in client.iter_blocks(query):\n            debug_block_count += 1\n'''
if old not in t: raise RuntimeError('loop marker not found')
t=t.replace(old,new,1)
old='''            instructions = block.get("instructions", []) or []\n            grouped: dict[int, list[dict[str, Any]]] = defaultdict(list)\n            for ins in instructions:\n'''
new='''            instructions = block.get("instructions", []) or []\n            debug_instruction_count += len(instructions)\n            for debug_ins in instructions:\n                debug_programs[str(debug_ins.get("programId"))] += 1\n                debug_d8s[str(debug_ins.get("d8"))] += 1\n                if debug_ins.get("programId") == PUMP_PROGRAM:\n                    debug_program_match += 1\n                if debug_ins.get("d8") in create_d8:\n                    debug_d8_match += 1\n            grouped: dict[int, list[dict[str, Any]]] = defaultdict(list)\n            for ins in instructions:\n'''
if old not in t: raise RuntimeError('instructions marker not found')
t=t.replace(old,new,1)
old='''        coverage_rows.append(\n            {\n'''
new='''        if wi == 1:\n            debug_payload = {\n                "window": window, "block_count": debug_block_count,\n                "instruction_count": debug_instruction_count,\n                "program_match": debug_program_match, "d8_match": debug_d8_match,\n                "accepted_rows": len(launch_rows) - rows_before,\n                "programs": dict(sorted(debug_programs.items(), key=lambda kv: -kv[1])[:25]),\n                "d8s": dict(sorted(debug_d8s.items(), key=lambda kv: -kv[1])[:50]),\n                "client_stats": dict(client.stats),\n            }\n            print("DEBUG_FIRST_WINDOW", json.dumps(debug_payload, sort_keys=True), flush=True)\n            (out / "debug_first_window.json").write_text(json.dumps(debug_payload, indent=2, sort_keys=True), encoding="utf-8")\n        coverage_rows.append(\n            {\n'''
if old not in t: raise RuntimeError('coverage marker not found')
t=t.replace(old,new,1)
p.write_text(t,encoding='utf-8')
