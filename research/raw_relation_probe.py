#!/usr/bin/env python3
from __future__ import annotations
import hashlib, json
from collections import Counter
from pathlib import Path
import requests

PORTAL='https://portal.sqd.dev/datasets/solana-mainnet/stream'
PUMP='6EF8rrecthR5Dkzon8Nwu78hRvfCKubJ14M5uBEwF6P'
CREATE=['0x181ec828051c0777','0xd6904cec5f8b31b4']
OUT=Path('out/raw-relation-probe'); OUT.mkdir(parents=True,exist_ok=True)
FIELDS={
 'block':{'number':True,'timestamp':True,'hash':True},
 'transaction':{'transactionIndex':True,'signatures':True,'feePayer':True,'fee':True,'err':True},
 'instruction':{'transactionIndex':True,'instructionAddress':True,'programId':True,'accounts':True,'data':True,'d8':True,'error':True},
 'balance':{'transactionIndex':True,'account':True,'pre':True,'post':True},
 'tokenBalance':{'transactionIndex':True,'account':True,'preMint':True,'postMint':True,'preOwner':True,'postOwner':True,'preAmount':True,'postAmount':True,'preDecimals':True,'postDecimals':True},
}

def blocks(obj):
    if isinstance(obj,list):
        for x in obj:
            if isinstance(x,dict): yield x
    elif isinstance(obj,dict) and isinstance(obj.get('blocks'),list):
        yield from (x for x in obj['blocks'] if isinstance(x,dict))
    elif isinstance(obj,dict): yield obj

def run(name:str, tx_instructions:bool):
    flt={'programId':[PUMP],'d8':CREATE,'transaction':True,'innerInstructions':True,'transactionBalances':True,'transactionTokenBalances':True}
    if tx_instructions: flt['transactionInstructions']=True
    query={'type':'solana','fromBlock':434622702,'toBlock':434624855,'instructions':[flt],'fields':FIELDS}
    raw_path=OUT/f'{name}.ndjson'; dig=hashlib.sha256(); summary={'name':name,'query':query,'lines':0,'blocks':0,'instructions':0,'matching_create':0,'d8':Counter(),'programs':Counter(),'top_keys':Counter(),'block_keys':Counter(),'timestamp_min':None,'timestamp_max':None,'examples':[]}
    with requests.post(PORTAL,json=query,headers={'accept':'application/x-ndjson','content-type':'application/json'},stream=True,timeout=(30,600)) as r:
        summary['http_status']=r.status_code
        if r.status_code>=400: summary['error_body']=r.text[:10000]
        r.raise_for_status()
        with raw_path.open('wb') as fh:
            for raw in r.iter_lines():
                if not raw: continue
                fh.write(raw+b'\n'); dig.update(raw+b'\n'); summary['lines']+=1
                obj=json.loads(raw)
                if isinstance(obj,dict): summary['top_keys'].update(obj.keys())
                for b in blocks(obj):
                    summary['blocks']+=1; summary['block_keys'].update(b.keys())
                    h=b.get('header') or {}; ts=h.get('timestamp')
                    if ts is not None:
                        summary['timestamp_min']=ts if summary['timestamp_min'] is None else min(summary['timestamp_min'],ts)
                        summary['timestamp_max']=ts if summary['timestamp_max'] is None else max(summary['timestamp_max'],ts)
                    for ins in b.get('instructions',[]) or []:
                        summary['instructions']+=1; summary['programs'][str(ins.get('programId'))]+=1; summary['d8'][str(ins.get('d8'))]+=1
                        if ins.get('programId')==PUMP and ins.get('d8') in CREATE:
                            summary['matching_create']+=1
                            if len(summary['examples'])<5: summary['examples'].append(ins)
    summary['sha256']=dig.hexdigest(); summary['d8']=dict(summary['d8'].most_common()); summary['programs']=dict(summary['programs'].most_common()); summary['top_keys']=dict(summary['top_keys']); summary['block_keys']=dict(summary['block_keys'])
    (OUT/f'{name}.json').write_text(json.dumps(summary,indent=2,sort_keys=True),encoding='utf-8')
    print(json.dumps({k:v for k,v in summary.items() if k not in {'query','examples','d8','programs'}},sort_keys=True))

run('without_transaction_instructions',False)
run('with_transaction_instructions',True)
