/**
 * GET /api/copilot/info - Agent Registration Endpoint
 *
 * Returns metadata about available agents for CopilotKit runtime sync.
 * This endpoint is called by CopilotKit during initialization to discover
 * available agents and actions.
 *
 * Vercel best practice: Simple, focused API routes
 */

const CORS_HEADERS = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
  "Access-Control-Allow-Headers": "Content-Type, Authorization",
};

export async function OPTIONS() {
  return new Response(null, {
    status: 204,
    headers: CORS_HEADERS,
  });
}

export async function GET() {
  const metadata = {
    agents: [
      {
        name: "support_agent",
        description: "Lev Haolam customer support assistant with HITL confirmations",
      },
    ],
    actions: [],
    sdkVersion: "1.51.3",
  };

  console.log("[AG-UI] /info GET endpoint called");
  console.log("[AG-UI] Returning metadata:", JSON.stringify(metadata, null, 2));

  return new Response(JSON.stringify(metadata), {
    status: 200,
    headers: {
      "Content-Type": "application/json",
      "Cache-Control": "no-cache, no-store, must-revalidate",
      "Pragma": "no-cache",
      "Expires": "0",
      ...CORS_HEADERS,
    },
  });
}

/**
 * POST /api/copilot/info - Also support POST for compatibility
 * Some AG-UI implementations use POST instead of GET
 */
export async function POST() {
  console.log("[AG-UI] /info POST endpoint called");
  return GET();
}
