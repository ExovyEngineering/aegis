"""Verify supplied originals against the existing audit, with bounded memory."""
import sys,json,hashlib
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from backend.paths import ROOT,write_json
def main():
    manifest=json.loads((ROOT/'data/manifests/inventory.json').read_text(encoding='utf-8'));checked=[]
    for item in manifest['files']:
        path=Path(item['path']);entry={'path':str(path),'filename':item['filename'],'expected_sha256':item.get('sha256')}
        try:
            digest=hashlib.sha256()
            with path.open('rb') as f:
                for chunk in iter(lambda:f.read(1024*1024),b''):digest.update(chunk)
            entry.update(actual_sha256=digest.hexdigest(),unchanged=digest.hexdigest()==item.get('sha256'))
        except OSError as e:entry.update(unchanged=False,error=f'{type(e).__name__}: {e}')
        checked.append(entry)
    result={'audit_timestamp':manifest['retrieved_at'],'checked':len(checked),'unchanged':sum(r['unchanged'] for r in checked),'passed':all(r['unchanged'] for r in checked),'files':checked}
    write_json(ROOT/'reports/raw_integrity.json',result);print(f"{result['unchanged']}/{result['checked']} original file hashes unchanged")
    if not result['passed']:raise SystemExit(1)
if __name__=='__main__':main()
