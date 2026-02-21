# Character Voice Consistency Checker

> Fiction writers, especially for long series, struggle to maintain consistent character voice, dialect, and speech patterns across chapters and books.

## Feedback & Ideas

> **This project is being built in public and we want to hear from you.**
> Found a bug? Have a feature idea? Something feel wrong or missing?
> **[Open an issue](../../issues)** — every piece of feedback directly shapes what gets built next.

## Status

> 🚧 In active development — not yet production ready

| Feature | Status | Notes |
|---------|--------|-------|
| Project scaffold & CI | ✅ Complete | |
| Auth, project model, file upload & Stripe paywall | ✅ Complete | Supabase auth, .docx parsing, 15k-word paywall |
| Character identification & dialogue extraction | ✅ Complete | Regex + alias merge |
| Voice profile generation & consistency scoring | ✅ Complete | 4 dimensions, flags, dismiss, SSE progress |
| Web dashboard | 🚧 In Progress | Next task |
| Deploy & verify | 📋 Planned | |

## What It Solves

Fiction writers, especially for long series, struggle to maintain consistent character voice, dialect, and speech patterns across chapters and books. VoiceCheck automatically identifies characters in your manuscript, builds per-character voice profiles across four dimensions (vocabulary level, sentence structure, verbal tics, and formality), and flags dialogue lines that deviate from each character's established voice.

### How consistency flags work

Each character gets a 0–100 consistency score. The analyzer detects dialogue lines that are stylistically inconsistent with the character's overall voice — for example, a formally-written character suddenly using slang. Each flag includes:

- **Severity** (low / medium / high)
- **Dimension** (formality, vocabulary_level, sentence_structure, or verbal_tics)
- **Manuscript location** (chapter + paragraph index)
- **Verbatim passage** from the manuscript

Flags can be dismissed as intentional (e.g., a character using a different register in a specific scene), which removes them from the score. Dismissing all flags returns a score of exactly 100.

## Who It's For

Novelists, series writers, and interactive fiction authors managing large casts of characters.

## Tech Stack

- **Backend**: Python + FastAPI
- **Frontend**: React + Vite + TypeScript
- **Testing**: Pytest (backend), Playwright (E2E)
- **AI**: Claude API (Anthropic) — with rule-based fallback for test environments
- **Auth**: Supabase
- **Payments**: Stripe Checkout
- **File Parsing**: python-docx

## API Overview

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/auth/signup` | POST | Create account |
| `/api/auth/login` | POST | Get session token |
| `/api/projects` | POST | Upload .docx or paste text |
| `/api/projects/{id}` | GET | Get project (includes `text` and `status` fields) |
| `/api/projects/{id}/progress` | GET | Polling status (queued → complete) |
| `/api/projects/{id}/retry` | POST | Retry failed analysis without re-uploading |
| `/api/projects/{id}/characters` | GET | List detected characters |
| `/api/projects/{id}/characters/merge` | POST | Merge two character aliases |
| `/api/projects/{id}/characters/{cid}/profile` | GET | Voice profile (4 dimensions + score) |
| `/api/projects/{id}/characters/{cid}/flags` | GET | Consistency flags |
| `/api/projects/{id}/characters/{cid}/flags/{fid}/dismiss` | POST | Dismiss a flag |

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
