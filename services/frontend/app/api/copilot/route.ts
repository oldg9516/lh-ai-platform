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

/**
 * Vercel best practice: Use Edge Runtime for streaming responses
 * Edge Runtime has lower latency and better streaming support
 */
export const runtime = "edge";

/**
 * POST /api/copilot - AG-UI streaming endpoint
 * Handles chat messages and streams responses using AG-UI protocol
 */
export async function POST(req: NextRequest) {
  try {
    const body = await req.json();

    // Log full request body for debugging
    console.log("[AG-UI] Full request body:", JSON.stringify(body, null, 2));

    const { threadId, messages } = body;

    // Log request for debugging (Vercel best practice: structured logging)
    console.log("[AG-UI] Parsed fields:", {
      threadId,
      messageCount: messages?.length || 0,
      bodyKeys: Object.keys(body),
    });

    // Validate required fields - make threadId optional for now to debug
    if (!threadId) {
      console.warn("[AG-UI] No threadId provided, using fallback");
      // return new Response(
      //   JSON.stringify({ error: "threadId is required" }),
      //   { status: 400, headers: { "Content-Type": "application/json" } }
      // );
    }

    // Use fallback threadId if not provided
    const actualThreadId = threadId || crypto.randomUUID();

    // TODO: Forward to FastAPI backend (ai-engine)
    // For now, return a simple response with proper AG-UI event types
    const encoder = new TextEncoder();
    const stream = new ReadableStream({
      async start(controller) {
        try {
          // AG-UI protocol events:
          // 1. RUN_STARTED - agent execution begins
          controller.enqueue(
            encoder.encode(
              `data: ${JSON.stringify({
                type: "RUN_STARTED",
                runId: crypto.randomUUID(),
                threadId: actualThreadId,
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
          const userMessage = messages?.[messages.length - 1]?.content || "Hello";
          const responseMessage = `Hello! I'm your Lev Haolam support assistant.\n\n` +
            `You said: "${userMessage}"\n\n` +
            `HITL forms and real agent integration coming soon...\n`;

          controller.enqueue(
            encoder.encode(
              `data: ${JSON.stringify({
                type: "TEXT_MESSAGE_CONTENT",
                content: responseMessage,
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
                threadId: actualThreadId,
              })}\n\n`
            )
          );

          controller.close();
        } catch (error) {
          console.error("[AG-UI] Stream error:", error);
          controller.error(error);
        }
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
    console.error("[AG-UI] POST error:", error);
    return new Response(
      JSON.stringify({ error: "Internal server error" }),
      { status: 500, headers: { "Content-Type": "application/json" } }
    );
  }
}
