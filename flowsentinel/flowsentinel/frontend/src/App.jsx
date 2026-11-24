import React, { useEffect, useState } from "react";
import Dashboard from "./pages/Dashboard.jsx";
import Incidents from "./pages/Incidents.jsx";
import IncidentDetail from "./pages/IncidentDetail.jsx";
import Knowledge from "./pages/Knowledge.jsx";
import { api } from "./api.js";

function useHashRoute() {
  const read = () => window.location.hash.replace(/^#/, "") || "/";
  const [route, setRoute] = useState(read);
  useEffect(() => {
    const onChange = () => setRoute(read());
    window.addEventListener("hashchange", onChange);
    return () => window.removeEventListener("hashchange", onChange);
  }, []);
  return route;
}

const NAV = [
  { path: "/", label: "Overview" },
  { path: "/incidents", label: "Incidents" },
  { path: "/knowledge", label: "Knowledge base" },
];

export default function App() {
  const route = useHashRoute();
  const [health, setHealth] = useState(null);

  useEffect(() => {
    api.health().then(setHealth).catch(() => setHealth({ status: "unreachable" }));
  }, []);

  let page;
  const detail = route.match(/^\/incidents\/(\d+)$/);
  if (detail) page = <IncidentDetail id={Number(detail[1])} />;
  else if (route.startsWith("/incidents")) page = <Incidents />;
  else if (route.startsWith("/knowledge")) page = <Knowledge />;
  else page = <Dashboard />;

  const active = (path) => (path === "/" ? route === "/" : route.startsWith(path));

  return (
    <div className="shell">
      <aside className="sidebar">
        <a className="brand" href="#/">FlowSentinel</a>
        <nav aria-label="Main">
          {NAV.map((item) => (
            <a key={item.path} href={`#${item.path}`} className={active(item.path) ? "nav-link current" : "nav-link"}>
              {item.label}
            </a>
          ))}
        </nav>
        <div className="sidebar-foot">
          {health && health.status === "ok" ? (
            <>
              <span className="dot ok" /> API online
              <div className="muted small">AI: {health.llm.startsWith("enabled") ? "language model" : "offline rules"}</div>
            </>
          ) : health ? (
            <>
              <span className="dot bad" /> API unreachable
            </>
          ) : null}
        </div>
      </aside>
      <main className="main">{page}</main>
    </div>
  );
}
