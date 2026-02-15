import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Enable standalone output for Docker deployment
  output: "standalone",

  // Note: Rewrites removed - using API route handler instead
  // See app/api/copilot/[[...path]]/route.ts for proxy implementation
};

export default nextConfig;
