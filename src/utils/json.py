import json

def is_json(data: str) -> bool:
    try:
        json.loads(data)
        return True
    except (ValueError, TypeError):
        return False

def is_not_json(data: str) -> bool:
    return not is_json(data)

def compact(data: str, escape: bool = False) -> str | None:
    if is_not_json(data):
        return data

    compacted = json.dumps(json.loads(data), separators=(',', ':'))
    return compacted if not escape else compacted.replace('"', '\\"')
