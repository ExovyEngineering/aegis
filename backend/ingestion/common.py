"""Bounded discovery/provenance helpers shared by source-specific ingestion."""
import hashlib
import os
import tempfile
import time
from pathlib import Path
import pandas as pd
from backend.paths import ROOT

RUNTIME_PARTS={'.git','.tools','.venv','.aws','.codex','.agents','.vscode','node_modules','__pycache__','.pytest_cache'}
REPOSITORY_OUTPUTS=('backend','frontend','scripts','tests','docs','config','reports','.kiro',
                    'data/processed','data/cache','data/fixtures','data/manifests','data/external')


def source_files(folder, suffixes, excluded=()):
    """Recurse supplied inputs, excluding known generated repository/runtime trees."""
    folder=Path(folder).resolve()
    if not folder.exists():raise FileNotFoundError(f'Data directory does not exist: {folder}')
    if not folder.is_dir():raise NotADirectoryError(f'Data directory is not a folder: {folder}')
    blocked=[Path(p).resolve() for p in excluded]
    if folder==ROOT.resolve():blocked.extend((ROOT/p).resolve() for p in REPOSITORY_OUTPUTS)
    found=[]
    for path in folder.rglob('*'):
        if not path.is_file() or path.is_symlink() or path.suffix.lower() not in suffixes:continue
        relative=path.relative_to(folder)
        if any(part in RUNTIME_PARTS for part in relative.parts):continue
        if any(path.resolve().is_relative_to(p) for p in blocked):continue
        found.append(path)
    return sorted(found,key=lambda p:(p.relative_to(folder).as_posix().casefold(),p.relative_to(folder).as_posix()))


def sha256_file(path):
    digest=hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda:stream.read(1024*1024),b''):digest.update(chunk)
    return digest.hexdigest()


def table_separator(path):return '\t' if Path(path).suffix.lower()=='.tsv' else ','


def read_columns(path):
    # Inspect only the header before choosing an adapter or loading observations.
    return list(pd.read_csv(path,sep=table_separator(path),encoding='utf-8-sig',nrows=0).columns)


def read_table(path,**kwargs):
    return pd.read_csv(path,sep=table_separator(path),encoding='utf-8-sig',**kwargs)


def exact_error(error):return f'{type(error).__name__}: {error}'


def publish_parquet(frame,path):
    """Publish a whole derived table; a failed writer leaves previous bytes intact."""
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=path.parent,prefix='.'+path.name+'.',suffix='.tmp',delete=False) as stream:
        temporary=Path(stream.name)
    try:
        frame.to_parquet(temporary,index=False)
        for attempt in range(8):
            try:os.replace(temporary,path);break
            except PermissionError:
                if attempt==7:raise
                time.sleep(.005*(attempt+1))
    finally:
        if temporary.exists():temporary.unlink()
