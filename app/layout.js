import { Inter } from "next/font/google";
import "./global.css"; // Import your styles here

const inter = Inter({ subsets: ["latin"] });

export const metadata = {
  title: "MaRe Command Center",
  description: "Strategic Growth Catalyst for Modern Markets",
};

export default function RootLayout({ children }) {
  return (
    <html lang="en">
      <body className={inter.className}>
        {/* You could add a Navbar here if you want it on every page */}
        <main>{children}</main>
      </body>
    </html>
  );
}