import {
  CopilotRuntime,
  ExperimentalEmptyAdapter,
  copilotRuntimeNextJSAppRouterEndpoint,
} from "@copilotkit/runtime";
import { NextRequest } from "next/server";

/**
 * CopilotKit Runtime for Lev Haolam Support Platform
 *
 * Phase 6.2: Proxies requests to FastAPI backend with AG-UI protocol
 *
 * Architecture:
 * - Frontend (Next.js CopilotKit) → /api/copilot → FastAPI backend
 * - Backend URL configured in next.config.ts rewrites
 * - AG-UI Protocol: Event-based streaming (SSE) for real-time interactions
 * - HITL: Human-in-the-Loop confirmations via useHumanInTheLoop hook
 *
 * References:
 * - https://docs.copilotkit.ai/
 * - https://www.copilotkit.ai/blog/how-to-add-a-frontend-to-any-ag2-agent-using-ag-ui-protocol
 */

const serviceAdapter = new ExperimentalEmptyAdapter();

const runtime = new CopilotRuntime();

export const POST = async (req: NextRequest) => {
  const { handleRequest } = copilotRuntimeNextJSAppRouterEndpoint({
    runtime,
    serviceAdapter,
    endpoint: "/api/copilot",
  });

  return handleRequest(req);
};
