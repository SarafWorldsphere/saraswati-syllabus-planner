"""Split a topic across calendar blocks when it does not fit in one.

Capacity is working_days times the subject's periods_per_week, stored on the
segment. It is not divided by a guessed school week. A subject with no
weekly figure is placed entirely in the first block, because there is no
published capacity to overflow.
"""


def block_capacity(working_days: int | None, periods_per_week: int | None) -> int | None:
    if not working_days or not periods_per_week:
        return None
    return working_days * periods_per_week


def split_topic(periods_estimated: int | None, blocks: list, periods_per_week: int | None) -> list[dict]:
    """blocks are mappings with block_id, block_seq, working_days, already the year's order."""
    ordered = sorted(blocks, key=lambda block: block["block_seq"])
    if not ordered:
        return []

    if not periods_estimated:
        first = ordered[0]
        return [
            {
                "block_id": first["block_id"],
                "periods_in_block": None,
                "segment_seq": 1,
                "period_capacity": block_capacity(first.get("working_days"), periods_per_week),
                "placement": "planned",
            }
        ]

    remaining = periods_estimated
    placed: list[dict] = []
    for block in ordered:
        if remaining <= 0:
            break
        capacity = block_capacity(block.get("working_days"), periods_per_week)
        # No published weekly load: keep the whole topic in this first window.
        if capacity is None:
            placed.append(
                {
                    "block_id": block["block_id"],
                    "periods_in_block": remaining,
                    "segment_seq": 1,
                    "period_capacity": None,
                    "placement": "planned",
                }
            )
            return placed
        take = min(remaining, capacity)
        placed.append(
            {
                "block_id": block["block_id"],
                "periods_in_block": take,
                "segment_seq": len(placed) + 1,
                "period_capacity": capacity,
                "placement": "planned" if not placed else "continues",
            }
        )
        remaining -= take
    # More periods than the year has room for still belong to the last window,
    # so the topic is not dropped.
    if remaining > 0 and placed:
        placed[-1]["periods_in_block"] += remaining
    return placed
