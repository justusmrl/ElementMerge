#!/usr/bin/env python3
from pathlib import Path
p=Path('/tmp/acquire.py')
t=p.read_text(encoding='utf-8')
insert=r'''

# The raw Portal stream returns bounded chunks. Continue from the last emitted
# block until the requested slot range has been exhausted; otherwise a buffered
# query can return only pre-window records and silently miss the target window.
_ORIGINAL_PORTAL_ITER_BLOCKS = PortalClient.iter_blocks

def _iter_blocks_paginated(self: "PortalClient", query: Mapping[str, Any], attempts: int = 9) -> Iterator[dict[str, Any]]:
    base = dict(query)
    from_block = base.get("fromBlock")
    to_block = base.get("toBlock")
    if from_block is None or to_block is None:
        yield from _ORIGINAL_PORTAL_ITER_BLOCKS(self, base, attempts)
        return
    current = int(from_block)
    target = int(to_block)
    page = 0
    while current <= target:
        payload = dict(base)
        payload["fromBlock"] = current
        yielded = False
        max_block: int | None = None
        for block in _ORIGINAL_PORTAL_ITER_BLOCKS(self, payload, attempts):
            yielded = True
            header = block.get("header") or {}
            number = safe_number(header.get("number"))
            if number is not None:
                max_block = int(number) if max_block is None else max(max_block, int(number))
            yield block
        page += 1
        self.stats["range_pages"] += 1
        if not yielded:
            return
        if max_block is None:
            raise RuntimeError("SQD range page emitted blocks without header.number")
        if max_block >= target:
            return
        next_block = max_block + 1
        if next_block <= current:
            raise RuntimeError(f"SQD pagination made no progress: {current=} {max_block=}")
        current = next_block

PortalClient.iter_blocks = _iter_blocks_paginated
'''
marker='\n\ndef resolve_slot_for_timestamp('
if '_iter_blocks_paginated' not in t:
    if marker not in t: raise RuntimeError('resolver marker not found')
    t=t.replace(marker,insert+marker,1)
p.write_text(t,encoding='utf-8')
