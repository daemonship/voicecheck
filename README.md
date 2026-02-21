# Character Voice Consistency Checker

> Fiction writers, especially for long series, struggle to maintain consistent character voice, dialect, and speech patterns across chapters and books.

## What It Solves

Fiction writers, especially for long series, struggle to maintain consistent character voice, dialect, and speech patterns across chapters and books.

## Who It's For

Novelists, series writers, and interactive fiction authors managing large casts of characters.

## Tech Stack

- **Backend**: Python + FastAPI
- **Frontend**: React + Vite + TypeScript
- **Testing**: Pytest (backend), Playwright (E2E)
- **AI**: Claude API (Anthropic)
- **Auth**: Supabase
- **Payments**: Stripe Checkout
- **File Parsing**: python-docx

## Development Status

| Task | Status | Description |
|------|--------|-------------|
| Task 1 | ✅ Complete | Initialize repo structure and CI skeleton |
| Task 2 | ⏳ Pending | Auth, project model, file upload, and Stripe paywall |
| Task 3 | ⏳ Pending | Character identification, dialogue extraction, and alias merging |
| Task 4 | ⏳ Pending | Voice profile generation, consistency analysis, and scoring |
| Task 5 | ⏳ Pending | Web UI: upload, manuscript viewer, character list, profiles, and flags |
| Task 6 | ⏳ Pending | Code review |
| Task 7 | ⏳ Pending | Pre-launch verification |
| Task 8 | ⏳ Pending | Deploy and verify |

## Getting Started

### Prerequisites
- Python 3.11+
- Node.js 20+
- Anthropic API key
- Stripe account (test mode)
- Supabase project

### Installation

```bash
# Install dependencies
make install

# Run development servers
make dev

# Run tests
make test

# Run linters
make lint
```

### Environment Setup

Copy `.env.example` to `.env` and fill in your credentials:

```bash
cp .env.example .env
```

---

*Built by [DaemonShip](https://github.com/daemonship) — autonomous venture studio*
