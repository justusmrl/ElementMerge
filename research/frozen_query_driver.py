#!/usr/bin/env python3
from __future__ import annotations
import importlib.util, json, sys
from collections import Counter
from pathlib import Path

spec=importlib.util.spec_from_file_location('frozen_acquire','/tmp/acquire.py')
mod=importlib.util.module_from_spec(spec); sys.modules['frozen_acquire']=mod; spec.loader.exec_module(mod)
out=Path('out/frozen-query-driver'); out.mkdir(parents=True,exist_ok=True)
pump, amm=mod.load_registries(out)
create_d8=[s['d8'] for s in pump.instructions.values() if s.get('name') in {'create','create_v2'}]
client=mod.PortalClient()
query={
 'type':'solana','fromBlock':434622702,'toBlock':434624855,
 'instructions':[mod.related_flags({'programId':[mod.PUMP_PROGRAM],'d8':create_d8})],
 'fields':mod.query_fields(),
}
summary={'pump_program':mod.PUMP_PROGRAM,'create_d8':create_d8,'query':query,'blocks':0,'instructions':0,'matching_create':0,'accepted_by_time':0,'programs':Counter(),'d8':Counter(),'timestamps':[],'examples':[]}
for block in client.iter_blocks(query):
 summary['blocks']+=1; h=block.get('header') or {}; ts=mod.safe_number(h.get('timestamp'))
 if ts is not None: summary['timestamps'].append(int(ts))
 for ins in block.get('instructions',[]) or []:
  summary['instructions']+=1; summary['programs'][str(ins.get('programId'))]+=1; summary['d8'][str(ins.get('d8'))]+=1
  if ins.get('programId')==mod.PUMP_PROGRAM and ins.get('d8') in create_d8:
   summary['matching_create']+=1
   if ts is not None and 1784770980 <= ts < 1784771880: summary['accepted_by_time']+=1
   if len(summary['examples'])<3: summary['examples'].append(ins)
summary['timestamp_min']=min(summary['timestamps']) if summary['timestamps'] else None
summary['timestamp_max']=max(summary['timestamps']) if summary['timestamps'] else None
summary['programs']=dict(summary['programs'].most_common(25)); summary['d8']=dict(summary['d8'].most_common(50)); summary['client_stats']=dict(client.stats); summary.pop('timestamps',None)
(out/'summary.json').write_text(json.dumps(summary,indent=2,sort_keys=True),encoding='utf-8')
print(json.dumps({k:v for k,v in summary.items() if k not in {'query','examples','programs','d8'}},sort_keys=True))
