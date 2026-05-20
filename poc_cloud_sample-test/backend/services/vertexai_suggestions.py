"""Vertex AI powered suggestion generation helpers."""
from __future__ import annotations

import json
import os
import re
from collections import Counter
from datetime import date
from hashlib import sha1
from typing import Any

try:
    from google import genai  # type: ignore
    from google.genai import types  # type: ignore
except Exception:  # pragma: no cover - optional dependency runtime fallback
    genai = None
    types = None

_MODEL = "gemini-3.1-flash-lite"
_MAX_RESOURCES_SAMPLE = 80
_MAX_HEURISTIC_SAMPLE = 20


def _compact_resources(resources: list[dict[str, Any]]) -> dict[str, Any]:
    type_counts = Counter((r.get("type") or "Unknown") for r in resources)
    sample: list[dict[str, Any]] = []
    for r in resources[:_MAX_RESOURCES_SAMPLE]:
        sample.append(
            {
                "name": r.get("name"),
                "type": r.get("type"),
                "status": r.get("status"),
                "region": r.get("region"),
                "size": r.get("size"),
                "machine_type": r.get("machine_type"),
                "instance_type": r.get("instance_type"),
                "public_ip": r.get("public_ip"),
                "mfa_enabled": r.get("mfa_enabled"),
            }
        )
    return {
        "total": len(resources),
        "resource_types": dict(type_counts.most_common(20)),
        "sample": sample,
    }


def _compact_billing(billing: dict[str, Any], start: date, end: date) -> dict[str, Any]:
    return {
        "requested_range": {"start_date": start.isoformat(), "end_date": end.isoformat()},
        "returned_range": {
            "start_date": billing.get("start_date"),
            "end_date": billing.get("end_date"),
        },
        "currency": billing.get("currency", "USD"),
        "total": billing.get("total", 0.0),
        "breakdown": (billing.get("breakdown") or [])[:25],
        "daily_costs": billing.get("daily_costs") or [],
    }


def _compact_iam(iam: dict[str, Any]) -> dict[str, Any]:
    if "all_bindings" in iam:
        bindings = iam.get("all_bindings") or []
        return {
            "binding_count": len(bindings),
            "sample_bindings": bindings[:40],
        }
    return {
        "users_count": len(iam.get("users") or []),
        "roles_count": len(iam.get("roles") or []),
        "groups_count": len(iam.get("groups") or []),
        "users_sample": (iam.get("users") or [])[:40],
        "roles_sample": (iam.get("roles") or [])[:40],
    }


def _extract_json_object(raw_text: str) -> dict[str, Any] | None:
    text = raw_text.strip()
    if not text:
        return None

    if text.startswith("```"):
        fenced = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.S)
        if fenced:
            text = fenced.group(1)

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    match = re.search(r"\{.*\}", text, re.S)
    if not match:
        return None
    try:
        return json.loads(match.group(0))
    except json.JSONDecodeError:
        return None


def _build_suggestion_id(provider: str, item: dict[str, Any]) -> str:
    base = "|".join(
        [
            provider,
            str(item.get("category", "")),
            str(item.get("resource_name", "")),
            str(item.get("title", "")),
        ]
    )
    digest = sha1(base.encode("utf-8")).hexdigest()[:12]
    return f"vertex-{provider}-{digest}"


def _normalize_suggestions(provider: str, suggestions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    normalized: list[dict[str, Any]] = []
    for raw in suggestions:
        if not isinstance(raw, dict):
            continue
        category = str(raw.get("category", "")).strip().lower()
        if category not in {"resources", "billing", "iam"}:
            continue
        severity = str(raw.get("severity", "info")).strip().lower()
        if severity not in {"critical", "warning", "info"}:
            severity = "info"
        suggestion_type = str(raw.get("type", "underused")).strip().lower()
        if suggestion_type not in {"overused", "underused", "security", "cost_optimization"}:
            suggestion_type = "underused"

        item: dict[str, Any] = {
            "id": _build_suggestion_id(provider, raw),
            "category": category,
            "severity": severity,
            "type": suggestion_type,
            "resource_name": str(raw.get("resource_name", "Unknown")),
            "resource_type": str(raw.get("resource_type", "Unknown")),
            "title": str(raw.get("title", "Optimization suggestion"))[:180],
            "description": str(raw.get("description", ""))[:1200],
            "current_value": str(raw.get("current_value", ""))[:500],
            "recommendation": str(raw.get("recommendation", ""))[:2000],
        }

        for numeric in ("current_cost", "estimated_savings", "estimated_savings_pct"):
            value = raw.get(numeric)
            if value is None or value == "":
                continue
            try:
                item[numeric] = round(float(value), 2)
            except (TypeError, ValueError):
                continue
        normalized.append(item)
    return normalized


def generate_vertexai_suggestions(
    provider: str,
    resources_data: list[dict[str, Any]],
    billing_data: dict[str, Any],
    iam_data: dict[str, Any],
    heuristic_suggestions: list[dict[str, Any]],
    billing_start: date,
    billing_end: date,
) -> tuple[list[dict[str, Any]], str | None]:
    """Generate additional suggestions from Vertex AI using provider data."""
    if genai is None or types is None:
        return [], "google-genai is not installed."
    project = (os.environ.get("GOOGLE_CLOUD_PROJECT") or "").strip()
    location = (os.environ.get("GOOGLE_CLOUD_LOCATION") or "us-central1").strip()
    if not project:
        return [], "GOOGLE_CLOUD_PROJECT is not configured for Vertex AI."

    payload = {
        "provider": provider.upper(),
        "resources": _compact_resources(resources_data),
        "billing": _compact_billing(billing_data, billing_start, billing_end),
        "iam": _compact_iam(iam_data),
        "heuristic_suggestions_sample": heuristic_suggestions[:_MAX_HEURISTIC_SAMPLE],
    }

    prompt = (
        "You are a senior cloud FinOps + IAM security engineer.\n"
        f"Generate highly accurate optimization suggestions for {provider.upper()}.\n"
        "Use ONLY the JSON data provided below. Do not invent resources, users, services, or costs.\n"
        "Billing analysis window is mandatory: from current date to the previous 3 months.\n"
        "Focus on resources, IAM, and billing.\n\n"
        "Return ONLY valid JSON with this structure:\n"
        "{\n"
        '  "suggestions": [\n'
        "    {\n"
        '      "category": "resources|billing|iam",\n'
        '      "severity": "critical|warning|info",\n'
        '      "type": "overused|underused|security|cost_optimization",\n'
        '      "resource_name": "string",\n'
        '      "resource_type": "string",\n'
        '      "title": "string",\n'
        '      "description": "string",\n'
        '      "current_value": "string",\n'
        '      "recommendation": "string",\n'
        '      "current_cost": 0.0,\n'
        '      "estimated_savings": 0.0,\n'
        '      "estimated_savings_pct": 0.0\n'
        "    }\n"
        "  ]\n"
        "}\n\n"
        "Rules:\n"
        "1) Keep suggestions directly grounded in provided values.\n"
        "2) Prefer specific, actionable recommendations.\n"
        "3) At most 12 total suggestions.\n"
        "4) Include billing trend guidance from the provided 3-month range.\n"
        "5) No markdown, no prose outside JSON.\n\n"
        f"INPUT_JSON:\n{json.dumps(payload, ensure_ascii=False)}"
    )

    try:
        client = genai.Client(
            vertexai=True,
            project=project,
            location=location,
        )
        contents = [
            types.Content(
                role="user",
                parts=[types.Part.from_text(text=prompt)],
            )
        ]
        tools = [types.Tool(google_search=types.GoogleSearch())]
        generate_content_config = types.GenerateContentConfig(
            temperature=0.2,
            top_p=0.95,
            max_output_tokens=65535,
            safety_settings=[
                types.SafetySetting(category="HARM_CATEGORY_HATE_SPEECH", threshold="OFF"),
                types.SafetySetting(category="HARM_CATEGORY_DANGEROUS_CONTENT", threshold="OFF"),
                types.SafetySetting(category="HARM_CATEGORY_SEXUALLY_EXPLICIT", threshold="OFF"),
                types.SafetySetting(category="HARM_CATEGORY_HARASSMENT", threshold="OFF"),
            ],
            tools=tools,
            thinking_config=types.ThinkingConfig(thinking_level="LOW"),
        )

        text_chunks: list[str] = []
        for chunk in client.models.generate_content_stream(
            model=_MODEL,
            contents=contents,
            config=generate_content_config,
        ):
            chunk_text = getattr(chunk, "text", "")
            if chunk_text:
                text_chunks.append(chunk_text)
        response_text = "".join(text_chunks).strip()
        parsed = _extract_json_object(response_text)
        if not parsed:
            return [], "Vertex AI did not return parsable JSON."
        normalized = _normalize_suggestions(provider, parsed.get("suggestions", []))
        return normalized, None
    except Exception as exc:
        return [], str(exc)[:300]
