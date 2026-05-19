# Cloud Management Console

A full-stack cloud management POC that lets you view resources and billing for **AWS**, **GCP**, and **Azure** — with realistic **mock data** so it works without real credentials.

## Architecture

```
backend/   FastAPI (Python)  →  http://localhost:8000
frontend/  React + PrimeReact →  http://localhost:3000
```

## Quick Start

### 1. Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

The API will be available at **http://localhost:8000**.  
Interactive docs: **http://localhost:8000/docs**

### 2. Frontend

```bash
cd frontend
npm install
npm run dev
```

The app will be available at **http://localhost:3000**.

## Using the App

1. **Select a cloud provider** (AWS / GCP / Azure)
2. **Enter credentials** or click **"Use Mock Data"** to skip
3. Explore the **Resources** tab — a searchable table of all cloud resources
4. Explore the **Billing** tab:
   - Summary cards and daily cost bar chart for the current month
   - Filter by resource type (EC2, S3, RDS… / Compute Engine… / Virtual Machines…)
   - Custom date range picker

## Mock Data

The backend automatically returns mock data when:
- No credentials are provided
- Real SDK calls fail (invalid credentials, network errors, etc.)

Mock data includes realistic resource names, types, regions, tags, and day-by-day billing figures for all three cloud providers.

## Credential Formats

| Provider | Required Fields |
|----------|----------------|
| AWS | `access_key_id`, `secret_access_key`, `region` (optional) |
| GCP | `project_id`, `service_account_json` (JSON string) |
| Azure | `subscription_id`, `tenant_id`, `client_id`, `client_secret` |

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/credentials/validate` | Store credentials in session |
| `DELETE` | `/api/credentials` | Clear session |
| `GET` | `/api/session` | Current session info |
| `GET` | `/api/resources` | List all resources |
| `GET` | `/api/billing/overall` | Overall billing (`start_date`, `end_date`) |
| `GET` | `/api/billing/resource-types` | Available resource type list |
| `GET` | `/api/billing/by-resource-type` | Billing for a specific type (`resource_type`, `start_date`, `end_date`) |

## Tech Stack

**Backend:** FastAPI · Pydantic · boto3 · google-cloud · azure-mgmt  
**Frontend:** React 18 · Vite · PrimeReact (lara-light-blue theme) · PrimeFlex · Recharts · Axios