import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Enable standalone output for Docker deployment
  output: "standalone",

  // CopilotKit runtime depends on pino which must not be bundled by Next.js
  serverExternalPackages: ["@copilotkit/runtime", "pino", "thread-stream"],
};

export default nextConfig;
