"""Resources router."""
from typing import Optional
from fastapi import APIRouter, Request, HTTPException, Query

router = APIRouter(prefix="/api", tags=["resources"])

# IAM roles required for the GCP service account to fetch real data.
GCP_REQUIRED_ROLES = [
    {
        "role": "roles/cloudasset.viewer",
        "purpose": "List all resources via Cloud Asset Inventory API (required for Resources tab)",
    },
    {
        "role": "roles/billing.viewer",
        "purpose": "Read the billing account linked to the project (required for Billing tab)",
    },
]


@router.get("/resources/summary")
def get_resource_summary(
    request: Request,
    region: Optional[str] = Query(default=None, description="AWS region override"),
):
    """Return resource counts grouped by service type."""
    session: dict = request.app.state.session
    provider = session.get("provider")
    credentials = session.get("credentials", {})
    is_mock = session.get("mock", True)

    if not provider:
        raise HTTPException(status_code=400, detail="No cloud provider selected. Please validate credentials first.")

    api_error: str | None = None
    if provider == "gcp":
        from services.gcp_service import get_resources, _last_resources_error
        _last_resources_error.clear()
        all_resources = get_resources(credentials)
        api_error = _last_resources_error.get("error")
        if api_error and not is_mock:
            raise HTTPException(
                status_code=503,
                detail=f"Unable to retrieve GCP resource data: {api_error}",
            )
    elif provider == "aws":
        from services.aws_service import get_resources, _last_resources_error
        _last_resources_error.clear()
        all_resources = get_resources(credentials, region=region)
        api_error = _last_resources_error.get("error")
        if api_error and not is_mock:
            raise HTTPException(
                status_code=503,
                detail=f"Unable to retrieve AWS resource data: {api_error}",
            )
    else:
        raise HTTPException(status_code=400, detail="Resource summary view is only supported for GCP and AWS.")

    counts: dict[str, int] = {}
    for r in all_resources:
        t = r.get("type", "Unknown")
        counts[t] = counts.get(t, 0) + 1

    summary = sorted(
        [{"type": t, "count": c} for t, c in counts.items()],
        key=lambda x: -x["count"],
    )

    response: dict = {"summary": summary, "provider": provider}
    if api_error:
        response["api_error"] = api_error[:400]  # cap length for UI display
        if provider == "gcp" and credentials.get("project_id"):
            response["required_roles"] = GCP_REQUIRED_ROLES
    return response


@router.get("/resources")
def list_resources(
    request: Request,
    resource_types: Optional[str] = Query(default=None, description="Comma-separated resource types to fetch"),
    region: Optional[str] = Query(default=None, description="AWS region override"),
):
    session: dict = request.app.state.session
    provider = session.get("provider")
    credentials = session.get("credentials", {})
    is_mock = session.get("mock", True)

    if not provider:
        raise HTTPException(status_code=400, detail="No cloud provider selected. Please validate credentials first.")

    types_list = [t.strip() for t in resource_types.split(",") if t.strip()] if resource_types else None

    if provider == "aws":
        from services.aws_service import get_resources, get_resource_types, _last_resources_error
        _last_resources_error.clear()
        all_resources = get_resources(credentials, resource_types=types_list, region=region)
        if _last_resources_error.get("error") and not is_mock:
            raise HTTPException(
                status_code=503,
                detail=f"Unable to retrieve AWS resource data: {_last_resources_error['error']}",
            )
    elif provider == "gcp":
        from services.gcp_service import get_resources, get_resource_types, _last_resources_error
        _last_resources_error.clear()
        all_resources = get_resources(credentials)
        if types_list:
            all_resources = [r for r in all_resources if r.get("type") in types_list]
        if _last_resources_error.get("error") and not is_mock:
            raise HTTPException(
                status_code=503,
                detail=f"Unable to retrieve GCP resource data: {_last_resources_error['error']}",
            )
    elif provider == "azure":
        from services.azure_service import get_resources, get_resource_types, _last_resources_error
        _last_resources_error.clear()
        all_resources = get_resources(credentials)
        if types_list:
            all_resources = [r for r in all_resources if r.get("type") in types_list]
        if _last_resources_error.get("error") and not is_mock:
            raise HTTPException(
                status_code=503,
                detail=f"Unable to retrieve Azure resource data: {_last_resources_error['error']}",
            )
    else:
        raise HTTPException(status_code=400, detail=f"Unknown provider: {provider}")

    return {
        "resources": all_resources,
        "provider": provider,
        "resource_types": get_resource_types(credentials),
    }
