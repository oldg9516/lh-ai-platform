/**
 * CopilotKit Runtime Endpoint for Lev Haolam Support Platform
 *
 * Uses CopilotRuntime SDK with HttpAgent to connect to FastAPI backend.
 * The backend implements AG-UI protocol for streaming agent responses.
 *
 * Architecture:
 * Frontend (CopilotKit) → CopilotRuntime (this route) → HttpAgent → FastAPI backend
 */

import {
  CopilotRuntime,
  ExperimentalEmptyAdapter,
  copilotRuntimeNextJSAppRouterEndpoint,
} from "@copilotkit/runtime";
import { HttpAgent } from "@ag-ui/client";
import { NextRequest } from "next/server";

/**
 * Get backend URL based on environment.
 *
 * In Docker: use service name "ai-engine"
 * Fallback: env var NEXT_PUBLIC_API_URL
 */
function getBackendUrl(): string {
  return process.env.NEXT_PUBLIC_API_URL || "http://ai-engine:8000";
}

const serviceAdapter = new ExperimentalEmptyAdapter();

const agents = {
  default: new HttpAgent({ url: `${getBackendUrl()}/api/copilot` }),
};

// eslint-disable-next-line @typescript-eslint/no-explicit-any
const runtime = new CopilotRuntime({ agents } as any);

export const POST = async (req: NextRequest) => {
  const { handleRequest } = copilotRuntimeNextJSAppRouterEndpoint({
    runtime,
    serviceAdapter,
    endpoint: "/api/copilot",
  });

  return handleRequest(req);
};
