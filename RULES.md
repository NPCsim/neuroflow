# Project Standing Rules

These standing rules apply to all future architecture, implementation, testing, and agent workflows in this repository.

---

## 1. Monorepo Architecture & Tech Stack

The repository is structured as a monorepo containing two core applications:

- **/backend**
  - **Framework**: FastAPI
  - **Runtime**: Python 3.11
  - **ORM & Migrations**: SQLAlchemy & Alembic
  - **Architecture**: Modular layout with domain models, typed schemas, deterministic scheduling logic, and service layers.
- **/frontend**
  - **Framework**: Next.js 14 (App Router)
  - **Language**: TypeScript (strict mode)
  - **Styling**: Tailwind CSS
  - **Data Visualization**: Recharts
  - **Architecture**: Server & Client component segregation, centralized API client, typed state management.

---

## 2. Secrets & Environment Configuration

- **Zero Secrets in Code**: Secrets and sensitive configuration must only be accessed via environment variables. Never commit actual secret values, `.env` files, or production credentials.
- **Provide Templates**: Always provide and maintain `.env.example` files in both `/backend` and `/frontend` documenting all required and optional environment keys.
- **Fail Fast on Missing Config**: Validate required environment variables at application startup (e.g., using Pydantic `BaseSettings` on the backend and validated environment utilities on the frontend).

---

## 3. LLM Safeguards & Deterministic Scheduling

- **No Direct Schedule Mutation**: The LLM **NEVER** writes directly to the schedule database or mutates schedule state directly.
- **Tool-Based Proposals Only**: The LLM may only propose schedule modifications by invoking predefined, strongly-typed tools and action schemas.
- **Deterministic Engine**: All schedule placement, slot allocation, and conflict resolution must be calculated and executed solely by the deterministic scheduler located in `backend/scheduler.py`.

---

## 4. Change Tracking: Plan Diffs & Snapshots

- **Plan Diffs**: Every change proposed or enacted by an agent must produce a clear before-and-after "plan diff" highlighting the exact delta.
- **Undo / Snapshot Guarantee**: Every mutation must be accompanied by an immutable snapshot of the prior state so that any agent-made change can be safely rolled back or undone.

---

## 5. Time & Timezone Handling

- **Storage**: All dates and timestamps are stored exclusively in **UTC** across the database, APIs, and background processes.
- **Display**: All timestamps are formatted and rendered on the frontend in the user's localized timezone, resolved from user settings.
- **Explicit Serialization**: Timestamps must be serialized as ISO 8601 strings with explicit UTC indicator (`Z` or `+00:00`).

---

## 6. API Standards & Quality Assurance

- **Typed Contracts**: Every endpoint must define explicit, typed Pydantic models for request bodies, query params, and response envelopes.
- **Error Handling**: Implement structured error handling across all endpoints returning standardized error payloads with appropriate HTTP status codes.
- **Pytest Suite**: Every endpoint must be backed by automated tests written with `pytest`.
- **Mocked LLM Calls**: External LLM calls must **always** be mocked during test runs. Automated tests must never trigger live LLM API calls.

---

## 7. Workflow & Dependency Rules

- **Minimal Dependencies**: Keep dependencies minimal. Prefer standard library solutions where feasible; avoid bringing in unnecessary packages.
- **End-of-Task Protocol**: After completing each task:
  1. **Run tests**: Ensure the test suite passes (`pytest` and frontend checks).
  2. **Run the app**: Verify that backend and frontend compile/run cleanly.
  3. **5-Bullet Summary**: Summarize all changes in exactly **5 bullets**.
