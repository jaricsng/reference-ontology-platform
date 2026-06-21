"use client";

import { useCallback, useEffect, useMemo, useState } from "react";

type Bed = {
  bed_code: string;
  ward: string;
  occupied: boolean;
  occupant_id: string | null;
  occupant_name: string | null;
};

const ROLES = [
  { id: "bed_manager", label: "Carol — Bed Manager", scope: "all wards" },
  { id: "ward_nurse_a", label: "Alice — Ward Nurse", scope: "Ward A" },
  { id: "ward_nurse_b", label: "Bob — Ward Nurse", scope: "Ward B" },
];

type Banner = { kind: "ok" | "err"; text: string } | null;

export default function Dashboard() {
  const [role, setRole] = useState("bed_manager");
  const [beds, setBeds] = useState<Bed[]>([]);
  const [scope, setScope] = useState<string>("");
  const [loading, setLoading] = useState(false);
  const [banner, setBanner] = useState<Banner>(null);
  const [admitInputs, setAdmitInputs] = useState<Record<string, string>>({});

  const loadBeds = useCallback(async () => {
    setLoading(true);
    try {
      const r = await fetch(`/api/beds?role=${role}`, { cache: "no-store" });
      const data = await r.json();
      setBeds(data.beds ?? []);
      setScope(data.role_scope ?? "");
      if (!r.ok) setBanner({ kind: "err", text: data.error ?? "Failed to load beds" });
    } catch {
      setBanner({ kind: "err", text: "Could not reach the app server." });
    } finally {
      setLoading(false);
    }
  }, [role]);

  useEffect(() => { loadBeds(); }, [loadBeds]);

  const wards = useMemo(() => {
    const m = new Map<string, Bed[]>();
    for (const b of beds) {
      const arr = m.get(b.ward);
      if (arr) arr.push(b);
      else m.set(b.ward, [b]);
    }
    return [...m.entries()].sort(([a], [b]) => a.localeCompare(b));
  }, [beds]);

  async function admit(bed: Bed) {
    const patient_id = (admitInputs[bed.bed_code] ?? "").trim();
    if (!patient_id) { setBanner({ kind: "err", text: `Enter a patient id for ${bed.bed_code}.` }); return; }
    const r = await fetch("/api/admit", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ patient_id, bed_code: bed.bed_code, role }),
    });
    const data = await r.json();
    if (r.ok) {
      setBanner({ kind: "ok", text: `Admitted ${patient_id} to ${bed.bed_code}.` });
      setAdmitInputs((s) => ({ ...s, [bed.bed_code]: "" }));
    } else {
      const reasons = data?.detail?.reasons?.join(" ") ?? data?.detail ?? "Admit rejected.";
      setBanner({ kind: "err", text: `Rejected (${bed.bed_code}): ${reasons}` });
    }
    loadBeds();
  }

  async function discharge(bed: Bed) {
    const r = await fetch("/api/discharge", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ bed_code: bed.bed_code, role }),
    });
    const data = await r.json();
    setBanner(r.ok
      ? { kind: "ok", text: `Discharged from ${bed.bed_code}.` }
      : { kind: "err", text: data?.detail ?? "Discharge failed." });
    loadBeds();
  }

  return (
    <div className="wrap">
      <header className="top">
        <div>
          <h1>🏥 Hospital Bed &amp; Patient Flow</h1>
          <div className="sub">Live occupancy from the triplestore · guarded actions · role-scoped view</div>
        </div>
      </header>

      <div className="controls">
        <label htmlFor="role">Acting as</label>
        <select id="role" value={role} onChange={(e) => setRole(e.target.value)}>
          {ROLES.map((r) => <option key={r.id} value={r.id}>{r.label}</option>)}
        </select>
        <button className="secondary" onClick={loadBeds} disabled={loading}>
          {loading ? "Refreshing…" : "Refresh"}
        </button>
        <span className="scope-pill">visible scope: <b>{scope || "—"}</b></span>
      </div>

      {banner && <div className={`banner ${banner.kind}`}>{banner.text}</div>}

      <WardSummary wards={wards} />

      {wards.length === 0 && !loading && <p className="muted">No beds visible for this role.</p>}

      {wards.map(([ward, list]) => (
        <section className="ward-group" key={ward}>
          <h2>{ward} — {list.filter((b) => !b.occupied).length} free / {list.length} beds</h2>
          <div className="beds">
            {list.sort((a, b) => a.bed_code.localeCompare(b.bed_code)).map((bed) => (
              <div className={`bed ${bed.occupied ? "occ" : "free"}`} key={bed.bed_code}>
                <div className="code">{bed.bed_code}</div>
                <div className="state">{bed.occupied ? "Occupied" : "Free"}</div>
                {bed.occupied ? (
                  <>
                    <div className="occupant">{bed.occupant_id}</div>
                    <button className="discharge" onClick={() => discharge(bed)}>Discharge</button>
                  </>
                ) : (
                  <div className="admit-row">
                    <input
                      placeholder="patient id"
                      value={admitInputs[bed.bed_code] ?? ""}
                      onChange={(e) => setAdmitInputs((s) => ({ ...s, [bed.bed_code]: e.target.value }))}
                      onKeyDown={(e) => e.key === "Enter" && admit(bed)}
                    />
                    <button onClick={() => admit(bed)}>Admit</button>
                  </div>
                )}
              </div>
            ))}
          </div>
        </section>
      ))}

      <AgentBox role={role} />
    </div>
  );
}

function WardSummary({ wards }: { wards: [string, Bed[]][] }) {
  if (wards.length === 0) return null;
  return (
    <div className="summary">
      {wards.map(([ward, list]) => {
        const free = list.filter((b) => !b.occupied).length;
        const pct = list.length ? Math.round((free / list.length) * 100) : 0;
        return (
          <div className="card" key={ward}>
            <div className="ward">{ward}</div>
            <div className="nums">
              <span className="free">{free} free</span>
              <span className="occ">{list.length - free} occupied</span>
            </div>
            <div className="bar"><span style={{ width: `${pct}%` }} /></div>
          </div>
        );
      })}
    </div>
  );
}

function AgentBox({ role }: { role: string }) {
  const [q, setQ] = useState("How many beds are free in total?");
  const [busy, setBusy] = useState(false);
  const [res, setRes] = useState<{ answer?: string; scope?: string; sparql?: string } | null>(null);

  async function ask() {
    setBusy(true); setRes(null);
    try {
      const r = await fetch("/api/ask", {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question: q, role }),
      });
      setRes(await r.json());
    } catch {
      setRes({ answer: "Agent unreachable." });
    } finally { setBusy(false); }
  }

  return (
    <div className="agent">
      <h2>🤖 Ask the data</h2>
      <div className="hint">Natural-language question → SPARQL → answer, scoped to your role (M4, optional service).</div>
      <div className="ask-row">
        <input value={q} onChange={(e) => setQ(e.target.value)} onKeyDown={(e) => e.key === "Enter" && ask()} />
        <button onClick={ask} disabled={busy}>{busy ? "Thinking…" : "Ask"}</button>
      </div>
      {res && (
        <div className="answer">
          {res.scope && <div className="meta">scope: {res.scope}</div>}
          <div>{res.answer}</div>
          {res.sparql && <pre>{res.sparql}</pre>}
        </div>
      )}
    </div>
  );
}
