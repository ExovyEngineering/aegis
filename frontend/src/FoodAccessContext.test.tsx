import { fireEvent, render, screen } from '@testing-library/react';
import { beforeEach, expect, it, vi } from 'vitest';
import FoodAccessContext from './FoodAccessContext';
import { api } from './api';
vi.mock('./api',()=>({api:vi.fn()}));
const context={status:'available',provider:'USDA ERS',source_url:'https://ers.usda.gov/',documentation_url:'https://ers.usda.gov/',source_file:{filename:'atlas.xlsx',sha256:'actual-source-hash'},ingested_at:'2026-10-27T12:00:00Z',release_note:'Source release July 2025',geography:{county_count:2},variables:[{code:'GROC20',label:'Grocery stores',unit:'stores',year:2020,sheet:'STORES',denominator:'None; store count',definition:'Source-defined grocery stores.'}],records:[{FIPS:'29019',State:'MO',County:'Boone',county_display_name:'Boone',GROC20:null},{FIPS:'29510',State:'MO',County:'St. Louis',county_display_name:'St. Louis city',GROC20:8}],limitations:['No route-location join or dispatch weights.'],integrity_verified:true};
beforeEach(()=>{vi.mocked(api).mockReset();vi.mocked(api).mockResolvedValue(context);});
it('shows source-year context, preserves suppressed values and distinguishes a city county-equivalent',async()=>{
  render(<FoodAccessContext/>);
  expect(await screen.findByText('Missing / suppressed')).toBeInTheDocument();
  fireEvent.change(screen.getByLabelText('Compare USDA county'),{target:{value:'29510'}});
  expect(screen.getByText('St. Louis city:',{exact:false})).toBeInTheDocument();
  fireEvent.change(screen.getByLabelText('USDA county'),{target:{value:'29510'}});
  expect(screen.queryByText('Missing / suppressed')).not.toBeInTheDocument();
  expect(screen.getByRole('link',{name:'Download county CSV'})).toHaveAttribute('href','/api/food-access.csv');
  expect(screen.getByText(/Missing or suppressed values remain null/)).toBeInTheDocument();
});
it('exposes an unavailable or unverified extract and supports retry',async()=>{
  vi.mocked(api).mockResolvedValueOnce({...context,integrity_verified:false});
  render(<FoodAccessContext/>);
  expect(await screen.findByRole('alert')).toHaveTextContent('Verified USDA county context is unavailable');
  expect(screen.queryByText('Missing / suppressed')).not.toBeInTheDocument();
  fireEvent.click(screen.getByRole('button',{name:'Retry USDA context'}));
  expect(await screen.findByText('Missing / suppressed')).toBeInTheDocument();
});
