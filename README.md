# VoyageMind

A travel planning assistant powered by GPT-4o-mini. You pick a country, budget, duration, and travel style — it gives you city recommendations and a day-by-day itinerary.

---

## What it does

- Runs a specialist AI agent based on your chosen travel style (solo, honeymoon, adventure, etc.)
- Aggregates the results into ranked city recommendations
- Builds a detailed itinerary for each recommended city
- Lets you ask follow-up questions about your trip
- Compare two countries side by side

---

## Travel Styles

| Style | What the agent focuses on |
|---|---|
| Adventure | Hiking, extreme sports, outdoor activities |
| Relaxation | Spas, beaches, slow-paced retreats |
| Family | Kid-friendly activities, safety, convenience |
| Honeymoon | Romantic spots, fine dining, scenic stays |
| Solo | Budget tips, safe neighbourhoods, solo-friendly experiences |
| Culture | Museums, heritage sites, local history |
| Food | Street food, local restaurants, food markets |
| Nature | National parks, wildlife, scenic landscapes |

If you pick multiple styles, all relevant agents run in parallel and the aggregator combines them.

---

## Project Structure

```
VoyageMind/
├── main.py               # FastAPI app setup
├── routes.py             # API endpoints
├── agents.py             # Agent functions + TRAVEL_STYLE_AGENT_MAP
├── schemas.py            # Request/response models
├── config.py             # Settings from .env
├── exceptions.py         # Custom error classes
├── services.py           # OpenAI client
├── middleware.py         # Rate limiting + request logging
├── controllers/
│   └── travel_controller.py
├── models/
│   └── travel_model.py
├── requirements.txt
├── .env                  # Your API keys
├── static/
│   ├── css/style.css
│   ├── js/main.js
│   └── favicon.svg
├── templates/
│   └── index.html
└── prompts/
    ├── adventure/
    │   ├── system.txt
    │   └── user.txt
    ├── aggregator/
    ├── chat/
    ├── family/
    ├── food_cuisine/
    ├── history_culture/
    ├── honeymoon/
    ├── itinerary/
    ├── nature/
    ├── relaxation/
    ├── solo/
    └── transportation/
```

---

## Setup

**1. Clone the repo**
```bash
git clone https://github.com/sisteryell/VoyageMind.git
cd VoyageMind
```

**2. Create a virtual environment**
```bash
python -m venv venv
# Windows
venv\Scripts\activate
# Linux / macOS
source venv/bin/activate
```

**3. Install dependencies**
```bash
pip install -r requirements.txt
```

**4. Create your `.env` file**

Open `.env` and fill in your keys:
```env
OPENAI_API_KEY=sk-...
OPENAI_MODEL = gpt-4o-mini
OPENAI_TIMEOUT = 60
OPENAI_MAX_RETRIES = 3
APP_NAME = VoyageMind
APP_VERSION = 2.0.0
DEBUG = false
LOG_LEVEL = INFO
ALLOWED_ORIGINS = *
```

**5. Run the app**
```bash
uvicorn main:app --reload
```

Open **http://localhost:8000** in your browser.

---

## API Endpoints

### `GET /health`
Returns app status and version. No auth required.

**Response**
```json
{"status": "healthy", "version": "2.0.0"}
```

---

### `POST /plan`
Generate city recommendations and itineraries.

**Request**
```json
{
  "country": "Japan",
  "budget": "mid",
  "duration": 3,
  "city_count": 2,
  "travel_styles": ["solo", "food"],
  "session_id": null
}
```

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `country` | string | — | Destination country (required) |
| `budget` | string | `"mid"` | One of: `budget`, `mid`, `luxury` |
| `duration` | int | 3 | Trip length in days (1–30) |
| `city_count` | int | 2 | Number of cities to recommend (1–5) |
| `travel_styles` | string[] | [] | Styles from: `adventure`, `relaxation`, `family`, `honeymoon`, `solo`, `culture`, `food`, `nature` |
| `session_id` | string \| null | null | Optional id for idempotency/tracking |

**Response**
```json
{
  "country": "Japan",
  "budget": "mid",
  "duration": 7,
  "city_count": 2,
  "travel_styles": ["solo", "food"],
  "recommendations": [
    {
      "city": "Tokyo",
      "reason": "Best city for solo food exploration"
    }
  ],
  "itineraries": [
    {
      "city": "Tokyo",
      "days": [
        {
          "day": 1,
          "title": "Arrival and First Bites",
          "activities": ["...", "..."]
        }
      ]
    }
  ],
  "agent_details": {
    "solo": [{"city": "...", "confidence_score": 0.9, "reason": "..."}],
    "food": [{"city": "...", "confidence_score": 0.85, "reason": "..."}]
  },
  "session_id": "voyage-..."
}
```

---

### `POST /chat`
Ask a follow-up question about a country. Optionally pass `recommendations` from a previous `/plan` for context.

**Request**
```json
{
  "question": "What is the best time to visit?",
  "country": "Japan",
  "budget": "mid",
  "duration": 7,
  "travel_styles": ["solo"],
  "recommendations": []
}
```

| Field | Type | Description |
|-------|------|-------------|
| `question` | string | Your question (required, max 500 chars) |
| `country` | string | Destination country |
| `budget` | string | One of: `budget`, `mid`, `luxury` |
| `duration` | int | Trip length in days (1–30) |
| `travel_styles` | string[] | Same as `/plan` |
| `recommendations` | object[] | Optional; from a previous `/plan` for context |

**Response**
```json
{
  "answer": "The best time to visit Japan is..."
}
```

---

### `POST /compare`
Compare two countries for a given travel style. Returns two full plan objects (same shape as `/plan` response).

**Request**
```json
{
  "country_a": "Japan",
  "country_b": "Thailand",
  "budget": "mid",
  "duration": 10,
  "travel_styles": ["solo"]
}
```

| Field | Type | Description |
|-------|------|-------------|
| `country_a` | string | First country |
| `country_b` | string | Second country |
| `budget` | string | One of: `budget`, `mid`, `luxury` |
| `duration` | int | Trip length in days (1–30) |
| `travel_styles` | string[] | Same as `/plan` |

**Response**
```json
{
  "country_a": {
    "country": "Japan",
    "budget": "mid",
    "duration": 10,
    "city_count": 2,
    "travel_styles": ["solo"],
    "recommendations": [...],
    "itineraries": [...],
    "agent_details": {...}
  },
  "country_b": {
    "country": "Thailand",
    "budget": "mid",
    "duration": 10,
    "city_count": 2,
    "travel_styles": ["solo"],
    "recommendations": [...],
    "itineraries": [...],
    "agent_details": {...}
  }
}
```

---

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|--------|-------------|
| `OPENAI_API_KEY` | ✅ | — | Your OpenAI API key |
| `OPENAI_MODEL` | ❌ | `gpt-4o-mini` | Model to use |
| `OPENAI_TIMEOUT` | ❌ | 60 | Request timeout (seconds) |
| `OPENAI_MAX_RETRIES` | ❌ | 3 | Retries with exponential backoff |
| `APP_NAME` | ❌ | VoyageMind | Application name |
| `APP_VERSION` | ❌ | 2.0.0 | Application version |
| `DEBUG` | ❌ | false | Debug mode (keep false in production) |
| `LOG_LEVEL` | ❌ | INFO | Logging level |
| `ALLOWED_ORIGINS` | ❌ | * | CORS origins (comma-separated) |

---

## How it works

```
User picks country + budget + duration + travel styles
        ↓
Specialist agents run in parallel (one per selected style)
        ↓
Aggregator combines results → ranked city recommendations
        ↓
Itinerary agent builds day-by-day plan for each city
        ↓
Response returned to browser
```

---

## Rate Limits

| Endpoint | Limit |
|---|---|
| `/plan` | 3 requests/minute |
| `/chat` | 10 requests/minute |
| `/compare` | 5 requests/minute |

---

## License

MIT