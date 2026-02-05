# Langfuse Session Tracking in VoyageMind

## What Are Sessions?

Sessions group multiple traces together to track a complete user journey. In VoyageMind, a session represents all the travel planning requests made by a user during their browsing session.

## How It Works

### 1. Session ID Generation
```python
# routes.py
session_id = plan_request.session_id or f"voyage-{uuid.uuid4().hex[:12]}"
# Example: "voyage-a3f9d2b1c4e8"
```

### 2. Propagating Session ID
```python
with propagate_attributes(session_id=session_id):
    # All agent calls automatically get the session_id
    history_result = await history.run(country=country)
    food_result = await food.run(country=country)
    transport_result = await transport.run(country=country)
```

### 3. Frontend Tracking
```javascript
// Stores session_id across multiple requests
let currentSessionId = null;

// First request: creates new session
// Subsequent requests: reuses same session
body: JSON.stringify({ 
    country: country,
    session_id: currentSessionId 
})
```

## Session Structure in Langfuse

```
Session: voyage-a3f9d2b1c4e8
├── Trace 1: plan_travel (Japan)
│   ├── HistoryCultureAgent.run
│   ├── FoodCuisineAgent.run
│   ├── TransportationAgent.run
│   └── AggregatorAgent.run
│
├── Trace 2: plan_travel (Italy)
│   ├── HistoryCultureAgent.run
│   ├── FoodCuisineAgent.run
│   ├── TransportationAgent.run
│   └── AggregatorAgent.run
│
└── Trace 3: plan_travel (France)
    ├── HistoryCultureAgent.run
    ├── FoodCuisineAgent.run
    ├── TransportationAgent.run
    └── AggregatorAgent.run
```

## Benefits

1. **Track User Journey**
   - See all countries a user searched for in one session
   - Understand user behavior and preferences

2. **Session Metrics**
   - Total requests per session
   - Average response time across session
   - Success/failure rate

3. **Debugging**
   - Trace issues across multiple requests
   - See the full context of user interactions

4. **Session Replay**
   - View complete conversation flow
   - Understand how users interact with your app

## Viewing Sessions in Langfuse

1. **Dashboard** → Navigate to Sessions tab
2. **Find your session** → Search by `voyage-*` or filter by date
3. **View session details** → See all traces grouped together
4. **Session replay** → Watch the user journey unfold

## Session ID Format

- **Pattern**: `voyage-{12-char-hex}`
- **Example**: `voyage-a3f9d2b1c4e8`
- **Length**: 19 characters (within 200 char limit)
- **Unique**: Per browser session

## API Usage

**Request with session ID:**
```json
POST /plan
{
  "country": "Japan",
  "session_id": "voyage-a3f9d2b1c4e8"
}
```

**Response includes session ID:**
```json
{
  "country": "Japan",
  "recommendations": [...],
  "agent_details": {...},
  "session_id": "voyage-a3f9d2b1c4e8"
}
```

## Advanced: Custom Session IDs

You can provide your own session ID:

```javascript
// Use user ID as session
fetch('/plan', {
    body: JSON.stringify({ 
        country: "Japan",
        session_id: `user-${userId}-${Date.now()}`
    })
});
```

## What Gets Tracked?

✅ All agent executions (`@observe()` decorated functions)  
✅ OpenAI API calls  
✅ Input parameters (country name)  
✅ Output results (recommendations)  
✅ Execution times  
✅ Errors and exceptions  

## Session Display in UI

The session ID is shown in the header after the first request:
```
🌍 VoyageMind
Discover the Best Cities with AI-Powered Travel Planning
Session: voyage-a3f9d2b1c4e8
```

This lets users know their requests are being tracked together!
