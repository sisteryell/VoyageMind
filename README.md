# VoyageMind

AI-powered multi-agent travel planner. Enter a country and get the best cities to visit, ranked by history & culture, food & cuisine, and transportation — then aggregated into a final top-2.

## Quick Start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Create your .env (copy the example and fill in keys)
cp .env.example .env

# 3. Run
python main.py
```

Open **http://localhost:8000** in your browser.

## Project Structure

```
VoyageMind/
├── main.py              # FastAPI app, CORS, lifespan, middleware
├── config.py            # Pydantic-settings based configuration
├── routes.py            # API endpoints
├── agents.py            # Base agent + specialist agents
├── schemas.py           # Pydantic models (domain + API contracts)
├── services.py          # OpenAI & Langfuse singletons (retry, timeout)
├── exceptions.py        # Custom exception hierarchy
├── middleware.py         # Request-ID tracking & structured logging
├── prompts/             # Jinja2 user prompts & system prompts
├── templates/
│   └── index.html       # Single-page frontend
├── requirements.txt
└── .env.example
```

## Architecture

1. **User enters a country** — the frontend POSTs to `/plan`.
2. **Three specialist agents run in parallel** (async):
   - History & Culture
   - Food & Cuisine
   - Transportation
3. Each agent returns **3 cities** with confidence scores.
4. An **Aggregator agent** synthesises the results into the **top 2 cities**.

### Production-grade features

| Area | Detail |
|---|---|
| **Configuration** | `pydantic-settings` with `.env` — validated at startup |
| **Error handling** | Custom exception hierarchy (`VoyageMindError`) + global handler |
| **Resilience** | OpenAI calls retry with exponential back-off (configurable) |
| **Observability** | Langfuse tracing on every agent, structured logging, request-ID header |
| **Middleware** | Request logging with timing, CORS |
| **Lifespan** | Graceful startup / shutdown (Langfuse flush) |
| **Validation** | Pydantic v2 for all request, response, and LLM output |
| **DRY agents** | Zero code duplication — subclasses declare prompts + schema only |

## API

### `GET /health`

Liveness probe.

### `POST /plan`

```json
// Request
{ "country": "Japan" }

// Response
{
  "country": "Japan",
  "recommendations": [
    { "city": "Tokyo", "reason": "..." },
    { "city": "Kyoto", "reason": "..." }
  ],
  "agent_details": {
    "history_culture": [ ... ],
    "food_cuisine": [ ... ],
    "transportation": [ ... ]
  },
  "session_id": "voyage-abc123"
}
```

## Environment Variables

See [.env.example](.env.example) for all available options.

## Tech Stack

- **Python 3.11+**
- **FastAPI** + Uvicorn
- **OpenAI** (GPT-4o-mini default)
- **Langfuse** for observability
- **Pydantic v2** for validation & settings

## License

MIT
