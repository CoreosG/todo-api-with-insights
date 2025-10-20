import json
import logging
import os
from collections.abc import Awaitable, Callable
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from mangum import Mangum
from pydantic import BaseModel

from .controllers.task_controller import router as task_router
from .controllers.user_controller import router as user_router

# Configure logging
logging.basicConfig(
    level=logging.DEBUG if os.getenv("DEBUG") == "true" else logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)


@asynccontextmanager
async def lifespan(app: FastAPI):  # type: ignore
    """Application lifespan events."""
    # Startup
    logger = logging.getLogger(__name__)
    logger.info("Starting Todo API server...")
    yield
    # Shutdown
    logger.info("Shutting down Todo API server...")


app = FastAPI(
    title="Todo API with Insights",
    description="A serverless todo application with ETL pipeline and analytics",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)


# CORS middleware for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:8080",
        "http://localhost:3001",  # Add your frontend URLs
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Global exception handlers
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """Handle Pydantic validation errors."""
    return JSONResponse(
        status_code=422,
        content={
            "detail": "Validation error",
            "errors": exc.errors(),
            "body": exc.body,
        },
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """Handle HTTP exceptions with consistent format."""
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
    )


# Include routers with prefixes for user-scoped endpoints
app.include_router(user_router, prefix="/api/v1", tags=["users"])
app.include_router(task_router, prefix="/api/v1", tags=["tasks"])


# Health check endpoint
class HealthResponse(BaseModel):
    status: str
    version: str
    environment: str


@app.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    """Health check endpoint with system information."""
    return HealthResponse(
        status="ok",
        version="0.1.0",
        environment=os.getenv("ENVIRONMENT", "development"),
    )


# Middleware to attach API Gateway event to request state for auth extraction
@app.middleware("http")
async def add_event_to_request(
    request: Request, call_next: Callable[[Request], Awaitable[Response]]
) -> Response:
    """Attach API Gateway event to request state for authentication extraction."""
    # Check for test API Gateway event in headers (for testing)
    api_gateway_event_header = request.headers.get("X-API-Gateway-Event")
    if api_gateway_event_header:
        try:
            event_data = json.loads(api_gateway_event_header)
            request.state.event = event_data
        except json.JSONDecodeError:
            # Invalid JSON, continue without setting event
            pass

    # For Mangum, the event is available in request.scope or state
    # This is a placeholder; in production, ensure event is passed correctly
    response = await call_next(request)
    return response


# For AWS Lambda (API Gateway + Lambda)
handler = Mangum(app)
