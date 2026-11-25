import { useCallback, useEffect, useState } from "react";

const API_BASE = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";

const SEVERITIES = ["", "debug", "info", "warning", "error", "critical"];

export default function App() {
  const [events, setEvents] = useState([]);
  const [nextCursor, setNextCursor] = useState(null);
  const [stats, setStats] = useState([]);
  const [serviceFilter, setServiceFilter] = useState("");
  const [typeFilter, setTypeFilter] = useState("");
  const [severityFilter, setSeverityFilter] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const fetchStats = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/events/stats`);
      if (!res.ok) throw new Error(`Stats request failed (${res.status})`);
      setStats(await res.json());
    } catch (err) {
      setError(err.message);
    }
  }, []);

  const fetchEvents = useCallback(
    async (cursor = null, append = false) => {
      setLoading(true);
      setError("");
      try {
        const params = new URLSearchParams({ limit: "20" });
        if (serviceFilter.trim()) params.set("service_name", serviceFilter.trim());
        if (typeFilter.trim()) params.set("event_type", typeFilter.trim());
        if (severityFilter) params.set("severity", severityFilter);
        if (cursor) params.set("cursor", cursor);

        const res = await fetch(`${API_BASE}/events?${params.toString()}`);
        if (!res.ok) throw new Error(`Events request failed (${res.status})`);
        const data = await res.json();

        setEvents((prev) => (append ? [...prev, ...data.items] : data.items));
        setNextCursor(data.next_cursor);
      } catch (err) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    },
    [serviceFilter, typeFilter, severityFilter]
  );

  useEffect(() => {
    fetchEvents(null, false);
    fetchStats();
  }, [fetchEvents, fetchStats]);

  const handleRefresh = () => {
    fetchEvents(null, false);
    fetchStats();
  };

  return (
    <div className="container">
      <header className="header">
        <div>
          <h1>Event Log Dashboard</h1>
          <p className="subtitle">Append-only audit event feed</p>
        </div>
        <button className="btn" onClick={handleRefresh} disabled={loading}>
          Refresh
        </button>
      </header>

      {error && <div className="error-banner">{error}</div>}

      <section className="section">
        <h2>Event Stats</h2>
        {stats.length === 0 ? (
          <p className="muted">No events recorded yet.</p>
        ) : (
          <div className="stats-grid">
            {stats.map((item) => (
              <div
                key={`${item.service_name}-${item.event_type}`}
                className="stat-card"
              >
                <span className="stat-service">{item.service_name}</span>
                <span className="stat-type">{item.event_type}</span>
                <span className="stat-count">{item.count}</span>
              </div>
            ))}
          </div>
        )}
      </section>

      <section className="section">
        <h2>Event Feed</h2>
        <div className="filters">
          <input
            type="text"
            placeholder="Filter by service_name..."
            value={serviceFilter}
            onChange={(e) => setServiceFilter(e.target.value)}
          />
          <input
            type="text"
            placeholder="Filter by event_type..."
            value={typeFilter}
            onChange={(e) => setTypeFilter(e.target.value)}
          />
          <select
            value={severityFilter}
            onChange={(e) => setSeverityFilter(e.target.value)}
          >
            {SEVERITIES.map((sev) => (
              <option key={sev || "all"} value={sev}>
                {sev ? sev.toUpperCase() : "All severities"}
              </option>
            ))}
          </select>
        </div>

        {events.length === 0 && !loading ? (
          <p className="muted">No matching events found.</p>
        ) : (
          <div className="feed">
            {events.map((ev) => (
              <article key={ev.id} className="event-card">
                <div className="event-top">
                  <span className={`badge badge-${ev.severity}`}>
                    {ev.severity}
                  </span>
                  <strong>{ev.service_name}</strong>
                  <span className="dot">•</span>
                  <span>{ev.event_type}</span>
                  <span className="spacer" />
                  <time className="timestamp">
                    {new Date(ev.timestamp).toLocaleString()}
                  </time>
                </div>
                <div className="event-meta">
                  <span>Resource: {ev.resource_id}</span>
                  <span>ID: {ev.id}</span>
                </div>
                <pre className="payload">
                  {JSON.stringify(ev.payload, null, 2)}
                </pre>
              </article>
            ))}
          </div>
        )}

        {nextCursor && (
          <div className="load-more">
            <button
              className="btn"
              onClick={() => fetchEvents(nextCursor, true)}
              disabled={loading}
            >
              {loading ? "Loading..." : "Load More"}
            </button>
          </div>
        )}
      </section>
    </div>
  );
}
