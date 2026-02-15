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

export const POST = async (req: NextRequest) => {
  try {
    // Determine backend URL based on environment
    // In development: use localhost:8000
    // In Docker production: use ai-engine:8000
    const isDevelopment = process.env.NODE_ENV === "development";
    const backendUrl = isDevelopment
      ? "http://localhost:8000"
      : process.env.NEXT_PUBLIC_API_URL || "http://ai-engine:8000";

    console.log(`[CopilotProxy] Proxying to backend: ${backendUrl}`);

    // Proxy the request to the FastAPI backend
    const response = await fetch(`${backendUrl}/api/copilot`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: await req.text(),
    });

    if (!response.ok) {
      console.error(
        `[CopilotProxy] Backend returned ${response.status}: ${response.statusText}`
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
    console.error("[CopilotProxy] Error proxying to backend:", error);
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
