from typing import Dict, Any


def dict_diff(old: Dict[str, Any], new: Dict[str, Any]) -> Dict[str, Any]:
    diff = {}
    keys = set(old.keys()) | set(new.keys())
    for key in sorted(keys):
        old_val = old.get(key)
        new_val = new.get(key)
        if old_val != new_val:
            diff[key] = {"old": old_val, "new": new_val}
    return diff
