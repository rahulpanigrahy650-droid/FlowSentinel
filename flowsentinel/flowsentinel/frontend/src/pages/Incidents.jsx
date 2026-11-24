import React, { useEffect, useState } from "react";
import { api } from "../api.js";
import { SeverityBadge, StatusBadge, ErrorNote, CategoryLabel } from "../components/Common.jsx";
import { go, CATEGORIES, CATEGORY_LABELS, SEVERITIES, STATUS_LABELS, slaInfo, timeAgo } from "../util.js";

function NewIncidentForm({ onCancel }) {
  const [form, setForm] = useState({ title: "", description: "", reporter: "" });
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const set = (k) => (e) => setForm({ ...form, [k]: e.target.value });

  const submit = async (e) => {
    e.preventDefault();
    setBusy(true);
    setError("");
    try {
      const created = await api.createIncident(form);
      go(`/incidents/${created.id}`);
    } catch (err) {
      setError(err.message);
      setBusy(false);
    }
  };

  return (
    <form className="panel form" onSubmit={submit}>
      <h2>Report an incident</h2>
      <label>
        What is wrong?
        <input value={form.title} onChange={set("title")} placeholder="e.g. VPN disconnects every 10 minutes" required minLength={3} />
      </label>
      <label>
        Details
        <textarea
          value={form.description}
          onChange={set("description")}
          rows={5}
          placeholder="What happened, since when, who is affected, any error messages."
          required
          minLength={5}
        />
      </label>
      <label>
        Your name or team (optional)
        <input value={form.reporter} onChange={set("reporter")} />
      </label>
      <ErrorNote error={error} />
      <div className="actions">
        <button className="primary" disabled={busy}>{busy ? "Submitting…" : "Submit incident"}</button>
        <button type="button" onClick={onCancel}>Cancel</button>
      </div>
    </form>
  );
}

export default function Incidents() {
  const showNew = window.location.hash.includes("new=1");
  const [creating, setCreating] = useState(showNew);
  const [filters, setFilters] = useState({ status: "active", severity: "", category: "", q: "" });
  const [data, setData] = useState({ items: [], total: 0 });
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let live = true;
    setLoading(true);
    const timer = setTimeout(() => {
      api
        .listIncidents({ ...filters, limit: 100 })
        .then((d) => live && (setData(d), setError("")))
        .catch((e) => live && setError(e.message))
        .finally(() => live && setLoading(false));
    }, 200);
    return () => {
      live = false;
      clearTimeout(timer);
    };
  }, [filters]);

  const setF = (k) => (e) => setFilters({ ...filters, [k]: e.target.value });

  return (
    <>
      <header className="page-head">
        <h1>Incidents</h1>
        {!creating && <button className="primary" onClick={() => setCreating(true)}>Report incident</button>}
      </header>

      {creating && <NewIncidentForm onCancel={() => setCreating(false)} />}

      <div className="filters">
        <input type="search" placeholder="Search title or description" value={filters.q} onChange={setF("q")} aria-label="Search incidents" />
        <select value={filters.status} onChange={setF("status")} aria-label="Status">
          <option value="active">All open</option>
          {Object.entries(STATUS_LABELS).map(([v, l]) => <option key={v} value={v}>{l}</option>)}
        </select>
        <select value={filters.severity} onChange={setF("severity")} aria-label="Severity">
          <option value="">Any severity</option>
          {SEVERITIES.map((s) => <option key={s} value={s}>{s}</option>)}
        </select>
        <select value={filters.category} onChange={setF("category")} aria-label="Category">
          <option value="">Any category</option>
          {CATEGORIES.map((c) => <option key={c} value={c}>{CATEGORY_LABELS[c]}</option>)}
        </select>
      </div>

      <ErrorNote error={error} />
      <section className="panel flush">
        {loading && data.items.length === 0 ? (
          <p className="muted pad">Loading…</p>
        ) : data.items.length === 0 ? (
          <p className="muted pad">No incidents match these filters. Clear a filter or report a new incident.</p>
        ) : (
          <ul className="rows">
            {data.items.map((i) => {
              const sla = slaInfo(i);
              return (
                <li key={i.id} className={`row rail-${i.severity}`}>
                  <a href={`#/incidents/${i.id}`}>
                    <span className="row-title">
                      <span className="muted">#{i.id}</span> {i.title}
                      {i.analysis_status === "pending" && <span className="muted"> · analysing…</span>}
                    </span>
                    <span className="row-meta">
                      <SeverityBadge severity={i.severity} /> <StatusBadge status={i.status} />
                      <CategoryLabel category={i.category} />
                      <span className="muted">{i.assigned_team}</span>
                      <span className={sla.overdue ? "bad" : "muted"}>{sla.text}</span>
                      <span className="muted">{timeAgo(i.created_at)}</span>
                    </span>
                  </a>
                </li>
              );
            })}
          </ul>
        )}
      </section>
      <p className="muted small">{data.total} incident{data.total === 1 ? "" : "s"}</p>
    </>
  );
}
