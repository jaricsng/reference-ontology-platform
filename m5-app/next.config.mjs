/** @type {import('next').NextConfig} */
const nextConfig = {
  // Backends are reached server-side from route handlers (see lib/api.ts),
  // so the browser only ever talks to this app — no CORS needed.

  // Emit a self-contained server bundle for a small container image.
  output: "standalone",
};

export default nextConfig;
