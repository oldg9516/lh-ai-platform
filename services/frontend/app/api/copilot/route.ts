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

export async function POST(req: NextRequest) {
  try {
    const body = await req.json();

    // TODO: Implement AG-UI streaming protocol
    // For now, return a simple response
    const encoder = new TextEncoder();
    const stream = new ReadableStream({
      async start(controller) {
        // AG-UI protocol: send textDelta events
        const message = {
          type: "textDelta",
          delta: "Hello! I'm your Lev Haolam support assistant. HITL forms coming soon...\n"
        };

        controller.enqueue(
          encoder.encode(`data: ${JSON.stringify(message)}\n\n`)
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
