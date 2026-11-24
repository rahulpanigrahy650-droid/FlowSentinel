import React from "react";
import { CATEGORY_LABELS, STATUS_LABELS } from "../util.js";

export function SeverityBadge({ severity }) {
  return <span className={`badge sev-${severity}`}>{severity}</span>;
}

export function StatusBadge({ status }) {
  return <span className={`badge status-${status}`}>{STATUS_LABELS[status] || status}</span>;
}

export function CategoryLabel({ category }) {
  return <span className="muted">{CATEGORY_LABELS[category] || category}</span>;
}

export function ErrorNote({ error }) {
  return error ? <p className="error" role="alert">{error}</p> : null;
}

// Minimal, safe renderer for the Markdown the resolver produces (lists, **bold**, `code`, _italic_, [n]).
function inline(text, keyBase) {
  return text.split(/(\*\*[^*]+\*\*|`[^`]+`|_[^_]+_|\[\d+\])/g).filter(Boolean).map((part, i) => {
    const key = `${keyBase}-${i}`;
    if (part.startsWith("**")) return <strong key={key}>{part.slice(2, -2)}</strong>;
    if (part.startsWith("`")) return <code key={key}>{part.slice(1, -1)}</code>;
    if (part.startsWith("_") && part.endsWith("_") && part.length > 2) return <em key={key}>{part.slice(1, -1)}</em>;
    if (/^\[\d+\]$/.test(part)) return <sup key={key} className="cite">{part}</sup>;
    return <React.Fragment key={key}>{part}</React.Fragment>;
  });
}

export function RichText({ text }) {
  const blocks = [];
  let list = null;
  const flush = () => {
    if (list) {
      blocks.push(list);
      list = null;
    }
  };
  (text || "").split("\n").forEach((raw) => {
    const line = raw.trim();
    const ordered = line.match(/^\d+[.)]\s+(.*)/);
    const bullet = line.match(/^[-*]\s+(.*)/);
    if (ordered || bullet) {
      const kind = ordered ? "ol" : "ul";
      if (!list || list.kind !== kind) {
        flush();
        list = { kind, items: [] };
      }
      list.items.push((ordered || bullet)[1]);
    } else {
      flush();
      if (line) blocks.push({ kind: "p", text: line });
    }
  });
  flush();
  return (
    <div className="rich">
      {blocks.map((b, i) => {
        if (b.kind === "p") return <p key={i}>{inline(b.text, `p${i}`)}</p>;
        const Tag = b.kind;
        return (
          <Tag key={i}>
            {b.items.map((item, j) => (
              <li key={j}>{inline(item, `l${i}-${j}`)}</li>
            ))}
          </Tag>
        );
      })}
    </div>
  );
}
