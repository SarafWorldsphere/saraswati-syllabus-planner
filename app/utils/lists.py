"""Every list response is wrapped. A bare array cannot grow a field later."""


def item_list(rows: list) -> dict:
    return {"items": rows, "total": len(rows)}
