import React, { useCallback, useEffect, useState } from "react";
import { api } from "../api.js";
import { SeverityBadge, StatusBadge, ErrorNote, RichText } from "../components/Common.jsx";
import {
  CATEGORIES, CATEGORY_LABELS, NODE_LABELS, ROUTE_LABELS, SEVERITIES, STATUS_LABELS,
  formatDate, slaInfo, subHeading,
} from "../util.js";

function Trace({ trace }) {
  if (!trace || trace.length === 0) return <p className="muted">The workflow has not run yet.</p>;
  return (
    <ol className="trace">
      {trace.map((step, i) => (
        <li key={i}>
          <strong>{NODE_LABELS[step.node] || step.node}</strong>
          <span className="muted">{step.detail}</span>
        </li>
      ))}
    </ol>
  );
}

function Sources({ passages }) {
  if (!passages || passages.length === 0) return <p className="muted">No documentation matched this incident.</p>;
  return (
    <ol className="sources">
      {passages.map((p, i) => (
        <li key={p.chunk_id}>
          <details>
            <summary>
              <span className="cite">[{i + 1}]</span> {p.title}
              {subHeading(p.heading) && <span className="muted"> · {subHeading(p.heading)}</span>}
              <span className="score" title="Similarity to the incident">
                <span style={{ width: `${Math.min(100, Math.max(4, p.score * 200))}%` }} />
              </span>
            </summary>
            <pre className="excerpt">{p.content}</pre>
          </details>
        </li>
      ))}
    </ol>
  );
}

export default function IncidentDetail({ id }) {
  const [inc, setInc] = useState(null);
  const [error, setError] = useState("");
  const [notes, setNotes] = useState("");
  const [saveToKb, setSaveToKb] = useState(true);
  const [busy, setBusy] = useState(false);

  const load = useCallback(
    () =>
      api
        .getIncident(id)
        .then((d) => {
          setInc(d);
          setError("");
        })
        .catch((e) => setError(e.message)),
    [id]
  );

  useEffect(() => {
    setInc(null);
    load();
  }, [load]);

  // Analysis runs in the background; poll until the workflow has finished.
  useEffect(() => {
    if (!inc || inc.analysis_status !== "pending") return undefined;
    const timer = setTimeout(load, 1500);
    return () => clearTimeout(timer);
  }, [inc, load]);

  const run = async (fn) => {
    setBusy(true);
    try {
      await fn();
      await load();
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  };

  if (error && !inc) return <><a href="#/incidents">← All incidents</a><ErrorNote error={error} /></>;
  if (!inc) return <p className="muted">Loading…</p>;

  const sla = slaInfo(inc);
  const analysis = inc.analysis || {};
  const pending = inc.analysis_status === "pending";
  const resolved = inc.status === "resolved";

  return (
    <>
      <a href="#/incidents" className="back">← All incidents</a>
      <header className={`detail-head rail-${inc.severity}`}>
        <h1>{inc.title}</h1>
        <div className="row-meta">
          <SeverityBadge severity={inc.severity} /> <StatusBadge status={inc.status} />
          <span className="muted">#{inc.id}</span>
          <span className="muted">{CATEGORY_LABELS[inc.category] || inc.category}</span>
          {inc.assigned_team && <span className="muted">{inc.assigned_team}</span>}
          <span className={sla.overdue ? "bad" : "muted"}>{sla.text}</span>
        </div>
      </header>
      <ErrorNote error={error} />

      <div className="detail-grid">
        <div className="stack">
          <section className="panel">
            <h2>Report</h2>
            <p className="prewrap">{inc.description}</p>
            <p className="muted small">
              {inc.reporter ? `${inc.reporter} · ` : ""}reported {formatDate(inc.created_at)}
            </p>
            {inc.summary && !pending && <p className="summary"><strong>Summary:</strong> {inc.summary}</p>}
          </section>

          <section className="panel">
            <h2>Suggested resolution</h2>
            {pending ? (
              <p className="muted">Analysing the incident and searching the knowledge base…</p>
            ) : inc.analysis_status === "failed" ? (
              <p className="error">Automatic analysis failed. You can retry it below.</p>
            ) : (
              <>
                {inc.route && <p className="route">{ROUTE_LABELS[inc.route]}</p>}
                <RichText text={inc.suggested_resolution} />
                <div className="actions">
                  <span className="muted small">Was this useful?</span>
                  <button disabled={busy} className={inc.feedback === "helpful" ? "chosen" : ""} onClick={() => run(() => api.feedback(id, true))}>Yes</button>
                  <button disabled={busy} className={inc.feedback === "not_helpful" ? "chosen" : ""} onClick={() => run(() => api.feedback(id, false))}>No</button>
                  <button disabled={busy} onClick={() => run(() => api.reanalyze(id))}>Re-run analysis</button>
                </div>
              </>
            )}
          </section>

          <section className="panel">
            <h2>Documentation used</h2>
            <Sources passages={analysis.passages} />
          </section>

          {resolved ? (
            <section className="panel">
              <h2>Resolution</h2>
              <p className="prewrap">{inc.resolution_notes || "Resolved without notes."}</p>
              <div className="actions">
                <button disabled={busy} onClick={() => run(() => api.updateIncident(id, { status: "open" }))}>Reopen</button>
              </div>
            </section>
          ) : (
            <section className="panel form">
              <h2>Resolve</h2>
              <label>
                What fixed it?
                <textarea rows={4} value={notes} onChange={(e) => setNotes(e.target.value)} placeholder="Steps taken, root cause, anything the next engineer should know." />
              </label>
              <label className="check">
                <input type="checkbox" checked={saveToKb} onChange={(e) => setSaveToKb(e.target.checked)} />
                Add these notes to the knowledge base
              </label>
              <div className="actions">
                <button
                  className="primary"
                  disabled={busy}
                  onClick={() => run(() => api.updateIncident(id, { status: "resolved", resolution_notes: notes, save_to_kb: saveToKb }))}
                >
                  Mark resolved
                </button>
              </div>
            </section>
          )}
        </div>

        <div className="stack">
          <section className="panel form">
            <h2>Triage</h2>
            <label>
              Status
              <select value={inc.status} disabled={busy} onChange={(e) => run(() => api.updateIncident(id, { status: e.target.value }))}>
                {Object.entries(STATUS_LABELS).map(([v, l]) => <option key={v} value={v}>{l}</option>)}
              </select>
            </label>
            <label>
              Severity{inc.severity_overridden ? " (set by an agent)" : ""}
              <select value={inc.severity} disabled={busy} onChange={(e) => run(() => api.updateIncident(id, { severity: e.target.value }))}>
                {SEVERITIES.map((s) => <option key={s} value={s}>{s}</option>)}
              </select>
            </label>
            <label>
              Category
              <select value={inc.category} disabled={busy} onChange={(e) => run(() => api.updateIncident(id, { category: e.target.value }))}>
                {CATEGORIES.map((c) => <option key={c} value={c}>{CATEGORY_LABELS[c]}</option>)}
              </select>
            </label>
            {analysis.rationale && analysis.rationale.length > 0 && (
              <div>
                <p className="muted small">Why this severity and category</p>
                <ul className="plain">
                  {analysis.rationale.map((r, i) => <li key={i} className="small">{r}</li>)}
                </ul>
                <p className="muted small">Confidence {Math.round(inc.confidence * 100)}% · {analysis.llm_used ? "language model" : "rule-based"}</p>
              </div>
            )}
          </section>

          <section className="panel">
            <h2>Workflow</h2>
            <Trace trace={analysis.trace} />
          </section>

          <section className="panel">
            <h2>Activity</h2>
            <ul className="plain activity">
              {[...(inc.events || [])].reverse().map((e) => (
                <li key={e.id}>
                  <span>{e.message}</span>
                  <span className="muted small">{formatDate(e.created_at)}</span>
                </li>
              ))}
            </ul>
          </section>
        </div>
      </div>
    </>
  );
}
