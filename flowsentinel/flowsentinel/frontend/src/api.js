const BASE = import.meta.env.VITE_API_URL || "";

async function request(path, options = {}) {
  const isForm = options.body instanceof FormData;
  const res = await fetch(`${BASE}/api${path}`, {
    ...options,
    headers: isForm ? {} : { "Content-Type": "application/json" },
  });
  if (!res.ok) {
    let message = res.statusText;
    try {
      const body = await res.json();
      if (typeof body.detail === "string") message = body.detail;
      else if (Array.isArray(body.detail)) message = body.detail.map((d) => d.msg).join("; ");
    } catch (_) {
      /* keep status text */
    }
    throw new Error(message || `Request failed (${res.status})`);
  }
  return res.status === 204 ? null : res.json();
}

const json = (method, body) => ({ method, body: JSON.stringify(body) });

export const api = {
  health: () => request("/health"),
  summary: () => request("/analytics/summary"),
  listIncidents: (params = {}) => {
    const qs = new URLSearchParams(Object.entries(params).filter(([, v]) => v)).toString();
    return request(`/incidents${qs ? `?${qs}` : ""}`);
  },
  getIncident: (id) => request(`/incidents/${id}`),
  createIncident: (data) => request("/incidents", json("POST", data)),
  updateIncident: (id, patch) => request(`/incidents/${id}`, json("PATCH", patch)),
  reanalyze: (id) => request(`/incidents/${id}/reanalyze`, { method: "POST" }),
  feedback: (id, helpful) => request(`/incidents/${id}/feedback`, json("POST", { helpful, note: "" })),
  listDocuments: () => request("/knowledge/documents"),
  addDocument: (data) => request("/knowledge/documents", json("POST", data)),
  uploadDocument: (file) => {
    const form = new FormData();
    form.append("file", file);
    return request("/knowledge/documents/upload", { method: "POST", body: form });
  },
  deleteDocument: (id) => request(`/knowledge/documents/${id}`, { method: "DELETE" }),
  searchKnowledge: (query) => request("/knowledge/search", json("POST", { query, k: 5 })),
};
