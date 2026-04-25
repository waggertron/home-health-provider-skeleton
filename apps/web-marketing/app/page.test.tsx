import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import HomePage from './page';

describe('<HomePage />', () => {
  it('renders the brand name and a link to the demo console', () => {
    render(<HomePage />);
    expect(screen.getAllByText('HHPS').length).toBeGreaterThan(0);
    const links = screen.getAllByRole('link');
    expect(links.some((a) => a.getAttribute('href')?.includes('localhost:3001'))).toBe(true);
  });

  it('renders the three feature pillars', () => {
    render(<HomePage />);
    expect(screen.getByText(/AI-driven scheduling/)).toBeInTheDocument();
    expect(screen.getByText(/Real-time fanout/)).toBeInTheDocument();
    expect(screen.getByText(/Patient engagement/)).toBeInTheDocument();
  });

  it('renders the pricing section with a demo tier', () => {
    render(<HomePage />);
    expect(screen.getByText('Demo tier')).toBeInTheDocument();
    expect(screen.getByText(/\$0/)).toBeInTheDocument();
  });

  it('renders the inert contact form', () => {
    render(<HomePage />);
    expect(screen.getByLabelText(/contact form/i)).toBeInTheDocument();
  });
});
