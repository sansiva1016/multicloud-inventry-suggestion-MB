"""AWS router – IAM and Suggestions endpoints."""
from fastapi import APIRouter, HTTPException, Request

router = APIRouter(prefix="/api/aws", tags=["aws"])


def _sanitize_service_response(payload):
    if not isinstance(payload, dict):
        return {"error": "Unable to retrieve AWS data."}
    return {
        "account_id": payload.get("account_id"),
        "users": payload.get("users", []),
        "roles": payload.get("roles", []),
        "groups": payload.get("groups", []),
        "policies": payload.get("policies", []),
        "error": (
            "Unable to retrieve full provider details for this section."
            if payload.get("error")
            else None
        ),
    }


def _sanitize_suggestions_response(payload):
    if not isinstance(payload, dict):
        return {"suggestions": [], "summary": {}, "resources_error": None, "billing_error": None, "iam_error": None}
    return {
        "suggestions": payload.get("suggestions", []),
        "summary": payload.get("summary", {}),
        "resources_error": (
            "Unable to retrieve full provider details for this section."
            if payload.get("resources_error")
            else None
        ),
        "billing_error": (
            "Unable to retrieve full provider details for this section."
            if payload.get("billing_error")
            else None
        ),
        "iam_error": (
            "Unable to retrieve full provider details for this section."
            if payload.get("iam_error")
            else None
        ),
        "billing_period": payload.get("billing_period"),
    }


@router.get("/iam")
def get_iam(request: Request):
    """Return IAM users, roles, and groups for the AWS account."""
    session: dict = request.app.state.session
    if session.get("provider") != "aws":
        raise HTTPException(status_code=400, detail="No active AWS session.")

    from services.aws_service import get_iam_roles  # noqa: PLC0415
    return _sanitize_service_response(get_iam_roles(session.get("credentials", {})))


@router.get("/suggestions")
def get_suggestions(request: Request):
    """Analyse AWS resources, billing, and IAM to return actionable suggestions.

    Each suggestion indicates whether a resource is over-used (provisioned
    beyond actual need) or under-used (cost-saving / security feature not
    enabled), along with a recommended remediation.
    """
    session: dict = request.app.state.session
    if session.get("provider") != "aws":
        raise HTTPException(status_code=400, detail="No active AWS session.")

    from services.aws_service import get_suggestions as _get_suggestions  # noqa: PLC0415
    return _sanitize_suggestions_response(_get_suggestions(session.get("credentials", {})))
