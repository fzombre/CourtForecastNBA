import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Send every request for /api/... to the Python API (uvicorn on port 8000).
  // The browser only ever talks to Next.js on port 3000, so there are no CORS problems.
  async rewrites() {
    return [
      {
        source: "/api/:path*",
        destination: `${process.env.API_URL ?? "http://127.0.0.1:8000"}/api/:path*`,
      },
    ];
  },
  cacheComponents: true,
  partialPrefetching: true,
  turbopack: {
    rules: {
      "*.css": {
        loaders: ["@tailwindcss/turbopack"],
        as: "*.css",
      },
    },
  },
};

export default nextConfig;
