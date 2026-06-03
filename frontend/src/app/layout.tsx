import type { Metadata } from 'next';
import { Geist } from 'next/font/google'; // Updated import
import './globals.css';
import { Toaster } from "@/components/ui/toaster"; // Import Toaster

const geistSans = Geist({
  variable: '--font-geist-sans',
  subsets: ['latin'],
});

// Remove Geist Mono if not needed, or keep if used elsewhere
// const geistMono = Geist_Mono({
//   variable: '--font-geist-mono',
//   subsets: ['latin'],
// });

export const metadata: Metadata = {
  title: 'Neurolingo',
  description: 'Sprachanalyse-Tool fuer klinische Diagnostik',
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      {/* Apply Geist Sans font variable */}
      <body className={`${geistSans.variable} font-sans antialiased`}>
        {children}
        <Toaster /> {/* Add Toaster for notifications */}
      </body>
    </html>
  );
}
