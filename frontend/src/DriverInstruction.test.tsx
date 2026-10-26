import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { expect, it, vi } from 'vitest';
import DriverInstruction from './DriverInstruction';
import { api } from './api';
import type { Shipment } from './types';
vi.mock('./api', () => ({ api: vi.fn() }));
it('acknowledges the exact dispatcher instruction version separately from trip acknowledgment', async () => {
  vi.mocked(api).mockResolvedValue({});
  const reload = vi.fn().mockResolvedValue(undefined);
  render(<DriverInstruction shipment={{ id: 'SH01', instruction_revision: 4, instruction_acknowledged: false } as Shipment} onAcknowledged={reload} />);
  fireEvent.click(screen.getByRole('button', { name: 'Acknowledge new instruction' }));
  await waitFor(() => expect(api).toHaveBeenCalledWith('/driver/SH01/instruction-ack', { instruction_revision: 4 }));
  expect(reload).toHaveBeenCalled();
});
it('does not show a separate acknowledgment for initial assignment instructions', () => {
  render(<DriverInstruction shipment={{ id: 'SH01', instruction_revision: 0 } as Shipment} onAcknowledged={vi.fn()} />);
  expect(screen.queryByRole('button')).not.toBeInTheDocument();
});
