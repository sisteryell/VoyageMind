# VoyageMind

AI-powered multi-agent travel planner. Choose a country and travel styles, and VoyageMind dynamically selects the right specialist agents to run — returning the best cities with day-by-day itineraries.

---

## Quick Start

```bash
# 1. Clone & install dependencies
pip install -r requirements.txt

# 2. Put your credentials in .env
# Fill in your OPENAI_API_KEY

# 3. Run
uvicorn main:app --reload
```

Open **http://localhost:8000** in your browser.

---

## How It Works

### Planning Pipeline (`POST /plan`)

```
User selects country + budget + duration + travel styles
        ↓
Dynamic agent selection (based on travel styles)
        ↓
Selected specialist agents run IN PARALLEL
        ↓
Aggregator agent → picks top 2 cities
        ↓
2 × Itinerary agents run IN PARALLEL (one per city)
        ↓
Full result returned to the browser
```

### Dynamic Agent Selection

Agents are selected at runtime based on the user's chosen travel styles. Only the relevant agents run — no wasted API calls.

| Travel Style | Agent |
|---|---|
| 🏔️ Adventure | `AdventureAgent` |
| 🌴 Relaxation | `RelaxationAgent` |
| 👨‍👩‍👧 Family | `FamilyAgent` |
| 💘 Honeymoon | `HoneymoonAgent` |
| 🚶 Solo | `SoloAgent` |
| 🏛️ Culture | `HistoryCultureAgent` |
| 🍜 Food | `FoodCuisineAgent` |
| 🌿 Nature | `NatureAgent` |

> If no styles are selected, all 8 agents run.

---

## Project Structure

```
VoyageMind/
├── main.py              # FastAPI app — CORS, middleware, lifespan
├── config.py            # Pydantic-settings configuration (reads .env)
├── routes.py            # API endpoints: /plan, /chat, /compare
├── agents.py            # Base Agent class + all specialist agents + TRAVEL_STYLE_AGENT_MAP
├── schemas.py           # Pydantic models for requests, responses, and LLM output
├── services.py          # OpenAI singleton client (with retry + back-off)
├── exceptions.py        # Custom exception hierarchy
├── middleware.py        # Request-ID tracking & structured logging
├── prompts/             # Prompt files — one subfolder per agent
│   ├── adventure/
│   │   ├── system.txt
│   │   └── user.txt
│   ├── aggregator/
│   ├── chat/
│   ├── family/
│   ├── food_cuisine/
│   ├── history_culture/
│   ├── honeymoon/
│   ├── itinerary/
│   ├── nature/
│   ├── relaxation/
│   ├── solo/
│   └── transportation/
├── templates/
│   └── index.html       # Single-page frontend (vanilla JS)
├── static/
│   ├── css/style.css
│   └── js/main.js
├── requirements.txt
├── .env.example
└── .env                 # Your local secrets (git-ignored)
```

---

## API Endpoints

### `GET /`
Serves the frontend HTML page.

### `POST /plan`
Run the full planning pipeline for one country.

```json
// Request
{
  "country": "Japan",
  "budget": "mid",
  "duration": 7,
  "travel_styles": ["honeymoon", "food"]
}

// Response
{
  "country": "Japan",
  "budget": "mid",
  "duration": 7,
  "travel_styles": ["honeymoon", "food"],
  "recommendations": [
    { "city": "Kyoto", "reason": "..." },
    { "city": "Tokyo", "reason": "..." }
  ],
  "itineraries": [
    { "city": "Kyoto", "days": [ ... ] },
    { "city": "Tokyo", "days": [ ... ] }
  ],
  "agent_details": {
    "honeymoon": [ { "city": "...", "confidence_score": 0.92, "reason": "..." } ],
    "food":      [ { "city": "...", "confidence_score": 0.88, "reason": "..." } ]
  },
  "session_id": "voyage-abc123"
}
```

**Rate limit:** 10 requests/minute

### `POST /chat`
Ask a follow-up question about a previous plan.

```json
// Request
{
  "country": "Japan",
  "question": "What's the best time to visit Kyoto?",
  "budget": "mid",
  "duration": 7,
  "travel_styles": ["honeymoon"],
  "recommendations": [ ... ]
}

// Response
{ "answer": "The best time to visit Kyoto is..." }
```

**Rate limit:** 20 requests/minute

### `POST /compare`
Run the full pipeline for two countries simultaneously and return both results side by side.

```json
// Request
{
  "country_a": "Japan",
  "country_b": "Italy",
  "budget": "luxury",
  "duration": 10,
  "travel_styles": ["culture"]
}

// Response
{
  "country_a": { ...full plan for Japan... },
  "country_b": { ...full plan for Italy... }
}
```

**Rate limit:** 5 requests/minute

---

## Environment Variables

| Variable | Required | Default | Description |
|---|---|---|---|
| `OPENAI_API_KEY` | ✅ | — | Your OpenAI API key |
| `OPENAI_MODEL` | | `gpt-4o-mini` | Model to use |
| `OPENAI_TIMEOUT` | | `60` | Request timeout in seconds |
| `OPENAI_MAX_RETRIES` | | `3` | Retry attempts on failure |
| `APP_NAME` | | `VoyageMind` | App name in logs/docs |
| `APP_VERSION` | | `2.0.0` | Version string |
| `DEBUG` | | `false` | Enable debug mode |
| `LOG_LEVEL` | | `INFO` | `DEBUG`, `INFO`, `WARNING`, `ERROR` |
| `ALLOWED_ORIGINS` | | `*` | Comma-separated CORS origins |

See [.env.example](.env.example) for a ready-to-copy template.

---

## Production-Grade Features

| Area | Detail |
|---|---|
| **Configuration** | `pydantic-settings` — validated at startup, fails fast if required vars are missing |
| **Error handling** | Custom `VoyageMindError` hierarchy with a global FastAPI exception handler |
| **Resilience** | OpenAI calls retry with exponential back-off (2s → 4s → 8s) |
| **Rate limiting** | Per-endpoint limits via `slowapi` |
| **Middleware** | Per-request UUID, structured timing logs, CORS |
| **Validation** | Pydantic v2 on all requests, responses, and LLM JSON output |
| **DRY agents** | Zero code duplication — subclasses declare only prompts + schema |
| **Parallel execution** | `asyncio.gather` for specialist agents and itinerary agents |

---

## Tech Stack

- **Python 3.11+**
- **FastAPI** + Uvicorn
- **OpenAI** (GPT-4o-mini by default)
- **Pydantic v2** — validation & settings
- **Jinja2** — prompt templating
- **slowapi** — rate limiting

---

## License

MIT
