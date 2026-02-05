"""
Main FastAPI application.
"""
from fastapi import FastAPI
from routes import router

app = FastAPI(
    title="VoyageMind",
    description="AI Travel Planner",
    version="1.0.0"
)

app.include_router(router)


@app.get("/health")
async def health():
    """Health check."""
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
