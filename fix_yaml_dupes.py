import os
from pathlib import Path

def fix_yaml_dupes(file_path):
    path = Path(file_path)
    if not path.exists():
        print(f"File not found: {file_path}")
        return
    
    content = path.read_text()
    lines = content.splitlines()
    new_lines = []
    seen_keys = set()
    
    # Simple stack-based tracker for indentation levels to handle nested keys
    # But for these specific files, the dupes are mostly top-level or at known levels
    
    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()
        
        # Check for top-level keys like deferral: or time:
        if stripped.endswith(":") and not stripped.startswith("-"):
            indent = len(line) - len(line.lstrip())
            key_name = stripped[:-1]
            full_key = f"{indent}_{key_name}"
            
            if full_key in seen_keys:
                # Potential duplicate. Check if it is one of the ones we know about.
                if key_name in ["deferral", "time", "timezone", "location", "location_class"]:
                    # Skip this block until the next key at same or lower indentation
                    i += 1
                    while i < len(lines):
                        next_line = lines[i]
                        if not next_line.strip():
                            i += 1
                            continue
                        next_indent = len(next_line) - len(next_line.lstrip())
                        if next_indent <= indent:
                            break
                        i += 1
                    continue # Skip adding the duplicate key line itself
            else:
                seen_keys.add(full_key)
        
        new_lines.append(line)
        i += 1
    
    path.write_text("\n".join(new_lines) + "\n")
    print(f"Fixed dupes in {file_path}")

files_to_fix = [
    "pipeline/active/coinbase-senior-machine-learning-platform-engineer-platform.yaml",
    "pipeline/active/stripe-staff-software-engineer-stream-compute.yaml",
    "pipeline/active/toast-senior-backend-engineer-enterprise-financial-systems.yaml",
    "pipeline/closed/artadia-nyc.yaml",
    "pipeline/closed/prix-ars-digital-humanity.yaml",
    "pipeline/closed/watermill-center.yaml",
    "pipeline/submitted/snorkel-ai-staff-applied-ai-engineer-pre-sales.yaml",
    "pipeline/closed/cursor-software-engineer-client-infrastructure.yaml",
    "pipeline/closed/notion-software-engineer-developer-experience.yaml",
    "pipeline/active/zkm-rauschenberg.yaml"
]

for f in files_to_fix:
    fix_yaml_dupes(f)
