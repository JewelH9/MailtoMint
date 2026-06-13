from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from contextlib import asynccontextmanager
import os

from app.config import get_settings
from app.database import engine, Base
from app.models import user, invoice  # noqa: F401
from app.core.limiter import limiter
from app.core.middleware import SecurityHeadersMiddleware, RequestSizeLimitMiddleware

settings = get_settings()


def validate_settings():
    """
    Crash loudly at startup if critical config is missing.
    Better to fail at boot than mid-request.
    """
    errors = []
    if not settings.secret_key or len(settings.secret_key) < 32:
        errors.append("SECRET_KEY must be at least 32 characters")
    if not settings.database_url:
        errors.append("DATABASE_URL is required")
    if errors:
        raise ValueError(f"Configuration errors:\n" + "\n".join(errors))


@asynccontextmanager
async def lifespan(app: FastAPI):
    validate_settings()
    Base.metadata.create_all(bind=engine)
    print("✅ Database tables ready")

    from app.services.email_worker import start_email_worker
    start_email_worker()

    yield
    print("🛑 Shutting down")


app = FastAPI(
    title="MailToMint API",
    description="AI-powered invoice and expense intelligence platform",
    version="1.0.0",
    lifespan=lifespan,
    # Never expose docs in production
    docs_url="/docs" if settings.app_env == "development" else None,
    redoc_url=None,
    # Never expose the OpenAPI schema in production
    openapi_url="/openapi.json" if settings.app_env == "development" else None,
)

# --- Rate limiter ---
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# --- Security headers ---
app.add_middleware(SecurityHeadersMiddleware)

# --- Request size limit (15MB max) ---
app.add_middleware(RequestSizeLimitMiddleware, max_body_size=15 * 1024 * 1024)

# --- CORS ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.get_allowed_origins(),
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "Accept"],
)

# --- Trusted hosts (production only) ---
if settings.app_env == "production":
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=settings.allowed_hosts.split(","),
    )


# --- Global error handler ---
# Never leak stack traces to clients
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    # Log the real error server-side
    print(f"❌ Unhandled error on {request.method} {request.url}: {exc}")
    # Return a generic message to the client
    return JSONResponse(
        status_code=500,
        content={"detail": "An unexpected error occurred. Please try again."},
    )


# --- Routers ---
from app.routers import auth, invoices, analytics, fraud, search, export, settings as settings_router

app.include_router(auth.router,            prefix="/auth",     tags=["Auth"])
app.include_router(invoices.router,        prefix="/invoices", tags=["Invoices"])
app.include_router(analytics.router,       prefix="/analytics",tags=["Analytics"])
app.include_router(fraud.router,           prefix="/fraud",    tags=["Fraud"])
app.include_router(search.router,          prefix="/search",   tags=["Search"])
app.include_router(export.router,          prefix="/export",   tags=["Export"])
app.include_router(settings_router.router, prefix="/settings", tags=["Settings"])

# --- Static file serving ---
os.makedirs("uploads", exist_ok=True)
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")


@app.get("/health", tags=["System"])
def health_check():
    return {
        "status": "ok",
        "app": "MailToMint",
        "version": "1.0.0",
    }