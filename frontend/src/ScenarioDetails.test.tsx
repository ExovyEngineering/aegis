import { fireEvent, render, screen } from '@testing-library/react';
import { expect, it } from 'vitest';
import ScenarioDetails from './ScenarioDetails';
it('exposes resource arithmetic and exclusion limits without approving a plan', () => {
  const scenario: any = {scenario:'A',name:'Baseline',total_logistics_cost:200,unmet_demand_kg:300,shipments:[],review:{passed:true,method:'Independent check',exclusion_note:'Not a causal solver explanation',violations:[],resources:[{kind:'truck',id:'T1',used_kg:400,limit_kg:500,remaining_kg:100}],excluded_shipments:[{shipment_id:'SH1',destination:'D1',quantity_kg:400,reasons:['lot held']}]}};
  render(<ScenarioDetails scenarios={[scenario]} />);
  expect(screen.getByText('100 kg')).toBeInTheDocument();
  fireEvent.click(screen.getByText('Excluded candidates'));
  expect(screen.getByText('lot held')).toBeInTheDocument();
  expect(screen.getByText('Not a causal solver explanation')).toBeInTheDocument();
  expect(screen.queryByText('Approve')).not.toBeInTheDocument();
});
