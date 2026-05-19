"""FastAPI main application entry point."""
from __future__ import annotations

from typing import Any

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from routers import cloud, resources, billing
from routers.gcp_oauth import router as gcp_oauth_router
from routers.aws import router as aws_router

app = FastAPI(title="Cloud Management API", version="1.0.0")

# In-memory session (single-user POC)
app.state.session: dict[str, Any] = {}

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173", "http://127.0.0.1:3000", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def no_cache_middleware(request: Request, call_next) -> Response:
    """Prevent browsers from caching any API response."""
    response = await call_next(request)
    response.headers["Cache-Control"] = "private, no-store, no-cache, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response

app.include_router(cloud.router)
app.include_router(resources.router)
app.include_router(billing.router)
app.include_router(gcp_oauth_router)
app.include_router(aws_router)


# ---------------------------------------------------------------------------
# Credentials
# ---------------------------------------------------------------------------

class CredentialsRequest(BaseModel):
    provider: str
    credentials: dict[str, str]


@app.post("/api/credentials/validate")
def validate_credentials(payload: CredentialsRequest):
    """Store provider + credentials in session; return validation result."""
    provider = payload.provider.lower()
    valid_providers = {"aws", "gcp", "azure"}
    if provider not in valid_providers:
        return {"valid": False, "message": f"Unknown provider '{provider}'. Choose aws, gcp, or azure."}

    # Basic field validation
    creds = payload.credentials
    missing = []
    if provider == "aws":
        for field in ("access_key_id", "secret_access_key"):
            if not creds.get(field):
                missing.append(field)
    elif provider == "gcp":
        # OAuth credentials are validated via /api/gcp/oauth/init + callback.
        # For service-account flow, require both project_id and service_account_json.
        if creds.get("auth_type") != "oauth":
            for field in ("project_id", "service_account_json"):
                if not creds.get(field):
                    missing.append(field)
    elif provider == "azure":
        for field in ("subscription_id", "tenant_id", "client_id", "client_secret"):
            if not creds.get(field):
                missing.append(field)

    if missing:
        # Store session so the dashboard can still function (needed for "Use Mock Data" flow)
        app.state.session = {"provider": provider, "credentials": creds, "mock": True}
        return {
            "valid": False,
            "message": f"Missing required fields: {', '.join(missing)}.",
        }

    # For AWS, verify credentials are actually valid by calling STS
    if provider == "aws":
        try:
            import boto3  # type: ignore
            from botocore.config import Config  # type: ignore
            sts = boto3.client(
                "sts",
                aws_access_key_id=creds.get("access_key_id"),
                aws_secret_access_key=creds.get("secret_access_key"),
                region_name=creds.get("region", "us-east-1"),
                config=Config(connect_timeout=5, read_timeout=5, retries={"max_attempts": 1}),
            )
            sts.get_caller_identity()
        except Exception as exc:
            return {
                "valid": False,
                "message": f"AWS credentials could not be verified ({str(exc)[:200]}). Please check your credentials.",
            }

    # For GCP, verify service-account credentials by fetching project info via Resource Manager.
    # OAuth credentials are already verified during the OAuth callback flow.
    if provider == "gcp" and creds.get("auth_type") != "oauth":
        try:
            import json as _json
            from google.oauth2 import service_account as _sa  # type: ignore
            from googleapiclient import discovery as _disc  # type: ignore

            sa_info = _json.loads(creds.get("service_account_json", "{}"))
            gcp_creds = _sa.Credentials.from_service_account_info(
                sa_info,
                scopes=["https://www.googleapis.com/auth/cloud-platform"],
            )
            project_id = creds.get("project_id")
            crm = _disc.build(
                "cloudresourcemanager", "v1", credentials=gcp_creds,
                cache_discovery=False,
            )
            crm.projects().get(projectId=project_id).execute()
        except Exception as exc:
            return {
                "valid": False,
                "message": f"GCP credentials could not be verified ({str(exc)[:200]}). Please check your credentials.",
            }

    app.state.session = {"provider": provider, "credentials": creds, "mock": False}
    return {"valid": True, "mock": False, "message": "Credentials accepted. Connecting to cloud..."}


@app.delete("/api/credentials")
def clear_credentials():
    app.state.session = {}
    return {"message": "Session cleared."}


@app.get("/api/session")
def get_session():
    session = app.state.session
    if not session:
        return {"active": False}
    response: dict = {
        "active": True,
        "provider": session.get("provider"),
        "mock": session.get("mock", True),
    }
    if session.get("provider") == "gcp":
        creds = session.get("credentials", {})
        response["project_id"] = creds.get("project_id", "")
        response["has_gcp_projects"] = bool(session.get("gcp_projects"))
        response["has_gcp_organizations"] = bool(session.get("gcp_organizations"))
        response["bigquery_dataset"] = creds.get("bigquery_dataset", "")
        response["bigquery_table"] = creds.get("bigquery_table", "")
    return response


@app.get("/")
def root():
    return {"message": "Cloud Management API is running."}
