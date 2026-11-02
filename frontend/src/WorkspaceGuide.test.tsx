import { fireEvent, render, screen, within } from '@testing-library/react';
import { expect, it, vi } from 'vitest';
import WorkspaceGuide, { type WorkspaceView } from './WorkspaceGuide';

it('explains comparison, simulation and approval separately in Command', () => {
  const navigate = vi.fn();
  render(<WorkspaceGuide view="command" onNavigate={navigate} />);
  const guide = screen.getByRole('complementary', { name: 'Workspace guide' });
  expect(guide).toHaveTextContent('Changes simulation only after explicit apply or approval');
  const details = within(guide).getByText('How this connects').closest('details')!;
  expect(details).not.toHaveAttribute('open');
  fireEvent.click(within(guide).getByText('How this connects'));
  expect(details).toHaveAttribute('open');
  expect(details).toHaveTextContent('does not change a truck assignment or automatically avoid a closure');
  expect(details).toHaveTextContent('clears approved assignments');
  expect(details).toHaveTextContent('Only a separate human approval publishes simulated driver assignments');
  expect(navigate).not.toHaveBeenCalled();
});

it('navigates only through explicit connected-workspace buttons', () => {
  const navigate = vi.fn();
  render(<WorkspaceGuide view="routes" onNavigate={navigate} />);
  expect(screen.getByText('Planning workspace · does not dispatch')).toBeInTheDocument();
  fireEvent.click(screen.getByRole('button', { name: 'Inspect road evidence' }));
  expect(navigate).toHaveBeenNthCalledWith(1, 'roads');
  fireEvent.click(screen.getByRole('button', { name: 'Return to current operation' }));
  expect(navigate).toHaveBeenNthCalledWith(2, 'command');
  expect(navigate).toHaveBeenCalledTimes(2);
});

it('replaces the page explanation and closes expanded details when the view changes', () => {
  const navigate = vi.fn();
  const view = render(<WorkspaceGuide view="routes" onNavigate={navigate} />);
  fireEvent.click(screen.getByText('How this connects'));
  expect(screen.getByText('How this connects').closest('details')).toHaveAttribute('open');
  view.rerender(<WorkspaceGuide view="roads" onNavigate={navigate} />);
  expect(screen.getByText('How this connects').closest('details')).not.toHaveAttribute('open');
  expect(screen.getByRole('heading', { name: 'Inspect routes alongside road evidence' })).toBeInTheDocument();
  expect(screen.queryByRole('heading', { name: 'Experiment with a route design' })).not.toBeInTheDocument();
  expect(screen.getByRole('complementary')).toHaveTextContent('does not feed closures into OSRM');
  expect(navigate).not.toHaveBeenCalled();
});

it.each<WorkspaceView>(['command', 'routes', 'roads', 'dispatch', 'evidence', 'science', 'assistant', 'brief', 'drive'])('gives %s a scoped explanation and connected destinations', view => {
  render(<WorkspaceGuide view={view} onNavigate={vi.fn()} />);
  const guide = screen.getByRole('complementary', { name: 'Workspace guide' });
  expect(within(guide).getByRole('heading', { level: 2 })).toBeInTheDocument();
  expect(within(guide).getAllByRole('button')).toHaveLength(2);
  expect(within(guide).getByText('How this connects')).toBeInTheDocument();
});

it('preserves the actual driver and dispatcher boundaries in their explanations', () => {
  const view = render(<WorkspaceGuide view="dispatch" onNavigate={vi.fn()} />);
  expect(screen.getByRole('complementary')).toHaveTextContent('Releasing it does not recreate them');
  expect(screen.getByRole('complementary')).toHaveTextContent('does not itself compute or approve a replacement route');
  view.rerender(<WorkspaceGuide view="drive" onNavigate={vi.fn()} />);
  expect(screen.getByRole('complementary')).toHaveTextContent('does not detect actual motion, GPS or physical sensors');
  expect(screen.getByRole('complementary')).toHaveTextContent('do not automatically reroute the truck or hold a lot');
});
