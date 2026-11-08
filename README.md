# Rocco V

A conversational chatbot that interviews the user to gather a structured prompt
spec, then renders it as plain text the user copies/pastes into whatever AI
platform they're actually using (Claude, ChatGPT, DWOS, or anything else that
comes up). Rocco V never calls those platforms or writes files into them — its
entire output is a text block on screen.

## Core concept: ROCCOV

The interview gathers six things, in this order:

- **R**equirements — what the thing must do
- **O**bjective — the goal/why
- **C**ontext — background the model needs to know
- **C**onstraints — limits, things it must NOT do, format/length/tone limits
- **O**utput — exact shape of the expected response
- **V**erification — how to tell the output is correct/good enough

## Output contract (confirmed with user, 2026-11-08)

- Plain text only. No file generation, no structured JSON, no API calls to
  the target platform.
- The UI displays the **target platform name as a header** above the
  generated text block (e.g. "Claude", "ChatGPT", "DWOS") so a user running
  the same ROCCOV answers through multiple targets can tell renders apart.
- One ROCCOV interview can presumably render to more than one target without
  re-answering questions — the six gathered fields are target-agnostic; only
  the rendering step is target-specific.

## LLM backend and authorization (confirmed with user, 2026-11-08; revised 2026-11-08)

- Rocco V uses an LLM as the chat agent that runs the ROCCOV interview and
  composes the resulting prompt text. "Code generator" here just means
  that LLM writing the prompt text — it is not a new feature; the output
  contract above (plain text only) is unchanged.
- **Backend: OpenAI, not Anthropic.** Originally built against the
  Anthropic API, but the user's Claude Pro subscription ($20/mo) doesn't
  cover API usage — Anthropic bills the Console API separately, per
  token, on top of the chat subscription. Rather than pay for both, the
  backend was switched to OpenAI's API (`app/main.py` uses
  `openai.OpenAI`, model configured via `CHAT_MODEL`, currently
  `gpt-5.6-luna` per the user's request — unverified against Claude's
  training data, so if the model id is wrong the error will now surface
  visibly in the chat instead of failing silently).
- Before it can be used, the user must authorize Rocco V. Originally
  scoped as an **OAuth login flow** — but neither Anthropic nor OpenAI
  expose a public third-party OAuth client-registration flow for an app
  like this (no generic "Sign in with X" for arbitrary apps). Implemented
  instead as a **first-run API-key gate**: a `/setup` page blocks every
  other route until an API key is provided, from
  `platform.openai.com/api-keys`. Two ways to provide it:
  - Paste it into `/setup` — saved to `data/auth.json` (gitignored,
    local to the machine), reused on restart.
  - Or set `OPENAI_API_KEY` in `.env` (gitignored; see `.env.example`) —
    `docker-compose.yml` passes it through as a container env var, which
    `app/config.py` checks before the `data/auth.json` fallback, so it
    skips `/setup` entirely.

## Why DWOS matters as a reference target

Investigated `G:\dwos` directly (user's request) to ground what a
"DWOS-flavored" render should look like. Findings, in case the actual DWOS
project changes before this gets built:

- DWOS is a real, running, event-driven multi-agent platform (Kafka backbone,
  Orchestrator, Agent Manager, Tool Registry), deployed per-client as one
  docker-compose stack. See `G:\dwos\DWOS_Architecture_Design.md`.
- Its real artifacts are JSON files: **Employee** definitions
  (`input_schema` / `output_description` / `steps`, business-facing) and
  **Agent templates** (`runtime.system_prompt`, `capabilities.tools` with
  per-tool call caps, `expected_output_format`, `messaging` topics, `budget`
  — worker-facing). Example read in full:
  `G:\dwos\services\agent-runtime\app\templates\purchasing\purchasing_analyst.json`.
- That real system_prompt is a useful style reference even though Rocco V
  will never touch DWOS's actual JSON: it's rigid and step-numbered, bans
  specific anti-patterns in all caps ("NEVER CREATE MORE QUERIES THAN THE 2
  SUGGESTED ABOVE"), and spells out the exact output format/field order in
  prose — because it runs unattended inside a budgeted, auditable pipeline
  with no human in the loop to correct it mid-run.
- Conclusion: a "DWOS" render in Rocco V should lean toward that
  strict/procedural/anti-pattern-explicit style in the prose itself. It's a
  prompt-phrasing difference from a Claude/ChatGPT render, not a
  file-format difference — Rocco V still just outputs text either way.

## Stack and interview style (confirmed with user, 2026-11-08)

- **Stack: FastAPI.** Backend is FastAPI, which also owns the LLM
  authorization gate described above. Frontend framework wasn't specified
  beyond "FastAPI" — assuming server-rendered templates (Jinja2 + light
  JS) for the chat UI rather than a separate React build, since the whole
  app is one chat screen plus a render-with-header screen. Flag if a
  React frontend was actually intended.
- **Interview style: LLM-driven, using ROCCOV as the template.** The model
  runs the interview as a free-form conversation, with the six ROCCOV
  fields (Requirements, Objective, Context, Constraints, Output,
  Verification) given to it as the structure/checklist to fill rather than
  a fixed scripted question sequence — it asks natural follow-ups and
  decides when each field is answered well enough to move on.

## Running it

```
docker compose up -d --build
```

Then open **http://localhost:10222**. First run redirects to `/setup` to
paste an OpenAI API key (see Authorization above), unless `OPENAI_API_KEY`
is already set in `.env`, in which case it goes straight to the chat.

Port **10222** was picked deliberately to avoid the crowded `8000`/`8080`
range and the `3000`/`5432`/`9092`-family ports already used across this
machine's other docker stacks (bScan, DWOS, research-stack, etc.).

## Project layout

- `app/main.py` — FastAPI routes: `/setup` (auth gate), `/` (chat page),
  `/chat` (one interview turn), `/render/{target}` (ask the model to
  render for a specific target). Conversation history is kept in memory
  per session cookie — no database, this is a single-user local tool.
- `app/rocco.py` — the ROCCOV system prompt and the `<<<ROCCOV_OUTPUT>>>`
  marker convention the app uses to pull the final rendered text out of
  the model's reply.
- `app/targets.py` — the extensible target lookup (resolved as a plain
  dict). Currently: Claude, ChatGPT, DWOS, LangChain, Generic/Other. Add
  an entry here for any new target. (Note: these are render *targets* —
  what the output prompt text is styled for — independent of which LLM
  backend, above, actually runs the interview.)
- `app/templates/`, `app/static/` — Jinja2 pages + plain vanilla-JS
  `fetch()` for the chat/render interactions (no HTMX/React dependency
  pulled in, so the container has no external CDN dependency at runtime).

## Open decisions (not yet made — pick up here)

Everything from earlier scoping is resolved and built. Nothing currently
blocking; next to settle are usability follow-ups:

1. Should the LLM-driven interview enforce field order more, or is pure
   free-form (current behavior) good enough once used for real?
2. Persisting conversations across container restarts (currently
   in-memory, lost on restart) — worth it for a single-user local tool?

## Project tracking

This project uses ClaudeBrain (shared Postgres memory, see
`G:\bScan\CLAUDE.md` for the full command reference). `brain.py` is copied
into this repo root. Session #158 (2026-11-08) has the initial scoping
decisions logged; Session #159 added the authorization requirement;
Session #160 confirmed the FastAPI stack and LLM-driven/ROCCOV-template
interview style; Session #161 corrected OAuth to an API-key gate, added
the LangChain target, and built + ran the app; Session #162 re-confirmed
the API-key gate after user pushback; Session #163 fixed a silent-failure
bug in error handling; Session #164 switched the LLM backend from
Anthropic to OpenAI (billing — see above) and wired `.env`/`OPENAI_API_KEY`
through docker-compose. Run `python brain.py search "rocco"` or
`python brain.py recent 5` from this folder to pull them back up.
