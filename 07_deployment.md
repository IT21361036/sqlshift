# Deployment — SQL Modernization Accelerator

## Three Environments

| Environment | Where | Database | How to start |
|-------------|-------|----------|-------------|
| Local dev | Your laptop | SQLite | `docker-compose up --build` |
| Staging | Azure Container Apps (dev slot) | Azure SQL | Auto on merge to `main` |
| Production | Azure Container Apps (prod slot) | Azure SQL | Manual promote from staging |

---

## Local Development

### Start the full stack

```bash
# Clone and setup
git clone https://github.com/YOUR_USERNAME/sql-modernization-agent
cd sql-modernization-agent
cp .env.example .env
# Fill in your Azure OpenAI credentials in .env

# Start with Docker Compose (hot reload included)
docker-compose up --build

# Or run without Docker
pip install -r requirements.txt
python manage.py init_db
uvicorn api.main:app --reload --port 8000
```

### Test via CLI (no web server needed)

```bash
python run_cli.py \
  --input sample_sql/legacy_cursor.sql \
  --source tsql \
  --target postgresql
```

### Run tests

```bash
pytest tests/
pytest tests/test_pipeline_e2e.py -v   # full end-to-end
```

---

## Docker Setup

### `Dockerfile`

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN python manage.py init_db

EXPOSE 8000

CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### `docker-compose.yml`

```yaml
version: "3.9"

services:
  app:
    build: .
    ports:
      - "8000:8000"
    volumes:
      - .:/app          # hot reload in dev
      - ./data:/app/data
    env_file:
      - .env
    command: uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload
```

---

## GitHub Actions CI/CD

### `.github/workflows/ci.yml`

```yaml
name: CI

on:
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
      - run: pip install -r requirements.txt
      - run: python manage.py init_db
      - run: pytest tests/ -v
        env:
          DATABASE_URL: sqlite:///./data/test.db
          AZURE_OPENAI_ENDPOINT: ${{ secrets.AZURE_OPENAI_ENDPOINT }}
          AZURE_OPENAI_API_KEY: ${{ secrets.AZURE_OPENAI_API_KEY }}
          AZURE_OPENAI_DEPLOYMENT: gpt-4o
```

### `.github/workflows/deploy.yml`

```yaml
name: Deploy

on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Log in to Azure
        uses: azure/login@v1
        with:
          creds: ${{ secrets.AZURE_CREDENTIALS }}

      - name: Build and push Docker image
        run: |
          az acr build \
            --registry ${{ secrets.ACR_NAME }} \
            --image sql-modernizer:${{ github.sha }} \
            .

      - name: Deploy to Azure Container Apps
        run: |
          az containerapp update \
            --name sql-modernizer \
            --resource-group ${{ secrets.RESOURCE_GROUP }} \
            --image ${{ secrets.ACR_NAME }}.azurecr.io/sql-modernizer:${{ github.sha }}

      - name: Health check
        run: |
          sleep 10
          curl -f https://sql-modernizer.azurecontainerapps.io/health
```

---

## Azure Deployment (Hackathon Day 2)

### Step 1 — Login

```bash
azd auth login
az login
```

### Step 2 — Initialize project (once only)

```bash
azd init
# Select: Use existing template or start fresh
# Give your project a name: sql-modernizer
```

### Step 3 — Deploy everything

```bash
azd up
# This provisions:
#   - Azure Container Registry
#   - Azure Container Apps environment
#   - Azure Key Vault (stores OpenAI API key)
#   - Azure Monitor + App Insights
#   - Optional: Azure SQL
# Then builds Docker image, pushes, and deploys.
```

### Step 4 — Verify

```bash
# Check logs
azd monitor

# Test the live endpoint
curl -X POST https://YOUR-APP.azurecontainerapps.io/modernize \
  -H "Content-Type: application/json" \
  -d '{"sql": "SELECT * FROM emp WHERE ROWNUM <= 10", "source_dialect": "plsql", "target_dialect": "postgresql"}'
```

### Step 5 — Open Azure Monitor

```bash
azd monitor
# Opens browser to Azure Monitor dashboard
# See: agent call chains, response times, error rates
```

---

## Azure Resources Provisioned by `azd up`

| Resource | Purpose |
|----------|---------|
| Azure Container Registry | Stores Docker image |
| Azure Container Apps | Runs the application, auto-scales to zero |
| Azure Key Vault | Stores `AZURE_OPENAI_API_KEY` securely |
| Azure Monitor + App Insights | Logs, traces, agent observability |
| Azure SQL (optional) | Managed database for production |

---

## GitHub Secrets Required

Set these in your GitHub repo → Settings → Secrets → Actions:

| Secret | Value |
|--------|-------|
| `AZURE_CREDENTIALS` | JSON output of `az ad sp create-for-rbac` |
| `AZURE_OPENAI_ENDPOINT` | Your Azure OpenAI resource URL |
| `AZURE_OPENAI_API_KEY` | Your API key |
| `ACR_NAME` | Your Container Registry name |
| `RESOURCE_GROUP` | Your Azure resource group name |
