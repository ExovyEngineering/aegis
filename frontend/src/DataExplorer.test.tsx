import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { expect, it, vi } from 'vitest';
import DataExplorer from './DataExplorer';
import { api } from './api';
vi.mock('./api', async () => ({ ...await vi.importActual('./api'), api: vi.fn() }));
it('filters one named source, shows literal source values and page missingness', async () => {
  vi.mocked(api).mockImplementation(async path => path === '/data/catalog' ? [{id:'fsis_poultry',name:'FSIS samples',status:'available',rows:3,note:'Not illness probability',columns:[{name:'state',type:'string'}]}] : {rows:[{state:null}],columns:['state'],offset:0,returned_rows:1,matching_rows:3,next_offset:null,page_null_counts:{state:1},provenance:'Nulls on this page only'} as any);
  render(<DataExplorer />);
  await screen.findByText('Not illness probability');
  expect(await screen.findByText('∅')).toBeInTheDocument();
  expect(screen.getByText('1 null on this page')).toBeInTheDocument();
  fireEvent.change(screen.getByLabelText('Filter column'),{target:{value:'state'}});
  fireEvent.change(screen.getByLabelText('Contains text'),{target:{value:'MO'}});
  fireEvent.click(screen.getByText('Apply source filter'));
  await waitFor(() => expect(api).toHaveBeenCalledWith('/data/fsis_poultry?offset=0&limit=25&field=state&contains=MO'));
});
