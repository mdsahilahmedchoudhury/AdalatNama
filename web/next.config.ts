import type { NextConfig } from "next";

/**
 * The browser only ever talks to this Next.js server. Requests to /api/* are
 * forwarded to the FastAPI service, so the session cookie is first-party and
 * no CORS is needed.
 *
 * next.config is read at build time, so API_INTERNAL_URL is a build-time value
 * (a Docker build argument; see web/Dockerfile). Server Components read the
 * same variable at request time for their own API calls.
 */
const apiInternalUrl = process.env.API_INTERNAL_URL ?? "http://localhost:8000";

const nextConfig: NextConfig = {
  output: "standalone",
  poweredByHeader: false,
  turbopack: {
    rules: {
      "*.css": {
        loaders: ["@tailwindcss/turbopack"],
        as: "*.css",
      },
    },
  },
  async rewrites() {
    return [{ source: "/api/:path*", destination: `${apiInternalUrl}/api/:path*` }];
  },
  async headers() {
    return [
      {
        source: "/:path*",
        headers: [
          { key: "X-Content-Type-Options", value: "nosniff" },
          { key: "Referrer-Policy", value: "same-origin" },
          { key: "X-Frame-Options", value: "DENY" },
          { key: "Permissions-Policy", value: "camera=(), microphone=(), geolocation=()" },
        ],
      },
    ];
  },
};

export default nextConfig;
