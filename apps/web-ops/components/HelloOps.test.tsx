import { I18nProvider } from '@heroui/react';
import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { HelloOps } from './HelloOps';

describe('<HelloOps />', () => {
  it('renders inside the HeroUI provider with title + body', () => {
    render(
      <I18nProvider locale="en-US">
        <HelloOps />
      </I18nProvider>,
    );
    expect(screen.getByText('HHPS Ops Console')).toBeInTheDocument();
    expect(screen.getByText(/Phase 5 scaffold/)).toBeInTheDocument();
  });
});
