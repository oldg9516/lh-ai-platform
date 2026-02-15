/**
 * GET /api/copilot/info - Agent Registration Endpoint
 *
 * Returns metadata about available agents for CopilotKit runtime sync.
 * This endpoint is called by CopilotKit during initialization to discover
 * available agents and actions.
 *
 * Vercel best practice: Simple, focused API routes
 */

export async function GET() {
  const metadata = {
    agents: [
      {
        name: "support_agent",
        description: "Lev Haolam customer support assistant with HITL confirmations",
        type: "custom",
      },
    ],
    actions: [],
    sdkVersion: "1.51.3",
  };

  console.log("[AG-UI] /info endpoint called, returning:", metadata);

  return new Response(JSON.stringify(metadata), {
    status: 200,
    headers: {
      "Content-Type": "application/json",
      "Cache-Control": "no-cache", // Vercel best practice: disable cache for dynamic endpoints
    },
  });
}

/**
 * POST /api/copilot/info - Also support POST for compatibility
 * Some AG-UI implementations use POST instead of GET
 */
export async function POST() {
  return GET();
}
