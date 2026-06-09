import { useEffect, useMemo, useState } from "react";
import "./App.css";

const API_BASE = "http://localhost:8000";

const emptyDashboard = {
  total_meetings: 0,
  open_escalations: 0,
  open_action_items: 0,
  high_severity_risks: 0,
};

function App() {
  const [dashboard, setDashboard] = useState(emptyDashboard);
  const [meetingText, setMeetingText] = useState("");
  const [analysis, setAnalysis] = useState(null);
  const [question, setQuestion] = useState("");
  const [queryAnswer, setQueryAnswer] = useState(null);
  const [loadingAnalysis, setLoadingAnalysis] = useState(false);
  const [loadingQuery, setLoadingQuery] = useState(false);
  const [error, setError] = useState("");

  const kpis = useMemo(
    () => [
      { label: "Total Meetings", value: dashboard.total_meetings },
      { label: "Open Escalations", value: dashboard.open_escalations },
      { label: "Open Action Items", value: dashboard.open_action_items },
      { label: "High Severity Risks", value: dashboard.high_severity_risks },
    ],
    [dashboard],
  );

  const loadDashboard = async () => {
    const response = await fetch(`${API_BASE}/dashboard`);
    if (!response.ok) throw new Error("Unable to load dashboard");
    setDashboard(await response.json());
  };

  useEffect(() => {
    loadDashboard().catch((err) => setError(err.message));
  }, []);

  const analyzeMeeting = async () => {
    if (!meetingText.trim()) {
      setError("Paste meeting content before analyzing.");
      return;
    }

    setLoadingAnalysis(true);
    setError("");

    try {
      const response = await fetch(`${API_BASE}/analyze`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text: meetingText }),
      });

      const data = await response.json();
      if (!response.ok) {
        throw new Error(data?.detail?.message || data?.detail || "Analysis failed");
      }

      setAnalysis(data);
      await loadDashboard();
    } catch (err) {
      setError(err.message);
    } finally {
      setLoadingAnalysis(false);
    }
  };

  const askQuestion = async () => {
    if (!question.trim()) {
      setError("Enter a question for the query engine.");
      return;
    }

    setLoadingQuery(true);
    setError("");

    try {
      const response = await fetch(`${API_BASE}/query`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question }),
      });

      const data = await response.json();
      if (!response.ok) throw new Error(data?.detail || "Query failed");
      setQueryAnswer(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoadingQuery(false);
    }
  };

  return (
    <main className="app-shell">
      <section className="page-header">
        <div>
          <p className="eyebrow"></p>
          <h1>Meeting Intelligence & Escalation Tracking System </h1>
        </div>
      </section>

      {error && <div className="alert">{error}</div>}

      <section className="kpi-grid" aria-label="Dashboard Cards">
        {kpis.map((kpi) => (
          <article className="kpi-card" key={kpi.label}>
            <span>{kpi.label}</span>
            <strong>{kpi.value}</strong>
          </article>
        ))}
      </section>

      <section className="panel">
        <div className="section-heading">
          <p className="eyebrow">Meeting Analysis</p>
          <h2>Transform discussion into structured intelligence</h2>
        </div>
        <textarea
          className="meeting-input"
          rows="12"
          placeholder="Paste meeting summaries, transcripts, or free-form notes here..."
          value={meetingText}
          onChange={(event) => setMeetingText(event.target.value)}
        />
        <div className="actions">
          <button onClick={analyzeMeeting} disabled={loadingAnalysis}>
            {loadingAnalysis ? "Analyzing..." : "Analyze Meeting"}
          </button>
        </div>
      </section>

      {analysis && (
        <section className="results">
          <div className="section-heading">
            <p className="eyebrow">Analysis Results</p>
            <h2>{analysis.meeting_title || "Meeting Intelligence"}</h2>
            <p className="summary-text">{analysis.summary || "No summary extracted."}</p>
          </div>

          <div className="result-grid">
            <DataCard
              title="Projects"
              items={analysis.projects}
              columns={[
                ["Name", "name"],
                ["Status", "status"],
              ]}
              emptyText="No projects found."
            />
            <DataCard
              title="Action Items"
              items={analysis.action_items}
              columns={[
                ["Task", "task"],
                ["Owner", "owner"],
                ["Deadline", "deadline"],
              ]}
              emptyText="No action items found."
            />
            <DataCard
              title="Escalations"
              items={analysis.escalations}
              columns={[
                ["Issue", "issue"],
                ["Raised By", "raised_by"],
              ]}
              emptyText="No escalations found."
            />
            <DataCard
              title="Risks"
              items={analysis.risks}
              columns={[
                ["Description", "description"],
                ["Severity", "severity"],
              ]}
              emptyText="No risks found."
            />
          </div>
        </section>
      )}

      <section className="panel">
        <div className="section-heading">
          <p className="eyebrow">Organizational Query Engine</p>
          <h2>Ask about risks, owners, escalations, tasks, or projects</h2>
        </div>
        <div className="query-row">
          <input
            placeholder="Ask a question about organizational intelligence..."
            value={question}
            onChange={(event) => setQuestion(event.target.value)}
            onKeyDown={(event) => {
              if (event.key === "Enter") askQuestion();
            }}
          />
          <button onClick={askQuestion} disabled={loadingQuery}>
            {loadingQuery ? "Asking..." : "Ask"}
          </button>
        </div>

        {queryAnswer && <QueryResults answer={queryAnswer} />}
      </section>
    </main>
  );
}

function DataCard({ title, items = [], columns, emptyText }) {
  return (
    <article className="data-card">
      <div className="card-title">
        <h3>{title}</h3>
        <span>{items.length}</span>
      </div>
      {items.length === 0 ? (
        <p className="empty-state">{emptyText}</p>
      ) : (
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                {columns.map(([label]) => (
                  <th key={label}>{label}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {items.map((item, index) => (
                <tr key={`${title}-${index}`}>
                  {columns.map(([label, key]) => (
                    <td key={label}>{item?.[key] || "Unassigned"}</td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </article>
  );
}

function QueryResults({ answer }) {
  const columnsByType = {
    risks: [
      ["Description", "description"],
      ["Severity", "severity"],
      ["Meeting", "meeting_title"],
    ],
    escalations: [
      ["Issue", "issue"],
      ["Raised By", "raised_by"],
      ["Status", "status"],
      ["Meeting", "meeting_title"],
    ],
    tasks: [
      ["Task", "task"],
      ["Owner", "owner"],
      ["Deadline", "deadline"],
      ["Status", "status"],
    ],
    projects: [
      ["Name", "name"],
      ["Status", "status"],
      ["Meeting", "meeting_title"],
    ],
    meetings: [
      ["Title", "title"],
      ["Summary", "summary"],
      ["Analyzed", "analyzed_at"],
    ],
  };

  const columns = columnsByType[answer.type] || columnsByType.meetings;

  return (
    <div className="answer-panel">
      <div className="card-title">
        <h3>Answer</h3>
        <span>{answer.count} results</span>
      </div>
      {answer.message && <p className="summary-text">{answer.message}</p>}
      <DataCard
        title={answer.question}
        items={answer.results || []}
        columns={columns}
        emptyText="No matching records found."
      />
    </div>
  );
}

export default App;
