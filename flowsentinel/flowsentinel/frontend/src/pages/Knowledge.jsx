import React, { useCallback, useEffect, useRef, useState } from "react";
import { api } from "../api.js";
import { ErrorNote } from "../components/Common.jsx";
import { formatDate, subHeading } from "../util.js";

export default function Knowledge() {
  const [docs, setDocs] = useState([]);
  const [error, setError] = useState("");
  const [query, setQuery] = useState("");
  const [results, setResults] = useState(null);
  const [form, setForm] = useState({ title: "", content: "" });
  const [busy, setBusy] = useState(false);
  const fileRef = useRef(null);

  const load = useCallback(() => api.listDocuments().then(setDocs).catch((e) => setError(e.message)), []);
  useEffect(() => {
    load();
  }, [load]);

  const guard = async (fn) => {
    setBusy(true);
    setError("");
    try {
      await fn();
      await load();
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  };

  const search = (e) => {
    e.preventDefault();
    if (query.trim().length < 2) return;
    guard(async () => setResults(await api.searchKnowledge(query.trim())));
  };

  const add = (e) => {
    e.preventDefault();
    guard(async () => {
      await api.addDocument({ title: form.title, content: form.content, source: "manual" });
      setForm({ title: "", content: "" });
    });
  };

  const upload = (e) => {
    const file = e.target.files && e.target.files[0];
    if (!file) return;
    guard(async () => {
      await api.uploadDocument(file);
      if (fileRef.current) fileRef.current.value = "";
    });
  };

  const remove = (doc) => {
    if (!window.confirm(`Delete "${doc.title}" and its ${doc.chunk_count} passages?`)) return;
    guard(() => api.deleteDocument(doc.id));
  };

  return (
    <>
      <header className="page-head">
        <h1>Knowledge base</h1>
      </header>
      <p className="muted lead">
        Runbooks and fixes the platform searches when an incident arrives. Documents are split into passages and indexed for semantic search.
      </p>
      <ErrorNote error={error} />

      <section className="panel">
        <h2>Try a search</h2>
        <form className="inline-form" onSubmit={search}>
          <input value={query} onChange={(e) => setQuery(e.target.value)} placeholder="Describe a problem, e.g. users locked out after password reset" aria-label="Search the knowledge base" />
          <button className="primary" disabled={busy}>Search</button>
        </form>
        {results && (
          results.length === 0 ? (
            <p className="muted">No passages found.</p>
          ) : (
            <ol className="sources">
              {results.map((p) => (
                <li key={p.chunk_id}>
                  <details>
                    <summary>
                      {p.title}
                      {subHeading(p.heading) && <span className="muted"> · {subHeading(p.heading)}</span>}
                      <span className="score" title="Similarity">
                        <span style={{ width: `${Math.min(100, Math.max(4, p.score * 200))}%` }} />
                      </span>
                    </summary>
                    <pre className="excerpt">{p.content}</pre>
                  </details>
                </li>
              ))}
            </ol>
          )
        )}
      </section>

      <div className="grid-2">
        <section className="panel">
          <h2>Add a document</h2>
          <form onSubmit={add} className="form">
            <label>
              Title
              <input value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })} required minLength={2} />
            </label>
            <label>
              Content (Markdown works well: use headings for sections)
              <textarea rows={7} value={form.content} onChange={(e) => setForm({ ...form, content: e.target.value })} required minLength={20} />
            </label>
            <div className="actions">
              <button className="primary" disabled={busy}>Add document</button>
              <label className="filebtn">
                Upload .md or .txt
                <input ref={fileRef} type="file" accept=".md,.txt,text/plain,text/markdown" onChange={upload} hidden />
              </label>
            </div>
          </form>
        </section>

        <section className="panel flush">
          <h2 className="pad-h">Documents ({docs.length})</h2>
          {docs.length === 0 ? (
            <p className="muted pad">The knowledge base is empty. Add a runbook to get suggested fixes.</p>
          ) : (
            <ul className="rows">
              {docs.map((d) => (
                <li key={d.id} className="row doc">
                  <div>
                    <span className="row-title">{d.title}</span>
                    <span className="row-meta muted small">{d.chunk_count} passages · {d.source} · {formatDate(d.created_at)}</span>
                  </div>
                  <button className="danger" disabled={busy} onClick={() => remove(d)}>Delete</button>
                </li>
              ))}
            </ul>
          )}
        </section>
      </div>
    </>
  );
}
