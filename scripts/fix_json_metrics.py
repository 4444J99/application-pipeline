import json
import os
import re
from pathlib import Path

PROFILES_DIR = Path("targets/profiles")
OLD_VAL = "42"
NEW_VAL = "47"

def fix_json_metrics():
    fixed_count = 0
    file_count = 0
    
    if not PROFILES_DIR.exists():
        print(f"Directory {PROFILES_DIR} not found.")
        return

    # Pattern to match '42' as a whole word in strings
    # We use regex to be safe about not replacing parts of other numbers
    pattern = re.compile(r'\b' + OLD_VAL + r'\b')

    for filepath in PROFILES_DIR.glob("*.json"):
        file_count += 1
        with open(filepath, 'r') as f:
            try:
                data = json.load(f)
            except json.JSONDecodeError:
                print(f"Skipping {filepath}: Invalid JSON")
                continue

        modified = False

        def _transform(obj):
            nonlocal modified
            if isinstance(obj, str):
                new_str = pattern.sub(NEW_VAL, obj)
                if new_str != obj:
                    modified = True
                    return new_str
                return obj
            elif isinstance(obj, dict):
                return {k: _transform(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [_transform(i) for i in obj]
            return obj

        new_data = _transform(data)

        if modified:
            with open(filepath, 'w') as f:
                json.dump(new_data, f, indent=2)
            fixed_count += 1
            print(f"  Fixed: {filepath.name}")

    print(f"\nFinished: {fixed_count} files modified out of {file_count} checked.")

if __name__ == "__main__":
    fix_json_metrics()
