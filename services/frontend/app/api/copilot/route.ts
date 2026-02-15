import { NextRequest } from "next/server";

/**
 * AG-UI Streaming Endpoint for CopilotKit
 *
 * This endpoint receives messages from the CopilotKit frontend and:
 * 1. Forwards them to the FastAPI backend (ai-engine)
 * 2. Streams back agent responses with tool calls
 * 3. Handles HITL confirmations for write operations
 *
 * Phase 6.1: Initial stub that proxies to FastAPI
 * Phase 6.2: Full AG-UI protocol implementation
 */

export const runtime = "edge"; // Use Edge Runtime for streaming

/**
 * GET /api/copilot/info - Agent registration endpoint
 * Returns metadata about available agents for CopilotKit runtime sync
 */
export async function GET() {
  return new Response(
    JSON.stringify({
      agents: [
        {
          name: "support_agent",
          description: "Lev Haolam customer support assistant with HITL confirmations",
          type: "custom",
        },
      ],
      actions: [],
      sdkVersion: "1.51.3",
    }),
    {
      headers: { "Content-Type": "application/json" },
    }
  );
}

/**
 * POST /api/copilot - AG-UI streaming endpoint
 * Handles chat messages and streams responses using AG-UI protocol
 */
export async function POST(req: NextRequest) {
  try {
    const body = await req.json();

    // TODO: Forward to FastAPI backend (ai-engine)
    // For now, return a simple response with proper AG-UI event types
    const encoder = new TextEncoder();
    const stream = new ReadableStream({
      async start(controller) {
        // AG-UI protocol events:
        // 1. RUN_STARTED - agent execution begins
        controller.enqueue(
          encoder.encode(
            `data: ${JSON.stringify({
              type: "RUN_STARTED",
              runId: crypto.randomUUID(),
            })}\n\n`
          )
        );

        // 2. TEXT_MESSAGE_START - begin text response
        controller.enqueue(
          encoder.encode(
            `data: ${JSON.stringify({
              type: "TEXT_MESSAGE_START",
            })}\n\n`
          )
        );

        // 3. TEXT_MESSAGE_CONTENT - actual message content
        const message =
          "Hello! I'm your Lev Haolam support assistant. HITL forms coming soon...\n";
        controller.enqueue(
          encoder.encode(
            `data: ${JSON.stringify({
              type: "TEXT_MESSAGE_CONTENT",
              content: message,
            })}\n\n`
          )
        );

        // 4. TEXT_MESSAGE_END - complete text response
        controller.enqueue(
          encoder.encode(
            `data: ${JSON.stringify({
              type: "TEXT_MESSAGE_END",
            })}\n\n`
          )
        );

        // 5. RUN_FINISHED - agent execution complete
        controller.enqueue(
          encoder.encode(
            `data: ${JSON.stringify({
              type: "RUN_FINISHED",
            })}\n\n`
          )
        );

        controller.close();
      },
    });

    return new Response(stream, {
      headers: {
        "Content-Type": "text/event-stream",
        "Cache-Control": "no-cache",
        "Connection": "keep-alive",
      },
    });
  } catch (error) {
    console.error("Copilot API error:", error);
    return new Response(
      JSON.stringify({ error: "Internal server error" }),
      { status: 500 }
    );
  }
}
