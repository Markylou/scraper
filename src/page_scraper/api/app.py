from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from page_scraper.api.routers import api_router
from page_scraper.logging_config import configure_logging, get_logger
from page_scraper.paths import ensure_project_dirs


LOGGER = get_logger("api")


def create_app() -> FastAPI:
    app = FastAPI(
        title="Page Scraper API",
        version="1.0.0",
        description="Local backend for page archiving, crawling, and content extraction",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
    )

    # CORS for SolidJS Vite dev server + common local origins
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:5173",
            "http://127.0.0.1:5173",
            "http://localhost:3000",
            "http://127.0.0.1:3000",
            "http://localhost:8080",
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Include all API routes
    app.include_router(api_router, prefix="/api")

    # Root ping for simple health checks
    @app.get("/ping")
    async def ping():
        return {
            "ok": True,
            "data": {
                "status": "up",
                "service": "page-scraper",
                "apiVersion": "1",
            },
        }

    # Consistent error envelope
    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException):
        if isinstance(exc.detail, dict) and exc.detail.get("ok") is False:
            return JSONResponse(
                status_code=exc.status_code,
                content=exc.detail,
            )
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "ok": False,
                "error": {
                    "code": "http_error",
                    "message": str(exc.detail) or "Internal server error",
                },
            },
        )

    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception):
        LOGGER.exception("Unhandled exception")
        return JSONResponse(
            status_code=500,
            content={
                "ok": False,
                "error": {
                    "code": "internal_error",
                    "message": "An unexpected error occurred",
                },
            },
        )

    return app


app = create_app()


def main() -> None:
    """Entry point for uvicorn"""
    ensure_project_dirs()
    configure_logging()

    import uvicorn

    LOGGER.info("Starting Page Scraper FastAPI server")
    print("🚀 Page Saver (FastAPI) is running at http://127.0.0.1:8765")
    print("📘 OpenAPI docs: http://127.0.0.1:8765/docs")
    print("📘 ReDoc: http://127.0.0.1:8765/redoc")

    uvicorn.run(
        "page_scraper.api.app:app",
        host="127.0.0.1",
        port=8765,
        log_level="info",
        reload=False,  # set True during heavy dev if desired
    )


if __name__ == "__main__":
    main()