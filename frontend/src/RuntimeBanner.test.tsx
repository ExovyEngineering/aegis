import { render, screen } from '@testing-library/react';
import { expect, it } from 'vitest';
import RuntimeBanner from './RuntimeBanner';

it('never treats a rehearsal URL request alone as verified isolation',()=>{
  render(<RuntimeBanner requestedRehearsal runtime={{mode:'operator',isolated:false,offline:false,warning:'Operator workspace.'}}/>);
  expect(screen.getByLabelText('Unverified rehearsal runtime')).toHaveTextContent('THIS SERVER IS NOT A VERIFIED ISOLATED REHEARSAL');
  expect(screen.queryByLabelText('Isolated rehearsal runtime')).not.toBeInTheDocument();
});

it('shows verified rehearsal and offline provenance from the server context',()=>{
  render(<RuntimeBanner runtime={{mode:'isolated_rehearsal',isolated:true,offline:true,rehearsal_id:'89fae623-1399-4b59-936f-7736b115f024',warning:'Simulation'}}/>);
  expect(screen.getByLabelText('Isolated rehearsal runtime')).toHaveTextContent('89fae623');
  expect(screen.getByLabelText('Isolated rehearsal runtime')).toHaveTextContent('Not the operator database');
  expect(screen.getByRole('link',{name:'Timer and guided stages'})).toHaveAttribute('href','/?mode=rehearsal');
});

it('keeps an ordinary operator view quiet and flags misconfiguration regardless of the URL',()=>{
  const view=render(<RuntimeBanner runtime={{mode:'operator',isolated:false,offline:false,warning:'Operator'}}/>);
  expect(screen.queryByRole('complementary')).not.toBeInTheDocument();
  view.rerender(<RuntimeBanner runtime={{mode:'misconfigured',isolated:false,offline:true,warning:'Database does not match the session'}}/>);
  expect(screen.getByLabelText('Unverified rehearsal runtime')).toHaveTextContent('Database does not match the session');
});
