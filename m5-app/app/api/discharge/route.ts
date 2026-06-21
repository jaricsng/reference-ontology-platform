import { NextRequest, NextResponse } from "next/server";
import { ACTION_API, userForRole } from "@/lib/api";

export async function POST(req: NextRequest) {
  const body = await req.json();
  const actor = userForRole(body.role ?? "");
  try {
    const r = await fetch(`${ACTION_API}/discharge`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ bed_code: body.bed_code, actor }),
    });
    const data = await r.json();
    return NextResponse.json(data, { status: r.status });
  } catch {
    return NextResponse.json({ detail: "action API unreachable" }, { status: 502 });
  }
}
