/**
 * Proxy for HITL tool execution.
 *
 * Frontend forms call this endpoint after user approval.
 * It forwards the request to the FastAPI backend which
 * executes the actual tool and saves an audit log.
 */

import { NextRequest, NextResponse } from "next/server";

function getBackendUrl(): string {
  return process.env.NEXT_PUBLIC_API_URL || "http://ai-engine:8000";
}

export async function POST(req: NextRequest) {
  try {
    const body = await req.json();

    const res = await fetch(`${getBackendUrl()}/api/copilot/execute-tool`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });

    const data = await res.json();
    return NextResponse.json(data);
  } catch (error) {
    return NextResponse.json(
      { status: "error", message: String(error) },
      { status: 500 },
    );
  }
}
