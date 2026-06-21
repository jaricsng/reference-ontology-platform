import { NextRequest, NextResponse } from "next/server";
import { ACTION_API, userForRole } from "@/lib/api";

// Proxies an admit to the M2 action API. A 409 (rule violation) is passed
// straight through so the UI can show the rejection gracefully.
export async function POST(req: NextRequest) {
  const body = await req.json();
  const actor = userForRole(body.role ?? "");
  try {
    const r = await fetch(`${ACTION_API}/admit`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        patient_id: body.patient_id,
        bed_code: body.bed_code,
        patient_name: body.patient_name,
        actor,
      }),
    });
    const data = await r.json();
    return NextResponse.json(data, { status: r.status });
  } catch {
    return NextResponse.json({ detail: "action API unreachable" }, { status: 502 });
  }
}
