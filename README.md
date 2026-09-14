# Family Loop

**Track: Everyday Agents — [Agents for Humans](https://agentsforhumans.devpost.com/)**

Phones enforce. Agents remind, compare, and ask. Parent only shows up for a real yes/no.

**We do not control the device.**

Family Loop is the inbox around Screen Time / Digital Wellbeing — not a replacement for it, not MDM, not Family Link. Meera (parent) and Aarav (13, Bengaluru) already have a lock on the phone. They do not have a desk that notices a new app, a missed Saturday file, or a Reddit ask, and that only knocks when someone has to say yes or no.

## What it does

| Surface | Who | Artifact |
|---|---|---|
| Two doors | Parent / child | Child cannot change rules or approve themselves |
| Setup coach | Parent, once | **Family Policy JSON** |
| Locks checklist | Parent | Claimed Screen Time / Digital Wellbeing boxes. Unchecked → Sunday **Red** |
| Request desk | Child asks, agent triages | allow / deny / **ask parent** |
| Saturday file | Child | Pasted app list + minutes |
| Random Screen Time ask | Background, demo button | Max 1/day, 3/week, never during school hours |
| Sunday digest | Background | **Red / Needs you / Green** as a page + a WhatsApp-shaped message |
| Memory | JSON store | Policy, snapshots, decisions, overrides survive restart |

Must ask parent: new app, new contact, first blocked category, anything that costs money. **No silent yes** on social / purchase / new contact.

## Demo (5 minutes)

Seeded family: `meera@familyloop.demo` / `parent` and `aarav@familyloop.demo` / `aarav`.

1. Parent door → setup coach writes the policy → tick every lock.
2. Child door → ask for **Reddit** → stays **pending**.
3. Parent → **It’s Saturday** → **Simulate random ask**.
4. Child → paste `YouTube 40` / `Discord 25` / `WhatsApp 12`. Discord was never approved → marked Red.
5. Parent **ignores** Reddit.
6. Parent → **It’s Sunday** → **Run Sunday digest**.
   - **Red:** Discord (new app never approved) + ignored Reddit
   - **Needs you:** Reddit
   - Outbox shows a simulated WhatsApp, labelled as simulated

## Stack

- Python 3.10+ · FastAPI · [Strands Agents SDK](https://strandsagents.com/)
- Multi-agent: `family_desk` orchestrator + five specialists **as tools**
- Deterministic Python owns policy, triage, diffs, pings, and the digest buckets
- Amazon Bedrock Claude Sonnet when `FAMILY_LOOP_MODEL=bedrock`
- **LM Studio** (header default) — live local model at `http://192.168.31.64:1234`
- **Bedrock** — Amazon Bedrock Claude Sonnet when AWS access is on
- JSON file memory (`data/family.json`)
- Thin web UI (two doors, parent desk, child home)

```
Browser ──► FastAPI ──► Strands family_desk
                            ├ setup_coach
                            ├ request_triage
                            ├ checkin_runner
                            ├ digest_writer
                            └ override_clerk
                                 │
                                 ▼
                          @tool functions ──► JSON store
                                 │
                          Amazon Bedrock (or local desk-router)
```

Full drawing: [docs/architecture.svg](docs/architecture.svg)

Optional later: wrap the same orchestrator in **Amazon Bedrock AgentCore Runtime**. Cron or EventBridge can hit `POST /api/digest` and `POST /api/ping`; the UI buttons exist so judges do not wait for a clock.

## Run

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python -m app.seed
uvicorn app.main:app --reload --port 8000
```

Open http://127.0.0.1:8000

### Bedrock (hackathon submission)

1. AWS credentials with Bedrock access to Claude Sonnet in `us-west-2` (or set `AWS_REGION` / `BEDROCK_MODEL_ID`).
2. In `.env`: `FAMILY_LOOP_MODEL=bedrock`
3. Restart uvicorn. Desk tape will show `bedrock:…`.

### LM Studio

1. Open LM Studio, load a model, start the local server.
2. Point Family Loop at `http://192.168.31.64:1234` (header **LM Studio**).
3. If the box is offline, the desk still files artifacts so the demo does not die.

The mock model is still a real Strands `Agent` loop: it emits tool-use events and the same `@tool` specialists run. Use it for tests and for a live URL if Bedrock is not on that host.

```bash
make test
```

## What we did not build

iOS/Android apps, MDM, Screen Time API, Family Link API, geofence, reading Roblox DMs, live install spy. The checklist is an honest substitute for those APIs. Snapshots are **human paste**, labelled as such.

## License

MIT
