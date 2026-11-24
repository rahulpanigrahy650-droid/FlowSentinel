import React, { useEffect, useState } from "react";
import { api } from "../api.js";
import { SeverityBadge, StatusBadge, ErrorNote, CategoryLabel } from "../components/Common.jsx";
import { go, CATEGORY_LABELS, SEVERITIES, severityRank, slaInfo } from "../util.js";

export default function Dashboard() {
  const [summary, setSummary] = useState(null);
  const [active, setActive] = useState([]);
  const [error, setError] = useState("");

  useEffect(() => {
    let live = true;
    const load = () =>
      Promise.all([api.summary(), api.listIncidents({ status: "active", limit: 100 })])
        .then(([s, list]) => {
          if (!live) return;
          setSummary(s);
          setActive(list.items);
        })
        .catch((e) => live && setError(e.message));
    load();
    const timer = setInterval(load, 15000);
    return () => {
      live = false;
      clearInterval(timer);
    };
  }, []);

  if (error) return <ErrorNote error={error} />;
  if (!summary) return <p className="muted">Loading…</p>;

  const bySev = summary.active_by_severity;
  const totalActive = summary.totals.active;
  const attention = [...active]
    .sort((a, b) => severityRank(a.severity) - severityRank(b.severity) || new Date(b.created_at) - new Date(a.created_at))
    .slice(0, 6);
  const maxDaily = Math.max(1, ...summary.daily.map((d) => d.count));
  const maxCat = Math.max(1, ...summary.by_category.map((c) => c.count));

  return (
    <>
      <header className="page-head">
        <h1>{totalActive === 0 ? "No open incidents" : `${totalActive} open incident${totalActive === 1 ? "" : "s"}`}</h1>
        <button className="primary" onClick={() => go("/incidents?new=1")}>Report incident</button>
      </header>

      <section className="panel">
        <div className="sevbar" role="img" aria-label="Open incidents by severity">
          {totalActive === 0 ? (
            <div className="sevbar-seg empty" style={{ flexGrow: 1 }} />
          ) : (
            SEVERITIES.filter((s) => bySev[s] > 0).map((s) => (
              <div key={s} className={`sevbar-seg bg-${s}`} style={{ flexGrow: bySev[s] }}>
                {bySev[s]} {s}
              </div>
            ))
          )}
        </div>
        <dl className="facts">
          <div><dt>Escalated</dt><dd>{summary.totals.escalated}</dd></div>
          <div><dt>SLA breached</dt><dd className={summary.sla_breached ? "bad" : ""}>{summary.sla_breached}</dd></div>
          <div><dt>Avg. time to resolve</dt><dd>{summary.mttr_hours == null ? "–" : `${summary.mttr_hours} h`}</dd></div>
          <div><dt>Fixes suggested automatically</dt><dd>{summary.suggestion_rate == null ? "–" : `${Math.round(summary.suggestion_rate * 100)}%`}</dd></div>
          <div><dt>Marked helpful</dt><dd>{summary.helpful_rate == null ? "–" : `${Math.round(summary.helpful_rate * 100)}%`}</dd></div>
        </dl>
      </section>

      <div className="grid-2">
        <section className="panel">
          <h2>Needs attention</h2>
          {attention.length === 0 ? (
            <p className="muted">Nothing is waiting. New incidents appear here as they are triaged.</p>
          ) : (
            <ul className="rows">
              {attention.map((i) => (
                <li key={i.id} className={`row rail-${i.severity}`}>
                  <a href={`#/incidents/${i.id}`}>
                    <span className="row-title">{i.title}</span>
                    <span className="row-meta">
                      <SeverityBadge severity={i.severity} /> <StatusBadge status={i.status} />
                      <CategoryLabel category={i.category} />
                      <span className={slaInfo(i).overdue ? "bad" : "muted"}>{slaInfo(i).text}</span>
                    </span>
                  </a>
                </li>
              ))}
            </ul>
          )}
        </section>

        <div className="stack">
          <section className="panel">
            <h2>Reported in the last 14 days</h2>
            <div className="spark" role="img" aria-label="Incidents per day">
              {summary.daily.map((d) => (
                <div key={d.date} className="spark-col" title={`${d.date}: ${d.count}`}>
                  <div className="spark-bar" style={{ height: `${(d.count / maxDaily) * 100}%` }} />
                </div>
              ))}
            </div>
          </section>
          <section className="panel">
            <h2>By category</h2>
            {summary.by_category.length === 0 ? (
              <p className="muted">No data yet.</p>
            ) : (
              <ul className="bars">
                {summary.by_category.map((c) => (
                  <li key={c.category}>
                    <span>{CATEGORY_LABELS[c.category] || c.category}</span>
                    <div className="bar"><div style={{ width: `${(c.count / maxCat) * 100}%` }} /></div>
                    <span className="muted">{c.count}</span>
                  </li>
                ))}
              </ul>
            )}
          </section>
        </div>
      </div>
      <p className="muted small">Refreshes every 15 seconds</p>
    </>
  );
}
