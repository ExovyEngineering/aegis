import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { expect, it, vi } from 'vitest';
import VerificationReview, { VerificationStatus } from './VerificationReview';
import { api } from './api';
vi.mock('./api', () => ({api:vi.fn()}));
it('requires human identity and every checkbox for completion, with version guards', async () => {
  vi.mocked(api).mockResolvedValue({});const onSaved=vi.fn().mockResolvedValue(undefined);
  const shipment:any={id:'SH03',verification_required:true,verification_version:2};
  render(<VerificationReview assignments={[shipment]} revision={4} actor="Reviewer" reason="Reviewed scenario conditions" onSaved={onSaved} />);
  expect(screen.getByText('Record verification review complete')).toBeDisabled();
  for (const checkbox of screen.getAllByRole('checkbox')) fireEvent.click(checkbox);
  fireEvent.click(screen.getByText('Record verification review complete'));
  await waitFor(() => expect(api).toHaveBeenCalledWith('/dispatch/assignments/SH03/verification',expect.objectContaining({expected_network_revision:4,expected_verification_version:2,outcome:'complete'})));
  expect(onSaved).toHaveBeenCalled();
});
it('keeps assignment acknowledgment distinct from verification and safety certification', () => {
  render(<VerificationStatus shipment={{id:'SH03',verification_required:true,acknowledged:true} as any} />);
  expect(screen.getByText('Targeted verification: pending dispatcher review')).toBeInTheDocument();
  expect(screen.getByText(/Do not treat assignment acknowledgment as verification/)).toBeInTheDocument();
});
