# Insurance Requirement Analyser

React frontend + FastAPI backend. A requirement typed into the textbox is sent to
**Amazon Comprehend** (entity detection), then the text, the entities and the unified
insurance schema are sent to **Amazon Bedrock**, which returns a customer profile JSON.
Both results are shown in the UI.

```
React (textbox) ──POST /api/analyse──> FastAPI
                                         ├─ 1. Comprehend detect_entities
                                         ├─ 2. Bedrock converse (prompt.py + schema + entities)
                                         └─ 3. Validate profile against the schema
                                       <── { comprehend, bedrock }
```

## Project layout

```
backend/
  main.py                       API, Comprehend + Bedrock calls, schema validation
  prompt.py                     Bedrock system prompt, few-shot example, prompt builder
  unifiedInsuranceSchema.json   Your schema
  requirements.txt
  .env.example
frontend/
  src/App.jsx                   Textbox, Comprehend table, Bedrock JSON view
  src/App.css
  vite.config.js                Proxies /api to localhost:8000
```

## AWS setup

1. Configure credentials (`aws configure`, an `AWS_PROFILE`, or env vars).
2. The IAM user/role needs `comprehend:DetectEntities` and `bedrock:InvokeModel`.
3. In the Bedrock console, enable access to the model you set in `BEDROCK_MODEL_ID`,
   in the same region as `AWS_REGION`. Some newer models must be called through an
   inference profile ID (for example one starting with `eu.`) instead of the plain model ID.

## Run the backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env             # then edit the values
uvicorn main:app --reload --port 8000
```

Check it at http://localhost:8000/api/health or http://localhost:8000/docs.

## Run the frontend

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:5173, click **Use example**, then **Analyse requirement**.

## API

`POST /api/analyse`

```json
{ "text": "We recently purchased a detached house in Surrey...", "customer_id": "C123" }
```

`customer_id` is optional; one is generated if you leave it out. Response:

```json
{
  "customer_id": "C123",
  "comprehend": { "entities": [{ "text": "Surrey", "type": "LOCATION", "score": 0.998 }] },
  "bedrock": { "model_id": "...", "profile": { ... }, "schema_errors": [] }
}
```

## The Bedrock prompt

Lives in `backend/prompt.py`. It has a system prompt with the extraction rules
(output format, no invented facts, number and currency conversion, Title Case labels,
customer type rules, how to place jewellery/artwork and domestic staff) and a user
message containing the schema, your example as a few-shot sample, the customer ID,
the requirement and the Comprehend entities. Temperature is 0 for consistent output.
Edit the rules there to tune how fields are mapped.
