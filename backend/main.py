"""FastAPI backend: requirement text -> Amazon Comprehend -> Amazon Bedrock -> customer profile."""

import json
import os
import uuid
from pathlib import Path

import boto3
from botocore.exceptions import BotoCoreError, ClientError
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from jsonschema import Draft202012Validator
from pydantic import BaseModel, Field

from prompt import SYSTEM_PROMPT, build_user_prompt

load_dotenv()

AWS_REGION = os.getenv("AWS_REGION", "eu-west-2")
BEDROCK_MODEL_ID = os.getenv("BEDROCK_MODEL_ID", "anthropic.claude-3-5-sonnet-20240620-v1:0")
FRONTEND_ORIGIN = os.getenv("FRONTEND_ORIGIN", "http://localhost:5173")

# Load the unified insurance schema once at startup
SCHEMA_PATH = Path(__file__).parent / "unifiedInsuranceSchema.json"
SCHEMA = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
schema_validator = Draft202012Validator(SCHEMA)

# AWS clients
comprehend = boto3.client("comprehend", region_name=AWS_REGION)
bedrock = boto3.client("bedrock-runtime", region_name=AWS_REGION)

app = FastAPI(title="Insurance Requirement Analyser")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[FRONTEND_ORIGIN],
    allow_methods=["*"],
    allow_headers=["*"],
)


class AnalyseRequest(BaseModel):
    text: str = Field(min_length=1, max_length=5000)
    customer_id: str | None = None


# ---------- Step 1: Amazon Comprehend ----------
def extract_entities(text: str) -> list[dict]:
    response = comprehend.detect_entities(Text=text, LanguageCode="en")
    return [
        {
            "text": entity["Text"],
            "type": entity["Type"],
            "score": round(entity["Score"], 3),
        }
        for entity in response["Entities"]
    ]


# ---------- Step 2: Amazon Bedrock ----------
def parse_json(raw: str) -> dict:
    """Pulls the JSON object out of the model's reply, even if it added code fences."""
    start, end = raw.find("{"), raw.rfind("}")
    if start == -1 or end == -1:
        raise ValueError("no JSON object found in the model response")
    return json.loads(raw[start : end + 1])


def extract_profile(text: str, entities: list[dict], customer_id: str) -> dict:
    user_prompt = build_user_prompt(SCHEMA, text, entities, customer_id)

    response = bedrock.converse(
        modelId=BEDROCK_MODEL_ID,
        system=[{"text": SYSTEM_PROMPT}],
        messages=[{"role": "user", "content": [{"text": user_prompt}]}],
        inferenceConfig={"maxTokens": 2000, "temperature": 0},
    )

    content = response["output"]["message"]["content"]
    raw_text = "".join(block.get("text", "") for block in content)
    profile = parse_json(raw_text)
    profile["customer_id"] = customer_id  # always keep the ID we issued
    return profile


def validate_profile(profile: dict) -> list[str]:
    """Returns a readable list of schema problems (empty list means valid)."""
    return [
        f"{'/'.join(str(p) for p in error.path) or '(root)'}: {error.message}"
        for error in schema_validator.iter_errors(profile)
    ]


# ---------- API ----------
@app.get("/api/health")
def health():
    return {"status": "ok", "region": AWS_REGION, "model_id": BEDROCK_MODEL_ID}


@app.post("/api/analyse")
def analyse(request: AnalyseRequest):
    text = request.text.strip()
    if not text:
        raise HTTPException(status_code=400, detail="Enter a requirement to analyse.")

    customer_id = request.customer_id or f"C{uuid.uuid4().hex[:6].upper()}"

    try:
        entities = extract_entities(text)
    except (ClientError, BotoCoreError) as error:
        raise HTTPException(status_code=502, detail=f"Amazon Comprehend request failed: {error}")

    try:
        profile = extract_profile(text, entities, customer_id)
    except (ClientError, BotoCoreError) as error:
        raise HTTPException(status_code=502, detail=f"Amazon Bedrock request failed: {error}")
    except ValueError as error:
        raise HTTPException(status_code=502, detail=f"Bedrock returned invalid JSON: {error}")

    return {
        "customer_id": customer_id,
        "comprehend": {"entities": entities},
        "bedrock": {
            "model_id": BEDROCK_MODEL_ID,
            "profile": profile,
            "schema_errors": validate_profile(profile),
        },
    }
