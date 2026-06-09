# GenAI-Hackathon
# Meeting Intelligence System

AI-powered platform for transforming unstructured meeting discussions into structured organizational intelligence.

## Features

### Meeting Input Processing

Accepts:

* Meeting summaries
* Raw meeting transcripts
* Free-form meeting notes

### Intelligent Information Extraction

Uses a Large Language Model (Groq Llama 3.3) to automatically extract:

* Projects
* Action Items
* Owners
* Deadlines
* Risks
* Escalations

### Structured Knowledge Storage

Stores extracted information in SQLite:

* Meetings
* Projects
* Action Items
* Risks
* Escalations

### Organizational Dashboard

Provides visibility into:

* Total Meetings
* Open Escalations
* Open Action Items
* High Severity Risks

### Conversational Query Engine

Users can ask questions such as:

* Show all risks
* Show all escalations
* Show tasks assigned to Rahul
* Which projects are delayed?

---

# Technology Stack

Frontend

* React


Backend

* FastAPI

Database

* SQLite

AI

* Groq API
* Llama 3.3 70B Versatile

---

# Project Structure

```text
frontend/
backend/

main.py
database.py
models.py

meetings.db

requirements.txt
```

# Installation

## Backend

Create virtual environment:

```bash
python -m venv venv
```

Activate environment:

Windows:

```bash
venv\Scripts\activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Create `.env`:

```env
GROQ_API_KEY=your_api_key
```

Start backend:

```bash
uvicorn main:app --reload
```

Backend runs on:

```text
http://127.0.0.1:8000
```

Swagger Documentation:

```text
http://127.0.0.1:8000/docs
```

---

## Frontend

Install dependencies:

```bash
npm install
```

Run frontend:

```bash
npm run dev
```

Frontend runs on:

```text
http://localhost:5173
```

---

# API Endpoints

## Analyze Meeting

POST

```text
/analyze
```

Request:

```json
{
  "text": "meeting transcript"
}
```

---

## Dashboard

GET

```text
/dashboard
```

---

## Meetings

GET

```text
/meetings
```

---

## Risks

GET

```text
/risks
```

---

## Escalations

GET

```text
/escalations
```

---

## Tasks

GET

```text
/tasks
```

---

## Query Engine

POST

```text
/query
```

Request:

```json
{
  "question": "Show all risks"
}
```

---

# Example Workflow

1. Paste meeting transcript
2. Click Analyze Meeting
3. AI extracts:

   * Projects
   * Action Items
   * Risks
   * Escalations
4. Data stored in SQLite
5. Dashboard updates
6. Query organizational intelligence using natural language


# Author

Varad
