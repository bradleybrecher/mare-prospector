// app/layout.js
import "./global.css";

export default function RootLayout({ children }) {
  return (
    <html lang="en">
      {/* Remove any dark class if present */}
      <body>{children}</body>
    </html>
  );
}