"""Billing router."""
from __future__ import annotations

from datetime import date
from typing import Optional

from fastapi import APIRouter, Request, HTTPException, Query

router = APIRouter(prefix="/api/billing", tags=["billing"])


def _get_session_info(request: Request):
    session: dict = request.app.state.session
    provider = session.get("provider")
    credentials = session.get("credentials", {})
    is_mock = session.get("mock", True)
    if not provider:
        raise HTTPException(status_code=400, detail="No cloud provider selected.")
    return provider, credentials, is_mock


def _default_dates() -> tuple[date, date]:
    today = date.today()
    start = today.replace(day=1)
    return start, today


@router.get("/gcp-bq-projects")
def get_gcp_bq_projects(request: Request):
    """Return the distinct GCP project IDs present in the configured BigQuery billing table."""
    provider, credentials, _ = _get_session_info(request)
    if provider != "gcp":
        raise HTTPException(status_code=400, detail="This endpoint is only available for GCP.")
    from services.gcp_service import get_bigquery_billing_projects
    return {"projects": get_bigquery_billing_projects(credentials)}


@router.get("/resource-types")
def get_resource_types(request: Request):
    provider, credentials, _ = _get_session_info(request)
    if provider == "aws":
        from services.aws_service import get_resource_types
    elif provider == "gcp":
        from services.gcp_service import get_resource_types
    elif provider == "azure":
        from services.azure_service import get_resource_types
    else:
        raise HTTPException(status_code=400, detail=f"Unknown provider: {provider}")
    return {"resource_types": get_resource_types(credentials), "provider": provider}


@router.get("/overall")
def get_overall_billing(
    request: Request,
    start_date: Optional[str] = Query(default=None),
    end_date: Optional[str] = Query(default=None),
    region: Optional[str] = Query(default=None),
    bq_project: Optional[str] = Query(default=None),
):
    provider, credentials, is_mock = _get_session_info(request)
    default_start, default_end = _default_dates()
    start = date.fromisoformat(start_date) if start_date else default_start
    end = date.fromisoformat(end_date) if end_date else default_end

    if provider == "aws":
        from services.aws_service import get_overall_billing, _last_billing_error
        _last_billing_error.clear()
        result = get_overall_billing(credentials, start, end, region=region)
        if _last_billing_error.get("error") and not is_mock:
            raise HTTPException(
                status_code=503,
                detail=f"Unable to retrieve AWS billing data: {_last_billing_error['error']}",
            )
        return result
    elif provider == "gcp":
        from services.gcp_service import get_overall_billing, _last_billing_error
        _last_billing_error.clear()
        result = get_overall_billing(credentials, start, end, bq_project=bq_project)
        # Return estimated data with a note rather than raising 503, so OAuth users
        # without BigQuery configured can still see their dashboard.
        if result.get("estimated") and not is_mock:
            raise HTTPException(
                status_code=503,
                detail=(
                    result.get("note")
                    or "GCP billing data requires Cloud Billing export to BigQuery. "
                    "Enable it in the GCP Console under Billing → Billing export."
                ),
            )
        return result
    elif provider == "azure":
        from services.azure_service import get_overall_billing
        return get_overall_billing(credentials, start, end)
    else:
        raise HTTPException(status_code=400, detail=f"Unknown provider: {provider}")


@router.get("/by-resource-type")
def get_billing_by_resource_type(
    request: Request,
    resource_type: str = Query(...),
    start_date: Optional[str] = Query(default=None),
    end_date: Optional[str] = Query(default=None),
    region: Optional[str] = Query(default=None),
    bq_project: Optional[str] = Query(default=None),
):
    provider, credentials, is_mock = _get_session_info(request)
    default_start, default_end = _default_dates()
    start = date.fromisoformat(start_date) if start_date else default_start
    end = date.fromisoformat(end_date) if end_date else default_end

    if provider == "aws":
        from services.aws_service import get_billing_by_resource_type, _last_billing_error
        _last_billing_error.clear()
        result = get_billing_by_resource_type(credentials, resource_type, start, end, region=region)
        if _last_billing_error.get("error") and not is_mock:
            raise HTTPException(
                status_code=503,
                detail=f"Unable to retrieve AWS billing data: {_last_billing_error['error']}",
            )
        return result
    elif provider == "gcp":
        from services.gcp_service import get_billing_by_resource_type, _last_billing_error
        _last_billing_error.clear()
        result = get_billing_by_resource_type(credentials, resource_type, start, end, bq_project=bq_project)
        # Return estimated data with a note rather than raising 503.
        if result.get("estimated") and not is_mock:
            raise HTTPException(
                status_code=503,
                detail=(
                    result.get("note")
                    or "GCP billing data requires Cloud Billing export to BigQuery. "
                    "Enable it in the GCP Console under Billing → Billing export."
                ),
            )
        return result
    elif provider == "azure":
        from services.azure_service import get_billing_by_resource_type
        return get_billing_by_resource_type(credentials, resource_type, start, end)
    else:
        raise HTTPException(status_code=400, detail=f"Unknown provider: {provider}")
