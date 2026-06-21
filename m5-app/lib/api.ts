// Server-side only: backend URLs and the role -> identity mapping.
// The browser never sees these; route handlers call them server-side.

export const ACTION_API = process.env.ACTION_API ?? "http://127.0.0.1:8000";
export const AGENT_API = process.env.AGENT_API ?? "http://127.0.0.1:8002";

export type Role = "bed_manager" | "ward_nurse_a" | "ward_nurse_b";

export const ROLES: { id: Role; label: string; scope: string }[] = [
  { id: "bed_manager", label: "Carol — Bed Manager", scope: "all wards" },
  { id: "ward_nurse_a", label: "Alice — Ward Nurse", scope: "Ward A" },
  { id: "ward_nurse_b", label: "Bob — Ward Nurse", scope: "Ward B" },
];

const ROLE_TO_USER: Record<string, string> = {
  bed_manager: "manager_carol",
  ward_nurse_a: "nurse_alice",
  ward_nurse_b: "nurse_bob",
};

export function userForRole(role: string): string {
  return ROLE_TO_USER[role] ?? "unknown";
}

export type Bed = {
  bed_code: string;
  ward: string;
  occupied: boolean;
  occupant_id: string | null;
  occupant_name: string | null;
};
