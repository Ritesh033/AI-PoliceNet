import { afterEach, describe, expect, it } from 'vitest';
import { cleanup, render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { App } from './App';

afterEach(cleanup);

function tile(name: string) {
  return screen.getByRole('region', { name });
}

describe('Overview console', () => {
  it('labels itself as demo-only, with sample data and no live integrations', () => {
    render(<App simulateLive={false} />);
    const notice = screen.getByRole('region', { name: /demo notice/i });
    expect(notice).toHaveTextContent(/demo only/i);
    expect(notice).toHaveTextContent(/not live indian police records/i);
    expect(notice).toHaveTextContent(/not connected to any social-media account or police system/i);
    expect(screen.getByText('DEMO')).toBeInTheDocument();
  });

  it('shows the prototype headline figures', () => {
    render(<App simulateLive={false} />);
    expect(within(tile('Alerts received')).getByText('1,284')).toBeInTheDocument();
    expect(within(tile('Awaiting review')).getByText('76')).toBeInTheDocument();
    expect(within(tile('Urgent referrals')).getByText('12')).toBeInTheDocument();
    expect(within(tile('Open complaints')).getByText('143')).toBeInTheDocument();
  });

  it('exposes accessible tabs with the Overview selected and arrow-key navigation', async () => {
    const user = userEvent.setup();
    render(<App simulateLive={false} />);
    const tabs = screen.getAllByRole('tab');
    expect(tabs.map((t) => t.textContent)).toEqual(['Overview', 'Social media', 'Accountability', 'Legal cases']);
    expect(screen.getByRole('tab', { name: 'Overview' })).toHaveAttribute('aria-selected', 'true');

    screen.getByRole('tab', { name: 'Overview' }).focus();
    await user.keyboard('{ArrowRight}');
    expect(screen.getByRole('tab', { name: 'Social media' })).toHaveAttribute('aria-selected', 'true');
    expect(screen.getByRole('tabpanel')).toHaveTextContent(/module a · planned/i);
    await user.keyboard('{Home}');
    expect(screen.getByRole('tab', { name: 'Overview' })).toHaveAttribute('aria-selected', 'true');
  });

  it('switches the reporting period and keeps current-status figures unchanged', async () => {
    const user = userEvent.setup();
    render(<App simulateLive={false} />);
    await user.click(screen.getByRole('button', { name: '24 hours' }));
    expect(screen.getByRole('button', { name: '24 hours' })).toHaveAttribute('aria-pressed', 'true');
    expect(within(tile('Alerts received')).queryByText('1,284')).not.toBeInTheDocument();
    expect(within(tile('Awaiting review')).getByText('76')).toBeInTheDocument();
  });

  it('opens a case, and referring it updates the counts and the audit trail', async () => {
    const user = userEvent.setup();
    render(<App simulateLive={false} />);
    const detail = screen.getByRole('region', { name: /APN-1001/ });
    expect(within(detail).getByText(/preview withheld|no media is bundled/i)).toBeInTheDocument();
    expect(detail).toHaveTextContent(/does not register an fir/i);

    await user.type(within(detail).getByLabelText(/reviewer note/i), 'Context verified');
    await user.click(within(detail).getByRole('button', { name: /refer to authorized officer/i }));

    expect(within(tile('Awaiting review')).getByText('75')).toBeInTheDocument();
    expect(within(tile('Urgent referrals')).getByText('13')).toBeInTheDocument();
    expect(within(detail).getByRole('status')).toHaveTextContent(/referred to authorized officer/i);
    expect(within(detail).getByText(/context verified/i)).toBeInTheDocument();
    expect(within(detail).queryByRole('button', { name: /refer to authorized officer/i })).not.toBeInTheDocument();
  });

  it('sensitive items never render a media preview', async () => {
    const user = userEvent.setup();
    render(<App simulateLive={false} />);
    await user.click(screen.getByRole('button', { name: 'APN-1002' }));
    const detail = screen.getByRole('region', { name: /APN-1002/ });
    expect(detail).toHaveTextContent(/preview withheld/i);
    expect(detail.querySelector('img, video, audio')).toBeNull();
  });

  it('routes conduct complaints to a supervisory authority rather than an officer', async () => {
    const user = userEvent.setup();
    render(<App simulateLive={false} />);
    await user.click(screen.getByRole('button', { name: 'APN-1003' }));
    const detail = screen.getByRole('region', { name: /APN-1003/ });
    expect(within(detail).getByRole('button', { name: /route to supervisory authority/i })).toBeInTheDocument();
    expect(detail).toHaveTextContent(/no disciplinary inference/i);
  });

  it('offers a table alternative for each chart', async () => {
    const user = userEvent.setup();
    render(<App simulateLive={false} />);
    const alerts = screen.getByRole('region', { name: 'Alerts over time' });
    await user.click(within(alerts).getByRole('button', { name: /view as table/i }));
    const table = within(alerts).getByRole('table');
    expect(within(table).getAllByRole('row').length).toBeGreaterThan(7);
  });

  it('lets the live simulation be paused and resumed', async () => {
    const user = userEvent.setup();
    render(<App simulateLive />);
    const feed = screen.getByRole('region', { name: 'Live activity' });
    await user.click(within(feed).getByRole('button', { name: /pause/i }));
    expect(within(feed).getByText('Paused')).toBeInTheDocument();
    await user.click(within(feed).getByRole('button', { name: /resume/i }));
    expect(within(feed).getByText(/live \(simulated\)/i)).toBeInTheDocument();
  });
});
