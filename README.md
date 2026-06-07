# Autonomous Financial Agent (Investment Planner)

A privacy-first, multi-agent financial management application that ingests PDF bank statements, scrubs sensitive Personal Identifiable Information (PII) locally, parses and categorizes financial transactions, and facilitates natural language interactions with a financial database.

The system features an interactive Next.js dashboard, a FastAPI backend, and a multi-agent orchestration layer powered by LangGraph (with rule-based fallbacks) to route queries between a conversational assistant, a deterministic text-to-SQL agent, and an Indian Income Tax Advisory agent.

---

## Key Features

1. **Privacy-First Statement Uploads**: Upload statements securely. Local regular expressions mask and scrub emails, card numbers, account numbers, names, and Indian tax identifiers (PAN/Aadhar) before any cloud-based LLM processing.
2. **High-Fidelity PDF Parsing**: Converts complex statements and tables to clean markdown format using `LlamaParse` (with local `pdfplumber` layout analysis as a fallback).
3. **Structured Categorization**: Automated categorization of transactions into classes (`FOOD`, `TRAVEL`, `UTILITIES`, `RENT`, `INVESTMENT`, `POTENTIAL_DEDUCTION`, etc.) using LLM-structured schemas or rule-based heuristics.
4. **Deterministic SQL Agent**: Query spending history and statistics using natural language (e.g., *"What is my average monthly spend on utilities?"*). Translates inputs to read-only SQL queries with built-in protection against destructive operations (updates, drops, deletes).
5. **Indian Income Tax Advisory Agent**: Automatically scans historical transactions to offer personalized tax-saving recommendations matching Sections 80C, 80D, 44ADA, 80GG, and 80TTA of the Indian Income Tax Act.

---

## Tech Stack

- **Frontend**: Next.js (React), TailwindCSS, Lucide Icons, Fetch API.
- **Backend**: FastAPI, SQLAlchemy (SQLite/PostgreSQL support), LangGraph.
- **Data & OCR**: LlamaParse (LlamaIndex), pdfplumber.
- **Deployment**: Docker, Docker Compose, PostgreSQL (Alpine).

---

## Project Structure

```text
├── backend/
│   ├── app/
│   │   ├── main.py          # FastAPI application routes
│   │   ├── orchestrator.py  # LangGraph orchestration and query routing
│   │   ├── sql_agent.py     # Text-to-SQL Translation agent & DB sanitization
│   │   ├── tax_advisor.py   # RAG over Indian Income Tax Code
│   │   ├── parsing.py       # PDF extraction & PII Scrubber
│   │   ├── categorizer.py   # Transaction categorization (LLM/Heuristics)
│   │   └── database.py      # SQLAlchemy schemas & sessions
│   ├── tests/               # Backend integration and unit tests
│   └── Dockerfile           # Backend container environment
├── frontend/
│   ├── src/app/             # Next.js pages, CSS, and layouts
│   ├── Dockerfile           # Frontend container environment
│   └── README.md            # Frontend specific docs
├── docker-compose.yml       # Production-grade multi-container orchestrator
├── system_documentation.tex # Technical system documentation in LaTeX
└── README.md                # Root project documentation (this file)
```

---

## System Architecture

Below is the diagram of the information flow and multi-agent interaction layers:

```
                  ┌──────────────────────┐
                  │   Next.js Frontend   │
                  └──────────┬───────────┘
                             │
                  ┌──────────▼───────────┐
                  │   FastAPI Backend    │◀──────────────────┐
                  └────┬────────────┬────┘                   │
                       │            │                        │
        ┌──────────────▼──────┐     │              ┌─────────┴─────────┐
        │ Local PII Scrubber  │     │              │ Database (SQLite/ │
        └──────────────┬──────┘     │              │    Postgres)      │
                       │            │              └─────────▲─────────┘
        ┌──────────────▼──────┐     │                        │
        │      PDF Parser     │     │                        │
        │ (Llama/pdfplumber)  │     │                        │
        └──────────────┬──────┘     │                        │
                       │            │                        │
                       └────────────┼──────────┐             │
                                    │          │             │
                         ┌──────────▼──────────▼┐            │
                         │     Orchestrator     │            │
                         │ (LangGraph / Router) │            │
                         └──────────┬───────────┘            │
                                    │                        │
         ┌──────────────────────────┼────────────────────────┤
         │                          │                        │
 ┌───────▼───────┐          ┌───────▼───────┐        ┌───────▼───────┐
 │   SQL Agent   │          │  Tax Advisor  │        │ Conversational│
 │ (Text-to-SQL) │          │  (Tax RAG)    │        │   Assistant   │
 └───────────────┘          └───────────────┘        └───────────────┘
```

---

## Detailed System Documentation (LaTeX)

For a publication-ready, mathematically rigorous architectural breakdown, please refer to the LaTeX documentation file at:
👉 **[system_documentation.tex](system_documentation.tex)**

You can compile it locally using `pdflatex system_documentation.tex` or upload it to Overleaf to generate a PDF.

---

## Getting Started

### Prerequisites

- [Docker & Docker Compose](https://www.docker.com/)
- An [OpenAI API Key](https://platform.openai.com/) or [Google Gemini API Key](https://ai.google.dev/) (optional, fallbacks exist)
- A [LlamaParse API Key](https://cloud.llamaindex.ai/) (optional, fallbacks exist)

### Step 1: Clone and Configure Environment

Create a `.env` file in the root directory and populate your API credentials:

```bash
OPENAI_API_KEY=your_openai_api_key
GEMINI_API_KEY=your_gemini_api_key
LLAMAPARSE_API_KEY=your_llamaparse_api_key
```

### Step 2: Build and Run with Docker Compose

Launch the PostgreSQL database, FastAPI backend, and Next.js frontend services:

```bash
docker-compose up --build
```

### Step 3: Access the Services

- **Frontend Dashboard**: [http://localhost:3000](http://localhost:3000)
- **FastAPI Documentation & Swagger UI**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **Database Port**: Local mapping at `localhost:5432`

---

## License

This project is licensed under the MIT License.