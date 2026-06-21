import { NextRequest, NextResponse } from "next/server";
import { AGENT_API, userForRole } from "@/lib/api";

// Proxies a natural-language question to the M4 agent service. The agent
// applies the same security scope for the selected role.
export async function POST(req: NextRequest) {
  const body = await req.json();
  try {
    const r = await fetch(`${AGENT_API}/ask`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question: body.question, user: userForRole(body.role ?? "") }),
    });
    const data = await r.json();
    return NextResponse.json(data, { status: r.status });
  } catch {
    return NextResponse.json(
      { answer: "The AI agent service is not running (optional). Start m4-ai/server.py to enable it." },
      { status: 502 },
    );
  }
}
