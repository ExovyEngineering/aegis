"""Verify explicit rehearsal isolation without opening an operational database."""
import os
from pathlib import Path
from uuid import UUID

from fastapi import HTTPException
from backend.paths import ROOT


def runtime_context(db_path=None, root=ROOT, env=None):
    environment = os.environ if env is None else env
    workspace = Path(root).resolve()
    rehearsal_id = environment.get('AEGIS_REHEARSAL_ID')
    offline_value = environment.get('AEGIS_OFFLINE_DEMO')
    offline = offline_value == '1'
    try:
        requested = Path(db_path or environment.get('AEGIS_DB_PATH') or workspace / 'data/aegis.sqlite')
        selected = requested.resolve()
    except (OSError, ValueError, TypeError, RuntimeError) as error:
        return {'mode':'misconfigured','isolated':False,'offline':offline,
                'rehearsal_id':rehearsal_id or None,'database_relative_path':None,
                'warning':f'Rehearsal database path cannot be resolved: {type(error).__name__}: {error}'}
    directory = workspace / 'data/rehearsals'
    relative = selected.relative_to(workspace).as_posix() if selected.is_relative_to(workspace) else None
    context = {
        'mode': 'operator', 'isolated': False, 'offline': offline,
        'rehearsal_id': rehearsal_id or None, 'database_relative_path': relative,
        'warning': 'Operator workspace. Guided rehearsal mutations require an explicitly isolated rehearsal server.',
    }
    partial = (rehearsal_id is not None or offline_value is not None
               or selected.is_relative_to(directory) or requested.absolute().is_relative_to(directory))
    if not partial:
        return context

    def invalid(message):
        return dict(context, mode='misconfigured', warning=message)

    try:
        if not rehearsal_id or str(UUID(rehearsal_id)) != rehearsal_id:
            return invalid('Rehearsal configuration requires a canonical lowercase UUID and its matching isolated database path.')
        if offline_value not in (None, '0', '1'):
            return invalid('AEGIS_OFFLINE_DEMO must be 0 or 1 when configuring a rehearsal server.')
        expected = (directory / f'{rehearsal_id}.sqlite').resolve()
        if not expected.is_relative_to(workspace) or selected != expected:
            return invalid('Rehearsal database must resolve to data/rehearsals/<rehearsal UUID>.sqlite inside this workspace.')
        operator = workspace / 'data/aegis.sqlite'
        if selected.exists() and operator.exists() and selected.samefile(operator):
            return invalid('Rehearsal database aliases the operator database; use a fresh isolated file.')
    except (OSError, ValueError, TypeError, RuntimeError) as error:
        return invalid(f'Rehearsal isolation could not be verified: {type(error).__name__}: {error}')
    return dict(context, mode='isolated_rehearsal', isolated=True,
                warning='Isolated simulated rehearsal. Timer and milestone records do not prove presentation quality, author approval or genuine Kiro execution.')


def require_valid_runtime(path, root=ROOT, env=None):
    """Call before opening SQLite or creating its parent directory."""
    context = runtime_context(path, root=root, env=env)
    if context['mode'] == 'misconfigured':
        raise HTTPException(503, context['warning'])
    return context
