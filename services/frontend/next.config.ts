import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Enable standalone output for Docker deployment
  output: "standalone",

  // Proxy AG-UI API requests to ai-engine backend
  async rewrites() {
    const backendUrl = process.env.NEXT_PUBLIC_API_URL || "http://ai-engine:8000";
    return [
      {
        source: "/api/copilot/:path*",
        destination: `${backendUrl}/api/copilot/:path*`,
      },
    ];
  },
};

export default nextConfig;
