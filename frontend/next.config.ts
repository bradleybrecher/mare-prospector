import type { NextConfig } from "next";

const apiBase = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:8000";

const nextConfig: NextConfig = {
  // Proxy /api/* in dev so the EventSource has no CORS surface area and the
  // dashboard and API appear to share an origin to the browser.
  async rewrites() {
    return [{ source: "/api/:path*", destination: `${apiBase}/api/:path*` }];
  },
};

export default nextConfig;
