# Architecture — OS enforcement vs our inbox

**We do not control the device.**

```
Parent door ─┐
Child door  ─┼─► FastAPI ─► Strands family_desk (orchestrator)
Phone OS    ─┘                      │
  (Screen Time /                    ├─ setup_coach        → Family Policy JSON
   Digital Wellbeing)               ├─ request_triage     → allow / deny / ask parent
   stays on the phone               ├─ checkin_runner     → Saturday + random ping
                                    ├─ digest_writer      → Red / Needs you / Green
                                    └─ override_clerk     → parent yes/no log
                                              │
                                              ▼
                                   @tool functions (deterministic)
                                              │
                          JSON store ◄────────┘         Amazon Bedrock Claude Sonnet
                          policy, snapshots,            (or local desk-router so the
                          decisions, outbox             Agent loop still runs)
```

The phone OS is the lock. Family Loop is the inbox:

- Agents remind (random ping), compare (snapshot diff vs approved apps), and ask (triage).
- Parent only sees a card when triage cannot safely file the decision.
- Sunday is a background job (`POST /api/digest`; cron/EventBridge can hit the same route).

See `architecture.svg` for the drawing used in the README.
