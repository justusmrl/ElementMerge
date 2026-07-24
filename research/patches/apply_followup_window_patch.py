#!/usr/bin/env python3
from pathlib import Path
p=Path('/tmp/acquire.py')
t=p.read_text(encoding='utf-8')
old='''            from_slot = estimate_slot(window["start_ts"]) - 2_000\n            to_slot = estimate_slot(window["end_ts"] + FOLLOWUP_SECONDS) + 2_000\n'''
new='''            day_ts = utc_timestamp(window["date"])\n            from_slot = int(window["estimated_from_slot"])\n            # The next-day anchor plus the same UTC offset gives a point-local\n            # estimate for the 24h follow-up end; the buffer absorbs intraday drift.\n            to_slot = int(round(\n                window["daily_anchor_end_slot"]\n                + (window["end_ts"] - day_ts) * window["daily_realised_slots_per_second"]\n            )) + 3_000\n'''
if old not in t: raise RuntimeError('Pump follow-up slot marker not found')
t=t.replace(old,new,1)
old='''                    if mint in batch_set:\n                        selected_by_tx[int(ins["transactionIndex"])].add(mint)\n                        try:\n'''
new='''                    if mint in batch_set:\n                        launch_ts = int(launch_map[mint]["timestamp"])\n                        if not (launch_ts <= int(timestamp) <= launch_ts + FOLLOWUP_SECONDS):\n                            continue\n                        selected_by_tx[int(ins["transactionIndex"])].add(mint)\n                        try:\n'''
if old not in t: raise RuntimeError('Pump per-token follow-up marker not found')
t=t.replace(old,new,1)
old='''        min_launch_ts = int(launches[launches["mint"].isin(batch)]["timestamp"].min())\n        max_launch_ts = int(launches[launches["mint"].isin(batch)]["timestamp"].max())\n        query = {"type": "solana", "fromBlock": estimate_slot(min_launch_ts) - 2_000,\n                 "toBlock": estimate_slot(max_launch_ts + FOLLOWUP_SECONDS) + 2_000,\n'''
new='''        batch_launches = launches[launches["mint"].isin(batch)]\n        min_launch_slot = int(pd.to_numeric(batch_launches["slot"], errors="raise").min())\n        max_launch_slot = int(pd.to_numeric(batch_launches["slot"], errors="raise").max())\n        query = {"type": "solana", "fromBlock": min_launch_slot - 2_000,\n                 "toBlock": max_launch_slot + int(FOLLOWUP_SECONDS * 3.0) + 5_000,\n'''
if old not in t: raise RuntimeError('AMM follow-up slot marker not found')
t=t.replace(old,new,1)
old='''                if mint in batch_set: selected_by_tx[int(ins["transactionIndex"])].add(mint)\n'''
new='''                if mint in batch_set:\n                    launch_ts = int(launch_map[mint]["timestamp"])\n                    if launch_ts <= int(timestamp) <= launch_ts + FOLLOWUP_SECONDS:\n                        selected_by_tx[int(ins["transactionIndex"])].add(mint)\n'''
if old not in t: raise RuntimeError('AMM per-token follow-up marker not found')
t=t.replace(old,new,1)
p.write_text(t,encoding='utf-8')
