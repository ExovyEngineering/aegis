import { render, screen } from '@testing-library/react';
import { expect, it, vi } from 'vitest';
import ProjectBrief from './ProjectBrief';
import { api } from './api';
vi.mock('./api', () => ({api: vi.fn()}));
it('shows recorded failures and pending gates beside downloadable evidence', async () => {
  vi.mocked(api).mockResolvedValue({register:{features:[{id:'kiro',priority:'P0',name:'Kiro workflow',status:'pending actual execution',detail:'Sign-in needed',evidence:'docs/kiro_handoff.md'}]},verification:{finished_at:'2026-10-26T12:00:00Z',all_passed:false,checks:[{name:'pytest',passed:false,tests_passed:7,duration_seconds:2,log:'test.txt'}]},brief:{generated_at:'2026-10-26T12:00:00Z',pages:10,sha256:'abc'},notice:'Recorded evidence only'});
  render(<ProjectBrief />);
  expect(await screen.findByText('FAIL')).toBeInTheDocument();
  expect(screen.getByText('pending actual execution')).toBeInTheDocument();
  expect(screen.getByText('Download project brief PDF')).toHaveAttribute('href','/api/project-brief.pdf');
});
