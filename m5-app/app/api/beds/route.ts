import { NextRequest, NextResponse } from "next/server";
import { ACTION_API, userForRole } from "@/lib/api";

// Role-scoped bed occupancy — proxies to the M2 API's /secure/beds, which
// consults the M3 OPA policy. The selected role becomes the X-User identity.
export async function GET(req: NextRequest) {
  const role = req.nextUrl.searchParams.get("role") ?? "bed_manager";
  try {
    const r = await fetch(`${ACTION_API}/secure/beds`, {
      headers: { "X-User": userForRole(role) },
      cache: "no-store",
    });
    const data = await r.json();
    return NextResponse.json(data, { status: r.status });
  } catch {
    return NextResponse.json(
      { error: "action API unreachable", beds: [] }, { status: 502 });
  }
}
