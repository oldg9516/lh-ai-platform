import {
  CopilotRuntime,
  ExperimentalEmptyAdapter,
  copilotRuntimeNextJSAppRouterEndpoint,
} from "@copilotkit/runtime";
import { HttpAgent } from "@copilotkit/runtime";
import { NextRequest } from "next/server";

/**
 * CopilotKit Runtime for Lev Haolam Support Platform
 *
 * Phase 6.1: Stub using HttpAgent pointing to future FastAPI backend
 * Phase 6.2: FastAPI backend implements AG-UI protocol endpoint
 *
 * Architecture:
 * - Frontend (Next.js) → HttpAgent → FastAPI backend (http://localhost:8000)
 * - AG-UI Protocol: Event-based streaming for real-time interactions
 * - HITL: Human-in-the-Loop confirmations via useHumanInTheLoop hook
 *
 * References:
 * - https://docs.copilotkit.ai/
 * - https://www.copilotkit.ai/blog/how-to-add-a-frontend-to-any-ag2-agent-using-ag-ui-protocol
 */

// Backend URL from environment variable
const BACKEND_URL = process.env.NEXT_PUBLIC_BACKEND_URL || "http://localhost:8000";

const serviceAdapter = new ExperimentalEmptyAdapter();

const runtime = new CopilotRuntime({
  agents: {
    support_agent: new HttpAgent({
      // Phase 6.2: FastAPI will implement AG-UI endpoint at /api/copilot
      url: `${BACKEND_URL}/api/copilot`,
    }),
  },
});

export const POST = async (req: NextRequest) => {
  const { handleRequest } = copilotRuntimeNextJSAppRouterEndpoint({
    runtime,
    serviceAdapter,
    endpoint: "/api/copilot",
  });

  return handleRequest(req);
};
