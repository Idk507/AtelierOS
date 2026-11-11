import type { Metadata } from 'next';
import './globals.css';

export const metadata: Metadata = {title: 'AtelierOS — Design studio',
  description: 'An editable, versioned workspace for garment design and human review.'};

export default function RootLayout({children}: Readonly<{children: React.ReactNode}>) {
  return <html lang="en"><body>{children}</body></html>;
}
