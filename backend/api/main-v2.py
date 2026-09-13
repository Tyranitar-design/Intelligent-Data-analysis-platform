"""
Legacy compatibility wrapper for the previous v2 entrypoint.

Canonical backend entrypoint is now `api.main:app`.
"""

from api.main import app


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
    )
