import { render, screen } from '@testing-library/react';
import { expect, it, vi } from 'vitest';
import ProjectBrief from './ProjectBrief';
import { api } from './api';
vi.mock('./api', () => ({api: vi.fn()}));
vi.mock('./RehearsalWorkspace',()=>({default:()=>null}));
it('shows recorded failures and pending gates beside downloadable evidence', async () => {
  vi.mocked(api).mockResolvedValue({register:{features:[{id:'kiro',priority:'P0',name:'Kiro workflow',status:'pending actual execution',detail:'Sign-in needed',evidence:'docs/kiro_handoff.md'}]},verification:{finished_at:'2026-10-26T12:00:00Z',all_passed:false,checks:[{name:'pytest',passed:false,tests_passed:7,duration_seconds:2,log:'test.txt'}]},brief:{generated_at:'2026-10-26T12:00:00Z',pages:10,sha256:'abc'},notice:'Recorded evidence only'});
  render(<ProjectBrief />);
  expect(await screen.findByText('FAIL')).toBeInTheDocument();
  expect(screen.getByText('pending actual execution')).toBeInTheDocument();
  expect(screen.getByText('Download project brief PDF')).toHaveAttribute('href','/api/project-brief.pdf');
  expect(screen.queryByRole('link',{name:'Download master guide PDF'})).not.toBeInTheDocument();
});
it('offers the complete master guide separately from the shorter status brief',async()=>{
  vi.mocked(api).mockResolvedValue({register:{features:[]},verification:null,brief:null,manual:{generated_at:'2026-10-28T14:00:00-05:00',pages:65,sha256:'guidehash',paper:'US Letter'},notice:'Dated results'});
  render(<ProjectBrief/>);
  expect(await screen.findByRole('link',{name:'Download master guide PDF'})).toHaveAttribute('href','/api/master-guide.pdf');
  expect(screen.getByRole('link',{name:'Read or print guide'})).toHaveAttribute('href','/api/master-guide.html');
  expect(screen.getByRole('link',{name:'Download master guide Markdown'})).toHaveAttribute('href','/api/master-guide.md');
  expect(screen.getByText(/65 pages · US Letter/)).toBeInTheDocument();
  expect(screen.getByRole('link',{name:'Download project brief PDF'})).toBeInTheDocument();
  expect(screen.getByRole('heading',{name:'P2 · Stretch work and deferred extensions'})).toBeInTheDocument();
});
