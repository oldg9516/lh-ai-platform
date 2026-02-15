import { NextRequest } from "next/server";

/**
 * CopilotKit Proxy for Lev Haolam Support Platform
 *
 * Phase 6.2: Proxies requests to FastAPI backend with AG-UI protocol
 *
 * Architecture:
 * - Frontend (Next.js CopilotKit) → /api/copilot → FastAPI backend
 * - Backend implements full AG-UI protocol with event streaming
 * - This route is a simple proxy - all agent logic is in the backend
 * - AG-UI Protocol: Event-based streaming (SSE) for real-time interactions
 * - HITL: Human-in-the-Loop confirmations via useHumanInTheLoop hook
 *
 * References:
 * - https://docs.copilotkit.ai/
 * - https://www.copilotkit.ai/blog/how-to-add-a-frontend-to-any-ag2-agent-using-ag-ui-protocol
 */

/**
 * Get backend URL based on environment
 *
 * Priority:
 * 1. If running outside Docker (can't reach ai-engine), use localhost
 * 2. Otherwise use NEXT_PUBLIC_API_URL or default to ai-engine (Docker)
 */
function getBackendUrl(): string {
  // In development, always use localhost (running outside Docker)
  if (process.env.NODE_ENV === "development") {
    return "http://localhost:8000";
  }

  // In production, use env var or Docker service name
  return process.env.NEXT_PUBLIC_API_URL || "http://ai-engine:8000";
}

/**
 * GET handler - proxies agent discovery requests (/info, etc.)
 * Catch-all route handles /api/copilot and /api/copilot/* paths
 */
export const GET = async (
  req: NextRequest,
  context: { params: Promise<{ path?: string[] }> }
) => {
  try {
    const backendUrl = getBackendUrl();
    const { path } = await context.params;

    // Build backend path from catch-all params
    const backendPath = path && path.length > 0 ? `/${path.join("/")}` : "";
    const targetUrl = `${backendUrl}/api/copilot${backendPath}`;

    console.log(`[CopilotProxy GET] ${targetUrl}`);

    const response = await fetch(targetUrl, {
      method: "GET",
      headers: {
        "Content-Type": "application/json",
      },
    });

    const data = await response.json();

    return new Response(JSON.stringify(data), {
      status: response.status,
      headers: {
        "Content-Type": "application/json",
      },
    });
  } catch (error) {
    console.error("[CopilotProxy GET] Error:", error);
    return new Response(
      JSON.stringify({
        error: "Failed to connect to AI backend",
        details: error instanceof Error ? error.message : String(error),
      }),
      {
        status: 502,
        headers: { "Content-Type": "application/json" },
      }
    );
  }
};

/**
 * POST handler - proxies chat messages and streaming responses
 * Catch-all route handles /api/copilot and /api/copilot/* paths
 */
export const POST = async (
  req: NextRequest,
  context: { params: Promise<{ path?: string[] }> }
) => {
  try {
    const backendUrl = getBackendUrl();
    const { path } = await context.params;

    // Build backend path from catch-all params (default to root for chat messages)
    const backendPath = path && path.length > 0 ? `/${path.join("/")}` : "";
    const targetUrl = `${backendUrl}/api/copilot${backendPath}`;

    console.log(`[CopilotProxy POST] ${targetUrl}`);

    // Proxy the request to the FastAPI backend
    const response = await fetch(targetUrl, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: await req.text(),
    });

    if (!response.ok) {
      console.error(
        `[CopilotProxy POST] Backend returned ${response.status}: ${response.statusText}`
      );
    }

    // Return the streaming response with proper headers
    return new Response(response.body, {
      status: response.status,
      headers: {
        "Content-Type": "text/event-stream",
        "Cache-Control": "no-cache",
        "Connection": "keep-alive",
      },
    });
  } catch (error) {
    console.error("[CopilotProxy POST] Error proxying to backend:", error);
    return new Response(
      JSON.stringify({
        error: "Failed to connect to AI backend",
        details: error instanceof Error ? error.message : String(error),
      }),
      {
        status: 502,
        headers: { "Content-Type": "application/json" },
      }
    );
  }
};
