import { fireEvent, render, screen } from '@testing-library/react';
import { expect, it } from 'vitest';
import ModelErrorAnalysis from './ModelErrorAnalysis';
it('shows only recorded subgroup results with scientific limits', () => {
  render(<ModelErrorAnalysis model={{status:'retrospective',error_analysis:[{state:'MO',n:42,prevalence:0.1,brier:0.09}]}} />);
  fireEvent.click(screen.getByText(/Inspect measured state-level error analysis/));
  expect(screen.getByText('MO')).toBeInTheDocument();
  expect(screen.getByText('0.09000')).toBeInTheDocument();
  expect(screen.getByText(/not independent state-level validation/)).toBeInTheDocument();
});
