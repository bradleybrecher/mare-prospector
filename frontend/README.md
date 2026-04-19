# MaRe — Frontend (placeholder)

Reserved for a Next.js review dashboard where the MaRe team will:

- Review and approve AI-drafted outreach before it sends.
- Skim generated content packages (Short + blog + social) and request edits.
- Track per-salon outreach status once Pillar 1 (Prospecting) is wired up.

## Initialize when ready

From the repo root:

```bash
cd frontend
npx create-next-app@latest . --typescript --tailwind --app --eslint --no-src-dir --import-alias "@/*"
```

Then create `frontend/.env.local` with:

```
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
```

The backend should be invoked via a thin FastAPI layer (not scaffolded yet —
Pillar 2 and 3 run fine from the CLI today).
