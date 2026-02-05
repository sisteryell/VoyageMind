# VoyageMind 🌍

AI Travel Planner using multiple specialized agents to recommend the best cities.

## Quick Start

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Set up `.env` file:**
   ```env
   OPENAI_API_KEY=your_key_here
   OPENAI_MODEL=gpt-4o-mini
   LANGFUSE_PUBLIC_KEY=your_key_here
   LANGFUSE_SECRET_KEY=your_key_here
   LANGFUSE_HOST=https://cloud.langfuse.com
   ```

3. **Run the app:**
   ```bash
   python main.py
   ```

4. **Open browser:** `http://localhost:8000`

## Project Structure

```
VoyageMind/
├── main.py              # FastAPI app
├── routes.py            # API endpoints
├── agents.py            # All AI agents
├── schemas.py           # Data validation
├── services.py          # OpenAI & Langfuse singletons
├── prompts/             # Jinja2 templates & system prompts
│   ├── history_culture.jinja
│   ├── history_culture_system.txt
│   ├── food_cuisine.jinja
│   ├── food_cuisine_system.txt
│   ├── transportation.jinja
│   ├── transportation_system.txt
│   ├── aggregator.jinja
│   └── aggregator_system.txt
├── templates/           # Web UI
│   └── index.html
├── requirements.txt
└── .env
```

## How It Works

1. **User enters a country** → Frontend sends POST to `/plan`
2. **3 specialist agents run in parallel:**
   - History & Culture Agent
   - Food & Cuisine Agent
   - Transportation Agent
3. **Each agent returns 3 cities** with confidence scores
4. **Aggregator agent synthesizes** all recommendations
5. **Returns top 2 cities** with comprehensive reasons

## Tech Stack

- **Python 3.11+** - Language
- **FastAPI** - Web framework
- **OpenAI API** - AI completions
- **Langfuse** - Observability
- **Pydantic** - Validation
- **Jinja2** - Templating

## Key Features

✅ Multi-agent architecture  
✅ Singleton pattern for efficiency  
✅ Async/parallel execution  
✅ Pydantic validation  
✅ Langfuse tracing  
✅ Clean, modern UI  

## API Usage

**POST /plan**
```json
{
  "country": "Japan"
}
```

**Response:**
```json
{
  "country": "Japan",
  "recommendations": [
    {"city": "Tokyo", "reason": "..."},
    {"city": "Kyoto", "reason": "..."}
  ],
  "agent_details": {...}
}
```

## License

MIT
