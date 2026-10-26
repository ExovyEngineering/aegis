from pathlib import Path
import os
ROOT = Path(__file__).resolve().parents[1]
# Minimal dotenv reader: no shell evaluation, existing environment takes precedence.
env_file=ROOT/'.env'
if env_file.exists():
    for line in env_file.read_text(encoding='utf-8-sig').splitlines():
        line=line.strip()
        if line and not line.startswith('#') and '=' in line:
            key,value=line.split('=',1)
            if key.strip().isidentifier(): os.environ.setdefault(key.strip(),value.strip().strip('\"\''))
def data_dir():
    return Path(os.environ.get('AEGIS_DATA_DIR') or (ROOT / 'data/raw' if (ROOT / 'data/raw').exists() else ROOT))
def write_json(path, obj):
    import json
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, default=str), encoding='utf-8')
