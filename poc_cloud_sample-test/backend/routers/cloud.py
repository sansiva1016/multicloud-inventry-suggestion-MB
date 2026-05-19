"""Cloud provider info router."""
from fastapi import APIRouter

router = APIRouter(prefix="/api/cloud", tags=["cloud"])

PROVIDERS = [
    {
        "id": "aws",
        "name": "Amazon Web Services",
        "shortName": "AWS",
        "color": "#FF9900",
        "description": "Amazon Web Services – compute, storage, databases and more",
    },
    {
        "id": "gcp",
        "name": "Google Cloud Platform",
        "shortName": "GCP",
        "color": "#4285F4",
        "description": "Google Cloud – data analytics, ML, and cloud infrastructure",
    },
    {
        "id": "azure",
        "name": "Microsoft Azure",
        "shortName": "Azure",
        "color": "#0078D4",
        "description": "Microsoft Azure – hybrid cloud and enterprise services",
    },
]


@router.get("/providers")
def list_providers():
    return PROVIDERS
