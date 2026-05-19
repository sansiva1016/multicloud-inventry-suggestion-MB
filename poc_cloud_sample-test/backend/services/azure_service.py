"""Azure service – attempts real SDK calls, falls back to mock data on error."""
from __future__ import annotations

from datetime import date

from . import mock_service


def get_resources(credentials: dict) -> list[dict]:
    _last_resources_error.clear()
    try:
        from azure.identity import ClientSecretCredential  # type: ignore
        from azure.mgmt.resource import ResourceManagementClient  # type: ignore

        cred = ClientSecretCredential(
            tenant_id=credentials["tenant_id"],
            client_id=credentials["client_id"],
            client_secret=credentials["client_secret"],
        )
        client = ResourceManagementClient(cred, credentials["subscription_id"])
        resources: list[dict] = []
        for r in client.resources.list():
            resources.append({
                "id": r.id,
                "name": r.name,
                "type": r.type.split("/")[-1] if r.type else "Unknown",
                "region": r.location or "global",
                "status": "active",
                "tags": ",".join(f"{k}:{v}" for k, v in (r.tags or {}).items()),
            })
        return resources
    except Exception as exc:
        _last_resources_error["error"] = str(exc)
        return []


# Stores the most recent error from get_resources so the router can surface it.
_last_resources_error: dict[str, str] = {}


def get_resource_types(credentials: dict) -> list[str]:  # noqa: ARG001
    return mock_service.get_resource_types("azure")


def get_overall_billing(credentials: dict, start: date, end: date) -> dict:
    _AZURE_BILLING_NOTE = (
        "Azure billing data is not available via the current API integration. "
        "View actual costs in Azure Cost Management portal."
    )
    return {
        **mock_service.get_overall_billing("azure", start, end),
        "estimated": True,
        "note": _AZURE_BILLING_NOTE,
    }


def get_billing_by_resource_type(credentials: dict, resource_type: str, start: date, end: date) -> dict:
    _AZURE_BILLING_NOTE = (
        "Azure billing data is not available via the current API integration. "
        "View actual costs in Azure Cost Management portal."
    )
    return {
        **mock_service.get_billing_by_resource_type("azure", resource_type, start, end),
        "estimated": True,
        "note": _AZURE_BILLING_NOTE,
    }
