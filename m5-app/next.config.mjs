/** @type {import('next').NextConfig} */
const nextConfig = {
  // Backends are reached server-side from route handlers (see lib/api.ts),
  // so the browser only ever talks to this app — no CORS needed.
};

export default nextConfig;
