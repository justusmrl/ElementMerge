#!/usr/bin/env python3
from pathlib import Path

path = Path('/tmp/pumpfun_phase1_acquire.py')
text = path.read_text(encoding='utf-8')

resolver = r'''

def resolve_slot_for_timestamp(client: "PortalClient", target_ts: int, initial_slot: int | None = None) -> tuple[int, dict[str, Any]]:
    """Resolve a UTC timestamp to a nearby indexed Solana slot using SQD block headers."""
    center = int(initial_slot if initial_slot is not None else estimate_slot(target_ts))
    audit: dict[str, Any] = {
        "target_ts": int(target_ts), "target_iso": iso_utc(target_ts),
        "initial_slot": center, "iterations": [],
    }
    nearest_slot = center
    nearest_ts = None
    for attempt in range(5):
        radius = 120 if attempt == 0 else 320
        query = {
            "type": "solana",
            "fromBlock": max(0, center - radius),
            "toBlock": center + radius,
            "fields": {"block": {"number": True, "timestamp": True}},
        }
        candidates: list[tuple[int, int]] = []
        for block in client.iter_blocks(query):
            header = block.get("header") or {}
            slot = safe_number(header.get("number"))
            ts = safe_number(header.get("timestamp"))
            if slot is not None and ts is not None:
                candidates.append((int(slot), int(ts)))
        if not candidates:
            audit["iterations"].append({
                "attempt": attempt, "center": center, "radius": radius,
                "candidate_count": 0,
            })
            center += 2_000
            continue
        nearest_slot, nearest_ts = min(
            candidates, key=lambda x: (abs(x[1] - target_ts), abs(x[0] - center))
        )
        candidates_sorted = sorted(candidates)
        local_rates: list[float] = []
        for (s0, t0), (s1, t1) in zip(candidates_sorted, candidates_sorted[1:]):
            if t1 != t0:
                rate = (s1 - s0) / (t1 - t0)
                if 1.0 <= rate <= 5.0:
                    local_rates.append(rate)
        local_rate = float(pd.Series(local_rates).median()) if local_rates else 2.5
        error_sec = int(target_ts - nearest_ts)
        audit["iterations"].append({
            "attempt": attempt, "center": center, "radius": radius,
            "candidate_count": len(candidates), "nearest_slot": nearest_slot,
            "nearest_ts": nearest_ts, "nearest_iso": iso_utc(nearest_ts),
            "error_sec": error_sec, "local_slots_per_second": local_rate,
        })
        if abs(error_sec) <= 1:
            break
        center = int(round(nearest_slot + error_sec * local_rate))
    if nearest_ts is None:
        raise RuntimeError(f"SQD could not resolve timestamp {target_ts}")
    audit["resolved_slot"] = int(nearest_slot)
    audit["resolved_ts"] = int(nearest_ts)
    audit["resolved_iso"] = iso_utc(nearest_ts)
    audit["absolute_error_sec"] = abs(int(nearest_ts) - int(target_ts))
    return int(nearest_slot), audit
'''

marker = '\n\n@dataclasses.dataclass\nclass Cursor:'
if 'def resolve_slot_for_timestamp(' not in text:
    if marker not in text:
        raise RuntimeError('Cursor insertion marker not found')
    text = text.replace(marker, resolver + marker)

old = '''    windows = [w for day in shard_days for w in sample_windows_for_day(day)]
    (out / "sample_windows.json").write_text(json.dumps(windows, indent=2), encoding="utf-8")

    launch_rows: list[dict[str, Any]] = []
'''
new = '''    windows = [w for day in shard_days for w in sample_windows_for_day(day)]

    # Resolve daily start/end slots directly from SQD block headers. Long-range
    # slot-rate interpolation is only an initial guess and can drift materially.
    anchor_audit: list[dict[str, Any]] = []
    by_date = {day.isoformat(): day for day in shard_days}
    for day_text, day in by_date.items():
        day_ts = utc_timestamp(day)
        next_ts = day_ts + 86_400
        start_slot, start_audit = resolve_slot_for_timestamp(client, day_ts, estimate_slot(day_ts))
        end_slot, end_audit = resolve_slot_for_timestamp(client, next_ts, estimate_slot(next_ts))
        anchor_audit.extend([start_audit, end_audit])
        realised_rate = (end_slot - start_slot) / 86_400.0
        for window in windows:
            if window["date"] != day_text:
                continue
            window["daily_anchor_start_slot"] = start_slot
            window["daily_anchor_end_slot"] = end_slot
            window["daily_realised_slots_per_second"] = realised_rate
            window["estimated_from_slot"] = int(round(
                start_slot + (window["start_ts"] - day_ts) * realised_rate
            )) - 1_000
            window["estimated_to_slot"] = int(round(
                start_slot + (window["end_ts"] - day_ts) * realised_rate
            )) + 1_000
    (out / "timestamp_slot_anchor_audit.json").write_text(
        json.dumps(anchor_audit, indent=2), encoding="utf-8"
    )
    (out / "sample_windows.json").write_text(json.dumps(windows, indent=2), encoding="utf-8")

    launch_rows: list[dict[str, Any]] = []
'''
if old in text:
    text = text.replace(old, new)
elif 'timestamp_slot_anchor_audit.json' not in text:
    raise RuntimeError('acquisition window block not found')

path.write_text(text, encoding='utf-8')
