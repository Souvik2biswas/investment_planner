import { Outfit } from "next/font/google";
import "./globals.css";

const outfit = Outfit({
  subsets: ["latin"],
  display: "swap",
});

export const metadata = {
  title: "Apex Finance | Autonomous Financial Co-Pilot",
  description: "Advanced multi-agent financial orchestrator for transaction parsing, deterministic spending math, and RAG-based tax savings advisory.",
};

export default function RootLayout({ children }) {
  return (
    <html lang="en" className={outfit.className}>
      <body>
        {children}
      </body>
    </html>
  );
}
