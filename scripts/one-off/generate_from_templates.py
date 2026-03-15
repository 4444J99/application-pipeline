#!/usr/bin/env python3
import pathlib
import re
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

REPO_ROOT = Path(__file__).resolve().parent.parent
TEMPLATES_DIR = REPO_ROOT / "templates"
METRICS_FILE = REPO_ROOT / "config" / "metrics.yaml"

def load_metrics():
    with open(METRICS_FILE) as f:
        return yaml.safe_load(f)

def render_template(content, metrics):
    # Simple recursive placeholder replacement: {{ key.subkey }}
    def _get_val(keys):
        val = metrics
        for k in keys.split('.'):
            val = val.get(k, f"MISSING_{k}")
        return str(val)

    # Match {{ system.total_repos }} etc.
    pattern = re.compile(r'\{\{\s*([\w\.]+)\s*\}\}')
    return pattern.sub(lambda m: _get_val(m.group(1)), content)

def generate_all():
    metrics = load_metrics()
    template_files = list(TEMPLATES_DIR.rglob("*.j2"))
    
    print(f"Generating from {len(template_files)} templates...")
    
    for template_path in template_files:
        # Determine output path: templates/blocks/cathedral.md.j2 -> blocks/cathedral.md
        # relative_to(TEMPLATES_DIR) -> blocks/cathedral.md.j2
        rel_path = template_path.relative_to(TEMPLATES_DIR)
        output_path = REPO_ROOT / str(rel_path).replace(".j2", "")
        
        # Ensure parent directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(template_path) as f:
            template_content = f.read()
            
        rendered = render_template(template_content, metrics)
        
        with open(output_path, 'w') as f:
            f.write(rendered)
            
        print(f"  Generated: {output_path.relative_to(REPO_ROOT)}")

if __name__ == "__main__":
    generate_all()
