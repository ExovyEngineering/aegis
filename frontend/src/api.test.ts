import { afterEach, describe, expect, it, vi } from 'vitest';
import { api, fixed, recallRows } from './api';
afterEach(() => vi.unstubAllGlobals());
describe('source handling', () => {
  it('does not manufacture recall notices from an unknown response', () => {
    expect(recallRows({ error: 'unavailable' })).toEqual([]);
    expect(recallRows({ data: [{ title: 'Official notice' }] })).toEqual([{ title: 'Official notice' }]);
    expect(fixed(undefined)).toBe('—');
  });
  it('preserves actionable backend failure messages for stale approvals', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: false, json: async () => ({ detail: 'Network changed; generate a fresh proposal' }) }));
    await expect(api('/proposals/old/approve', { actor: 'Dispatcher', reason: 'Reviewed' })).rejects.toThrow('Network changed');
  });
  it('reports malformed server responses with a recoverable connection message', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ok:false,status:502,json:async () => {throw new SyntaxError('not JSON');}}));
    await expect(api('/network')).rejects.toThrow('unreadable response (502)');
  });
});
