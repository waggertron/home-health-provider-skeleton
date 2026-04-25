import './globals.css';
import type { Metadata } from 'next';

export const metadata: Metadata = {
  title: 'HHPS — Home-health dispatch, simplified',
  description:
    'A B2B home-health dispatching platform with OR-Tools routing, real-time updates, and a clean dispatcher UI. Portfolio demo.',
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
