import json
import os
import re
import sqlite3
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from groq import Groq
from database import DB_NAME, init_db
from models import AnalyzeRequest, QueryRequest

app = FastAPI(title="Meeting Intelligence System")


def load_local_env(path: str = ".env"):
    if not os.path.exists(path):
        return

    with open(path, "r", encoding="utf-8") as env_file:
        for line in env_file:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


load_local_env()

api_key = os.getenv("GROQ_API_KEY")
groq_model = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")

client = Groq(api_key=api_key) if api_key else None

init_db()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_conn():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn


def rows_to_dicts(rows):
    return [dict(row) for row in rows]


def clean_llm_json(text: str) -> dict[str, Any]:
    cleaned = text.strip().replace("```json", "").replace("```", "").strip()
    match = re.search(r"\{.*\}", cleaned, re.DOTALL)
    if match:
        cleaned = match.group(0)
    return json.loads(cleaned)


def run_groq_json(prompt: str) -> dict[str, Any]:
    if client is None:
        raise HTTPException(status_code=500, detail="GROQ_API_KEY is not configured")

    response = client.chat.completions.create(
        model=groq_model,
        messages=[
            {
                "role": "system",
                "content": "You extract enterprise meeting intelligence and return only valid JSON.",
            },
            {
                "role": "user",
                "content": prompt,
            },
        ],
        temperature=0,
        response_format={"type": "json_object"},
    )

    content = response.choices[0].message.content or "{}"
    return clean_llm_json(content)


def as_list(value):
    return value if isinstance(value, list) else []


def normalize_extraction(extracted: dict[str, Any]) -> dict[str, Any]:
    return {
        "meeting_title": extracted.get("meeting_title") or extracted.get("title") or "Untitled Meeting",
        "summary": extracted.get("summary") or "",
        "projects": as_list(extracted.get("projects")),
        "action_items": as_list(extracted.get("action_items")),
        "escalations": as_list(extracted.get("escalations")),
        "risks": as_list(extracted.get("risks")),
    }


def store_extraction(raw_text: str, extracted: dict[str, Any]) -> int:
    conn = get_conn()
    cursor = conn.cursor()

    cursor.execute(
        """
        INSERT INTO meetings(title, summary, raw_text, analyzed_at)
        VALUES (?, ?, ?, CURRENT_TIMESTAMP)
        """,
        (extracted["meeting_title"], extracted["summary"], raw_text),
    )
    meeting_id = cursor.lastrowid

    for project in extracted["projects"]:
        cursor.execute(
            "INSERT INTO projects(meeting_id, name, status) VALUES (?, ?, ?)",
            (
                meeting_id,
                project.get("name", ""),
                project.get("status", "unknown"),
            ),
        )

    for item in extracted["action_items"]:
        cursor.execute(
            """
            INSERT INTO action_items(meeting_id, task, owner, deadline, status)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                meeting_id,
                item.get("task", ""),
                item.get("owner", ""),
                item.get("deadline", ""),
                item.get("status", "open") or "open",
            ),
        )

    for escalation in extracted["escalations"]:
        cursor.execute(
            """
            INSERT INTO escalations(meeting_id, issue, raised_by, status)
            VALUES (?, ?, ?, ?)
            """,
            (
                meeting_id,
                escalation.get("issue", ""),
                escalation.get("raised_by", ""),
                escalation.get("status", "open") or "open",
            ),
        )

    for risk in extracted["risks"]:
        cursor.execute(
            "INSERT INTO risks(meeting_id, description, severity) VALUES (?, ?, ?)",
            (
                meeting_id,
                risk.get("description", ""),
                risk.get("severity", "medium"),
            ),
        )

    conn.commit()
    conn.close()
    return meeting_id


@app.get("/")
def home():
    return {"status": "working"}


@app.get("/test-db")
def test_db():
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
    tables = [row["name"] for row in cursor.fetchall()]
    conn.close()
    return {"tables": tables}


@app.get("/test-groq")
def test_groq():
    prompt = """
    Return a JSON object with meeting_title, summary, projects, action_items, escalations, and risks.
    Generate a concise meeting title based on the discussion.
    Never leave meeting_title empty.
    Extract tasks, risks, and escalations from this meeting.

    Meeting:
    Rahul will coordinate backend team before Friday.
    Vendor API instability may delay the release.
    Priya escalated the issue.

    Return JSON only.
    """
    return run_groq_json(prompt)


@app.get("/test-gemini")
def test_gemini_compat():
    return test_groq()


@app.post("/analyze")
def analyze(data: AnalyzeRequest):
    prompt = f"""
You are an enterprise meeting intelligence extraction engine.

Extract structured organizational intelligence from the meeting text.
Return ONLY valid JSON. Do not include markdown.

Format:

{{
  "meeting_title": "",
  "summary": "",
  "projects": [
    {{
      "name": "",
      "status": ""
    }}
  ],
  "action_items": [
    {{
      "task": "",
      "owner": "",
      "deadline": "",
      "status": "open"
    }}
  ],
  "escalations": [
    {{
      "issue": "",
      "raised_by": "",
      "status": "open"
    }}
  ],
  "risks": [
    {{
      "description": "",
      "severity": ""
    }}
  ]
}}

Meeting:
{data.text}
"""

    try:
        extracted = normalize_extraction(run_groq_json(prompt))
        meeting_id = store_extraction(data.text, extracted)
        return {"meeting_id": meeting_id, **extracted}
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail={
                "message": "Groq response could not be parsed as meeting intelligence",
                "error": str(exc),
            },
        ) from exc


@app.get("/meetings")
def get_meetings():
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT
            m.id,
            m.title,
            m.summary,
            m.raw_text,
            COALESCE(m.analyzed_at, '') AS analyzed_at,
            COUNT(DISTINCT ai.id) AS action_item_count,
            COUNT(DISTINCT r.id) AS risk_count,
            COUNT(DISTINCT e.id) AS escalation_count
        FROM meetings m
        LEFT JOIN action_items ai ON ai.meeting_id = m.id
        LEFT JOIN risks r ON r.meeting_id = m.id
        LEFT JOIN escalations e ON e.meeting_id = m.id
        GROUP BY m.id
        ORDER BY m.id DESC
        """
    )
    rows = rows_to_dicts(cursor.fetchall())
    conn.close()
    return rows


@app.get("/tasks")
def get_tasks():
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT ai.id, ai.meeting_id, ai.task, ai.owner, ai.deadline, ai.status, m.title AS meeting_title
        FROM action_items ai
        LEFT JOIN meetings m ON m.id = ai.meeting_id
        ORDER BY ai.id DESC
        """
    )
    rows = rows_to_dicts(cursor.fetchall())
    conn.close()
    return rows


@app.get("/risks")
def get_risks():
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT r.id, r.meeting_id, r.description, r.severity, m.title AS meeting_title
        FROM risks r
        LEFT JOIN meetings m ON m.id = r.meeting_id
        ORDER BY r.id DESC
        """
    )
    rows = rows_to_dicts(cursor.fetchall())
    conn.close()
    return rows


@app.get("/escalations")
def get_escalations():
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT e.id, e.meeting_id, e.issue, e.raised_by, e.status, m.title AS meeting_title
        FROM escalations e
        LEFT JOIN meetings m ON m.id = e.meeting_id
        ORDER BY e.id DESC
        """
    )
    rows = rows_to_dicts(cursor.fetchall())
    conn.close()
    return rows


@app.get("/projects")
def get_projects():
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT p.id, p.meeting_id, p.name, p.status, m.title AS meeting_title
        FROM projects p
        LEFT JOIN meetings m ON m.id = p.meeting_id
        ORDER BY p.id DESC
        """
    )
    rows = rows_to_dicts(cursor.fetchall())
    conn.close()
    return rows


@app.get("/dashboard")
def dashboard():
    conn = get_conn()
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) AS count FROM meetings")
    total_meetings = cursor.fetchone()["count"]

    cursor.execute("SELECT COUNT(*) AS count FROM escalations WHERE COALESCE(status, 'open') != 'closed'")
    open_escalations = cursor.fetchone()["count"]

    cursor.execute("SELECT COUNT(*) AS count FROM action_items WHERE COALESCE(status, 'open') != 'closed'")
    open_action_items = cursor.fetchone()["count"]

    cursor.execute("SELECT COUNT(*) AS count FROM risks WHERE LOWER(COALESCE(severity, '')) = 'high'")
    high_severity_risks = cursor.fetchone()["count"]

    conn.close()
    return {
        "total_meetings": total_meetings,
        "open_escalations": open_escalations,
        "open_action_items": open_action_items,
        "high_severity_risks": high_severity_risks,
    }


def extract_name_after(question: str, markers: list[str]) -> str | None:
    for marker in markers:
        pattern = rf"{marker}\s+([a-zA-Z][a-zA-Z\s.-]*)"
        match = re.search(pattern, question, re.IGNORECASE)
        if match:
            return match.group(1).strip(" .?")
    return None


@app.post("/query")
def query(data: QueryRequest):
    question = data.question.strip()
    q = question.lower()
    conn = get_conn()
    cursor = conn.cursor()

    if "risk" in q:
        severity_filter = "high" if "high" in q else None
        if severity_filter:
            cursor.execute(
                """
                SELECT r.id, r.description, r.severity, m.title AS meeting_title
                FROM risks r
                LEFT JOIN meetings m ON m.id = r.meeting_id
                WHERE LOWER(COALESCE(r.severity, '')) = ?
                ORDER BY r.id DESC
                """,
                (severity_filter,),
            )
        else:
            cursor.execute(
                """
                SELECT r.id, r.description, r.severity, m.title AS meeting_title
                FROM risks r
                LEFT JOIN meetings m ON m.id = r.meeting_id
                ORDER BY r.id DESC
                """
            )
        rows = rows_to_dicts(cursor.fetchall())
        conn.close()
        return {"question": question, "type": "risks", "count": len(rows), "results": rows}

    if "escalation" in q:
        raised_by = extract_name_after(question, ["raised by", "from", "by"])
        if raised_by:
            cursor.execute(
                """
                SELECT e.id, e.issue, e.raised_by, e.status, m.title AS meeting_title
                FROM escalations e
                LEFT JOIN meetings m ON m.id = e.meeting_id
                WHERE LOWER(COALESCE(e.raised_by, '')) LIKE ?
                ORDER BY e.id DESC
                """,
                (f"%{raised_by.lower()}%",),
            )
        else:
            cursor.execute(
                """
                SELECT e.id, e.issue, e.raised_by, e.status, m.title AS meeting_title
                FROM escalations e
                LEFT JOIN meetings m ON m.id = e.meeting_id
                ORDER BY e.id DESC
                """
            )
        rows = rows_to_dicts(cursor.fetchall())
        conn.close()
        return {"question": question, "type": "escalations", "count": len(rows), "results": rows}

    if "task" in q or "owner" in q or "assigned" in q:
        owner = extract_name_after(question, ["assigned to", "owner", "for"])
        if owner:
            cursor.execute(
                """
                SELECT ai.id, ai.task, ai.owner, ai.deadline, ai.status, m.title AS meeting_title
                FROM action_items ai
                LEFT JOIN meetings m ON m.id = ai.meeting_id
                WHERE LOWER(COALESCE(ai.owner, '')) LIKE ?
                ORDER BY ai.id DESC
                """,
                (f"%{owner.lower()}%",),
            )
        else:
            cursor.execute(
                """
                SELECT ai.id, ai.task, ai.owner, ai.deadline, ai.status, m.title AS meeting_title
                FROM action_items ai
                LEFT JOIN meetings m ON m.id = ai.meeting_id
                ORDER BY ai.id DESC
                """
            )
        rows = rows_to_dicts(cursor.fetchall())
        conn.close()
        return {"question": question, "type": "tasks", "count": len(rows), "results": rows}

    if "project" in q:
        delayed_terms = ["delayed", "blocked", "at risk", "behind"]
        if any(term in q for term in delayed_terms):
            cursor.execute(
                """
                SELECT p.id, p.name, p.status, m.title AS meeting_title
                FROM projects p
                LEFT JOIN meetings m ON m.id = p.meeting_id
                WHERE LOWER(COALESCE(p.status, '')) LIKE '%delay%'
                   OR LOWER(COALESCE(p.status, '')) LIKE '%blocked%'
                   OR LOWER(COALESCE(p.status, '')) LIKE '%risk%'
                   OR LOWER(COALESCE(p.status, '')) LIKE '%behind%'
                ORDER BY p.id DESC
                """
            )
        else:
            cursor.execute(
                """
                SELECT p.id, p.name, p.status, m.title AS meeting_title
                FROM projects p
                LEFT JOIN meetings m ON m.id = p.meeting_id
                ORDER BY p.id DESC
                """
            )
        rows = rows_to_dicts(cursor.fetchall())
        conn.close()
        return {"question": question, "type": "projects", "count": len(rows), "results": rows}

    cursor.execute(
        """
        SELECT id, title, summary, COALESCE(analyzed_at, '') AS analyzed_at
        FROM meetings
        ORDER BY id DESC
        LIMIT 10
        """
    )
    rows = rows_to_dicts(cursor.fetchall())
    conn.close()
    return {
        "question": question,
        "type": "meetings",
        "count": len(rows),
        "results": rows,
        "message": "Showing recent meetings. Try asking about risks, escalations, tasks, owners, or projects.",
    }
