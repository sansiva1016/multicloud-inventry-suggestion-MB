"""GCP OAuth 2.0 login router.

Endpoints:
  POST /api/gcp/oauth/init        – uses GCP_CLIENT_ID / GCP_CLIENT_SECRET from
                                     the server .env file (optionally overridden in
                                     the request body); stores pending credentials
                                     in session and returns the Google OAuth URL.
  GET  /api/gcp/oauth/callback    – handles the redirect from Google, exchanges
                                     the auth code for tokens, auto-discovers
                                     accessible organizations and projects, stores
                                     credentials in session, and redirects to the
                                     frontend.
  GET  /api/gcp/organizations     – returns the list of GCP organizations
                                     accessible to the authenticated user.
  POST /api/gcp/select-org        – stores the chosen organization ID in session
                                     and returns projects belonging to that org.
  GET  /api/gcp/projects          – returns accessible GCP projects, optionally
                                     filtered by organization ID.
  POST /api/gcp/select-project    – sets the chosen project ID in the session.
  GET  /api/gcp/iam               – returns the authenticated user's IAM roles and
                                     the full project IAM policy.
"""
from __future__ import annotations

import os

from dotenv import load_dotenv
from fastapi import APIRouter, Query, Request
from fastapi.responses import RedirectResponse
from pydantic import BaseModel

# Load environment variables from .env file if present
load_dotenv()

# Pre-configured GCP OAuth credentials from environment (optional)
_GCP_CLIENT_ID = os.environ.get("GCP_CLIENT_ID", "")
_GCP_CLIENT_SECRET = os.environ.get("GCP_CLIENT_SECRET", "")

router = APIRouter(prefix="/api/gcp", tags=["gcp-oauth"])

_SCOPES = [
    "https://www.googleapis.com/auth/cloud-platform",
    "openid",
    "https://www.googleapis.com/auth/userinfo.email",
]

# Allow deployment-specific overrides via environment variables.
_BACKEND_BASE = os.environ.get("GCP_OAUTH_BACKEND_BASE", "http://localhost:8000")
_FRONTEND_BASE = os.environ.get("GCP_OAUTH_FRONTEND_BASE", "http://localhost:3000")
_REDIRECT_URI = f"{_BACKEND_BASE}/api/gcp/oauth/callback"
_FRONTEND_SUCCESS = f"{_FRONTEND_BASE}/?gcp_auth=success"
_FRONTEND_SELECT_ORG = f"{_FRONTEND_BASE}/?gcp_auth=select_org"
_FRONTEND_SELECT = f"{_FRONTEND_BASE}/?gcp_auth=select_project"
_FRONTEND_ERROR = f"{_FRONTEND_BASE}/?gcp_auth=error"


class GcpOAuthInitRequest(BaseModel):
    client_id: str = ""
    client_secret: str = ""
    bigquery_dataset: str = ""
    bigquery_table: str = ""


class GcpBillingConfigRequest(BaseModel):
    bigquery_dataset: str = ""
    bigquery_table: str = ""


class GcpSelectOrgRequest(BaseModel):
    org_id: str


class GcpSelectProjectRequest(BaseModel):
    project_id: str


def _list_user_organizations(gcp_creds) -> list[dict]:
    """Return GCP organizations accessible to the authenticated user.

    Uses the Cloud Resource Manager v3 organizations.search() API.
    Returns an empty list if the user has no organization access.
    """
    try:
        from googleapiclient import discovery  # type: ignore
        crm = discovery.build(
            "cloudresourcemanager", "v3", credentials=gcp_creds, cache_discovery=False
        )
        result = crm.organizations().search().execute()
        orgs = []
        for org in result.get("organizations", []):
            if org.get("state") != "ACTIVE":
                continue
            raw_name = org.get("name", "")  # e.g. "organizations/123456789"
            org_id = raw_name.split("/")[-1] if "/" in raw_name else raw_name
            orgs.append({
                "org_id": org_id,
                "name": org.get("displayName", org_id),
            })
        return orgs
    except Exception:
        return []


def _list_user_projects(gcp_creds, org_id: str = "") -> list[dict]:
    """Return all active GCP projects accessible with the given credentials.

    If *org_id* is provided, only projects whose parent is that organization
    are returned.  Tries the Cloud Resource Manager v1 API first; falls back
    to v3 (which uses a different endpoint) if v1 fails.
    """
    def _from_v1():
        from googleapiclient import discovery  # type: ignore
        crm = discovery.build(
            "cloudresourcemanager", "v1", credentials=gcp_creds, cache_discovery=False
        )
        result = crm.projects().list().execute()
        projects = [
            {"project_id": p["projectId"], "name": p.get("name", p["projectId"]), "parent": p.get("parent", {})}
            for p in result.get("projects", [])
            if p.get("lifecycleState") == "ACTIVE"
        ]
        if org_id:
            projects = [
                p for p in projects
                if str(p.get("parent", {}).get("id", "")) == str(org_id)
            ]
        # Normalize: remove the raw parent dict before returning
        return [{"project_id": p["project_id"], "name": p["name"]} for p in projects]

    def _from_v3():
        from googleapiclient import discovery  # type: ignore
        crm = discovery.build(
            "cloudresourcemanager", "v3", credentials=gcp_creds, cache_discovery=False
        )
        query = f"parent:organizations/{org_id}" if org_id else ""
        kwargs: dict = {}
        if query:
            kwargs["query"] = query
        result = crm.projects().search(**kwargs).execute()
        return [
            {"project_id": p["projectId"], "name": p.get("displayName", p["projectId"])}
            for p in result.get("projects", [])
            if p.get("state") == "ACTIVE"
        ]

    for fn in (_from_v1, _from_v3):
        try:
            projects = fn()
            if projects:
                return projects
        except Exception:
            pass
    return []


@router.post("/oauth/init")
def init_oauth(payload: GcpOAuthInitRequest, request: Request):
    """Store OAuth client credentials in session and return the Google auth URL."""
    # Use env-var credentials when the frontend does not supply them
    client_id = payload.client_id or _GCP_CLIENT_ID
    client_secret = payload.client_secret or _GCP_CLIENT_SECRET

    if not client_id or not client_secret:
        return {"error": "GCP OAuth credentials are not configured. Set GCP_CLIENT_ID and GCP_CLIENT_SECRET in the .env file."}

    try:
        from google_auth_oauthlib.flow import Flow  # type: ignore

        client_config = {
            "web": {
                "client_id": client_id,
                "client_secret": client_secret,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": [_REDIRECT_URI],
            }
        }

        flow = Flow.from_client_config(client_config, scopes=_SCOPES, redirect_uri=_REDIRECT_URI)
        auth_url, state = flow.authorization_url(
            access_type="offline",
            include_granted_scopes="true",
            prompt="consent",
        )

        # Preserve any existing session data while storing the pending OAuth state
        request.app.state.session = {
            **request.app.state.session,
            "pending_gcp": {
                "client_id": client_id,
                "client_secret": client_secret,
                "bigquery_dataset": payload.bigquery_dataset,
                "bigquery_table": payload.bigquery_table,
                "oauth_state": state,
            },
        }
        return {"auth_url": auth_url}
    except Exception as exc:
        return {"error": f"Failed to generate auth URL: {str(exc)[:300]}"}


@router.get("/oauth/callback")
def oauth_callback(
    request: Request,
    code: str = None,
    error: str = None,
    state: str = None,
):
    """Handle the OAuth redirect from Google."""
    if error:
        return RedirectResponse(f"{_FRONTEND_ERROR}&reason={error}")
    if not code:
        return RedirectResponse(f"{_FRONTEND_ERROR}&reason=no_code")

    session = request.app.state.session
    pending = session.get("pending_gcp", {})

    client_id = pending.get("client_id", "")
    client_secret = pending.get("client_secret", "")

    if not client_id or not client_secret:
        return RedirectResponse(f"{_FRONTEND_ERROR}&reason=missing_client_credentials")

    # Validate the OAuth state parameter to prevent CSRF attacks
    stored_state = pending.get("oauth_state", "")
    if stored_state and state != stored_state:
        return RedirectResponse(f"{_FRONTEND_ERROR}&reason=state_mismatch")

    try:
        from google_auth_oauthlib.flow import Flow  # type: ignore

        client_config = {
            "web": {
                "client_id": client_id,
                "client_secret": client_secret,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": [_REDIRECT_URI],
            }
        }
        flow = Flow.from_client_config(client_config, scopes=_SCOPES, redirect_uri=_REDIRECT_URI)
        flow.fetch_token(code=code)
        gcp_creds = flow.credentials
    except Exception as exc:
        import logging
        logging.getLogger(__name__).error("GCP OAuth token exchange failed: %s", exc)
        return RedirectResponse(f"{_FRONTEND_ERROR}&reason=token_exchange_failed")

    # Auto-discover GCP organizations and projects accessible to this user
    organizations = _list_user_organizations(gcp_creds)
    projects = _list_user_projects(gcp_creds)

    base_credentials: dict = {
        "auth_type": "oauth",
        "project_id": "",
        "client_id": client_id,
        "client_secret": client_secret,
        "token": gcp_creds.token,
        "refresh_token": gcp_creds.refresh_token,
        "token_uri": "https://oauth2.googleapis.com/token",
        "scopes": list(gcp_creds.scopes or _SCOPES),
        "bigquery_dataset": pending.get("bigquery_dataset", ""),
        "bigquery_table": pending.get("bigquery_table", ""),
        "gcp_projects": projects,
    }

    if organizations:
        # Ask the user to pick an organization first, then a project
        request.app.state.session = {
            "provider": "gcp",
            "credentials": base_credentials,
            "gcp_organizations": organizations,
            "gcp_projects": projects,
            "mock": False,
        }
        return RedirectResponse(_FRONTEND_SELECT_ORG)

    if projects:
        # No organisations but projects exist – go straight to project selection
        request.app.state.session = {
            "provider": "gcp",
            "credentials": base_credentials,
            "gcp_projects": projects,
            "mock": False,
        }
        return RedirectResponse(_FRONTEND_SELECT)

    # No projects discovered (permission issue or empty account) – proceed anyway
    request.app.state.session = {
        "provider": "gcp",
        "credentials": base_credentials,
        "mock": False,
    }
    return RedirectResponse(_FRONTEND_SUCCESS)


@router.get("/organizations")
def list_organizations(request: Request):
    """Return the GCP organizations discovered during OAuth."""
    session: dict = request.app.state.session
    return {"organizations": session.get("gcp_organizations", [])}


@router.post("/select-org")
def select_org(payload: GcpSelectOrgRequest, request: Request):
    """Store the chosen organization and return its projects."""
    session: dict = request.app.state.session
    if session.get("provider") != "gcp":
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail="No active GCP session.")

    # Rebuild credentials object with the selected org
    creds = dict(session.get("credentials", {}))

    # Re-build GCP credentials to fetch projects filtered by this org
    try:
        gcp_creds = _build_session_creds(creds)
        projects = _list_user_projects(gcp_creds, org_id=payload.org_id)
    except Exception:
        projects = []

    # Fall back to the full project list if org-filtered fetch returns nothing
    if not projects:
        all_projects: list[dict] = session.get("gcp_projects", [])
        projects = all_projects

    request.app.state.session = {
        **session,
        "credentials": creds,
        "gcp_selected_org": payload.org_id,
        "gcp_org_projects": projects,
    }
    return {"org_id": payload.org_id, "projects": projects}


def _build_session_creds(creds: dict):
    """Reconstruct google.oauth2 credentials from the session dict."""
    import google.oauth2.credentials as _gc  # type: ignore
    return _gc.Credentials(
        token=creds.get("token"),
        refresh_token=creds.get("refresh_token"),
        token_uri=creds.get("token_uri", "https://oauth2.googleapis.com/token"),
        client_id=creds.get("client_id"),
        client_secret=creds.get("client_secret"),
        scopes=creds.get("scopes"),
    )


@router.get("/projects")
def list_projects(request: Request, org_id: str = Query(default="")):
    """Return GCP projects for the authenticated user.

    If *org_id* is provided, only projects belonging to that organization are
    returned.  When the session already contains org-filtered projects (set by
    POST /select-org) they are returned directly to avoid redundant API calls.

    When no projects are cached in the session (because auto-discovery failed
    at OAuth callback time), a live fetch is attempted using the stored OAuth
    credentials so the user always gets a fresh list.
    """
    session: dict = request.app.state.session

    # If an org was already selected and its projects are cached, serve them.
    if org_id and session.get("gcp_selected_org") == org_id:
        return {"projects": session.get("gcp_org_projects", [])}

    creds_dict = session.get("credentials", {})

    if org_id:
        # Fetch projects for this org on demand
        try:
            gcp_creds = _build_session_creds(creds_dict)
            projects = _list_user_projects(gcp_creds, org_id=org_id)
        except Exception:
            projects = session.get("gcp_projects", [])
        return {"projects": projects}

    # No org filter – return cached projects.
    # If the cache is empty (discovery failed at OAuth time) and we have valid
    # OAuth credentials, attempt a live re-fetch so the user sees their projects.
    cached = session.get("gcp_projects", [])
    if not cached and creds_dict.get("auth_type") == "oauth":
        try:
            gcp_creds = _build_session_creds(creds_dict)
            live_projects = _list_user_projects(gcp_creds)
            if live_projects:
                # Cache the result so subsequent calls don't re-fetch
                request.app.state.session = {
                    **session,
                    "gcp_projects": live_projects,
                }
                return {"projects": live_projects}
        except Exception:
            pass

    return {"projects": cached}


@router.post("/select-project")
def select_project(payload: GcpSelectProjectRequest, request: Request):
    """Set the active GCP project in the session."""
    session: dict = request.app.state.session
    if session.get("provider") != "gcp":
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail="No active GCP session.")

    creds = dict(session.get("credentials", {}))
    creds["project_id"] = payload.project_id
    request.app.state.session = {**session, "credentials": creds}
    return {"project_id": payload.project_id, "message": "Project selected."}


@router.post("/billing-config")
def update_billing_config(payload: GcpBillingConfigRequest, request: Request):
    """Update the BigQuery billing dataset and table in the session credentials."""
    session: dict = request.app.state.session
    if session.get("provider") != "gcp":
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail="No active GCP session.")

    creds = dict(session.get("credentials", {}))
    creds["bigquery_dataset"] = payload.bigquery_dataset
    creds["bigquery_table"] = payload.bigquery_table
    request.app.state.session = {**session, "credentials": creds}
    return {"message": "Billing configuration updated."}


@router.get("/iam")
def get_iam_roles(request: Request):
    """Return IAM roles and bindings for the authenticated GCP user."""
    session: dict = request.app.state.session
    if session.get("provider") != "gcp":
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail="No active GCP session.")

    from services.gcp_service import get_iam_roles  # noqa: PLC0415
    return get_iam_roles(session.get("credentials", {}))


@router.get("/suggestions")
def get_suggestions(request: Request):
    """Analyse GCP resources, billing, and IAM to return actionable suggestions.

    Each suggestion indicates whether a resource is over-used (provisioned
    beyond actual need) or under-used (cost-saving / security feature not
    enabled), along with a recommended remediation.
    """
    session: dict = request.app.state.session
    if session.get("provider") != "gcp":
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail="No active GCP session.")

    from services.gcp_service import get_suggestions as _get_suggestions  # noqa: PLC0415
    return _get_suggestions(session.get("credentials", {}))
