from pathlib import Path
import os
import tempfile
import time
from threading import RLock

_json_io_lock=RLock()
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
def read_json(path):
    import json
    with _json_io_lock:
        return json.loads(Path(path).read_text(encoding='utf-8'))


def write_json(path, obj):
    import json
    path=Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    body=json.dumps(obj, indent=2, default=str)
    # Polling readers see either the prior complete response or the new one.
    with _json_io_lock:
        temporary=None
        try:
            with tempfile.NamedTemporaryFile(mode='w',encoding='utf-8',dir=path.parent,
                                             prefix='.'+path.name+'.',suffix='.tmp',delete=False) as stream:
                temporary=Path(stream.name)
                stream.write(body)
            for attempt in range(8):
                try:
                    os.replace(temporary,path)
                    break
                except PermissionError:
                    if attempt==7:raise
                    time.sleep(.005*(attempt+1))
        finally:
            if temporary is not None and temporary.exists():temporary.unlink()
