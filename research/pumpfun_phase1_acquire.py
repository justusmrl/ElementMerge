#!/usr/bin/env python3
"""Read-only Pump.fun Phase 1 acquisition through the public SQD Portal."""
from __future__ import annotations
import argparse, hashlib, json, time
from pathlib import Path
from typing import Any, Iterable
import requests

PORTAL = "https://portal.sqd.dev/datasets/solana-mainnet/stream"
PUMP_PROGRAM = "6EF8rrecthR5Dkzon8Nwu78hRvfCKubJ14M5uBEwF6P"
CREATE_D8 = ["0x181ec828051c0777", "0xd6904cec5f8b31b4"]

def iter_blocks(obj: Any) -> Iterable[dict[str, Any]]:
    if isinstance(obj, list):
        for item in obj: yield from iter_blocks(item)
    elif isinstance(obj, dict):
        if isinstance(obj.get("blocks"), list):
            yield from (b for b in obj["blocks"] if isinstance(b, dict))
        else: yield obj

def post_ndjson(query: dict[str, Any], output: Path, retries: int = 6) -> dict[str, Any]:
    output.parent.mkdir(parents=True, exist_ok=True)
    summary = {"query": query, "line_count": 0, "block_count": 0, "top_level_types": {},
               "top_level_keys": [], "block_key_examples": [], "instruction_key_examples": [],
               "transaction_key_examples": [], "sha256": None}
    for attempt in range(retries):
        try:
            with requests.post(PORTAL, json=query, headers={"accept":"application/x-ndjson"},
                               stream=True, timeout=(30,300)) as response:
                if response.status_code in {429,500,502,503,504}:
                    raise requests.HTTPError(f"retryable HTTP {response.status_code}: {response.text[:500]}")
                response.raise_for_status(); digest = hashlib.sha256()
                with output.open("wb") as fh:
                    for raw in response.iter_lines():
                        if not raw: continue
                        fh.write(raw+b"\n"); digest.update(raw+b"\n"); summary["line_count"] += 1
                        obj=json.loads(raw); typ=type(obj).__name__
                        summary["top_level_types"][typ]=summary["top_level_types"].get(typ,0)+1
                        if isinstance(obj,dict) and not summary["top_level_keys"]: summary["top_level_keys"]=sorted(obj.keys())
                        for block in iter_blocks(obj):
                            summary["block_count"] += 1
                            if len(summary["block_key_examples"])<5: summary["block_key_examples"].append(sorted(block.keys()))
                            for ins in block.get("instructions",[]) or []:
                                if isinstance(ins,dict) and len(summary["instruction_key_examples"])<5: summary["instruction_key_examples"].append(sorted(ins.keys()))
                            for tx in block.get("transactions",[]) or []:
                                if isinstance(tx,dict) and len(summary["transaction_key_examples"])<5: summary["transaction_key_examples"].append(sorted(tx.keys()))
                summary["sha256"]=digest.hexdigest(); return summary
        except Exception:
            if attempt+1>=retries: raise
            time.sleep(min(30,2**attempt))
    return summary

def run_probe(out_dir: Path) -> None:
    query={"type":"solana","fromBlock":434936100,"toBlock":434936300,
      "instructions":[{"programId":[PUMP_PROGRAM],"d8":CREATE_D8,"transaction":True,
                       "innerInstructions":True,"transactionBalances":True,"transactionTokenBalances":True}],
      "fields":{"block":{"number":True,"timestamp":True,"hash":True},
        "transaction":{"transactionIndex":True,"signatures":True,"feePayer":True,"fee":True,"err":True,
                       "computeUnitsConsumed":True,"hasDroppedLogMessages":True},
        "instruction":{"transactionIndex":True,"instructionAddress":True,"programId":True,"accounts":True,
                       "data":True,"d1":True,"d2":True,"d4":True,"d8":True,"error":True,
                       "computeUnitsConsumed":True,"isCommitted":True,"hasDroppedLogMessages":True},
        "balance":{"transactionIndex":True,"account":True,"pre":True,"post":True},
        "tokenBalance":{"transactionIndex":True,"account":True,"preMint":True,"postMint":True,
                        "preOwner":True,"postOwner":True,"preAmount":True,"postAmount":True,
                        "preDecimals":True,"postDecimals":True}}}
    out_dir.mkdir(parents=True,exist_ok=True)
    summary=post_ndjson(query,out_dir/"probe.ndjson")
    (out_dir/"probe_summary.json").write_text(json.dumps(summary,indent=2,sort_keys=True),encoding="utf-8")
    print(json.dumps(summary,indent=2,sort_keys=True))

def main()->int:
    p=argparse.ArgumentParser(); p.add_argument("--output-dir",type=Path,default=Path("out/phase1")); p.add_argument("--probe",action="store_true")
    a=p.parse_args();
    if not a.probe: p.error("This revision supports --probe only")
    run_probe(a.output_dir); return 0
if __name__=="__main__": raise SystemExit(main())
