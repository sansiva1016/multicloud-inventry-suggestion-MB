"""AWS router – IAM and Suggestions endpoints."""
from fastapi import APIRouter, HTTPException, Request

router = APIRouter(prefix="/api/aws", tags=["aws"])


@router.get("/iam")
def get_iam(request: Request):
    """Return IAM users, roles, and groups for the AWS account."""
    session: dict = request.app.state.session
    if session.get("provider") != "aws":
        raise HTTPException(status_code=400, detail="No active AWS session.")

    from services.aws_service import get_iam_roles  # noqa: PLC0415
    return get_iam_roles(session.get("credentials", {}))


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
    return _get_suggestions(session.get("credentials", {}))
