# ai lead qualification & outreach agent

ai-assisted b2b lead qualification and outreach system built with fastapi, celery, redis, postgresql, ollama, react, and vite.

this repository is a modified fork of the open-source `ai-lead-qualification-agent` project.

repository: https://github.com/haripriyatripathi/ai-lead-qualification-agent

## overview

the system accepts inbound leads, enriches company data, classifies lead attributes with a local llm, calculates a deterministic score, generates a short summary, and creates an email draft for high-priority leads.

```text
lead submission
      |
      v
fastapi api
      |
      v
postgresql + redis
      |
      v
celery worker
      |
      +--> website enrichment
      +--> llm classification
      +--> deterministic scoring
      +--> lead summary
      +--> email draft
      |
      v
react dashboard
```

## features

### lead intake

- accepts leads through the lead capture frontend or `post /leads`
- stores lead data in postgresql
- queues processing through redis and celery

### company enrichment

- extracts the domain from the lead email
- fetches the company homepage
- extracts title, meta description, and page content
- detects basic technology signals such as react, wordpress, and aws

### llm classification

ollama is used for local llm processing.

the classifier extracts:

- authority
- intent
- industry
- company size
- firmographic fit
- technology opportunity

### scoring

lead scoring is deterministic and does not use the llm directly.

| category | max score | source |
|---|---:|---|
| email trust | 20 | corporate / free / .edu |
| authority | 25 | llm classification |
| firmographic fit | 25 | llm inference |
| technology opportunity | 15 | llm + website analysis |
| intent | 15 | llm classification |

priority bands:

- high: 80+
- medium: 60-79
- low: 40-59
- very low: below 40
- rejected: academic intent

### ai summary and email draft

- generates a 5-10 word lead summary
- generates an email draft for high-priority leads
- supports view, edit, and send from the dashboard
- uses smtp for email delivery
- requires human approval before sending

### dashboard

- analytics
- lead search and filters
- priority and score display
- lead details
- confidence score
- scoring rules
- email draft view/edit/send
- email status

### event logging

processing events are stored in `lead_events`.

```text
lead_received
enqueued
lead_analyzed
lead_scored
email_generated
email_sent
email_failed
validation_adjustment
```

## architecture

the api accepts leads and queues background processing. the celery worker handles enrichment, llm classification, scoring, and email generation.

```text
                    +------------------+
                    |   react/vite     |
                    |    dashboard     |
                    |      :5173       |
                    +--------+---------+
                             |
                             v
                    +------------------+
                    |     fastapi      |
                    |      :8000       |
                    +--------+---------+
                             |
              +--------------+--------------+
              |                             |
              v                             v
      +---------------+              +---------------+
      |  postgresql   |              |     redis     |
      |     :5432     |              |     :6379     |
      +---------------+              +-------+-------+
                                              |
                                              v
                                      +---------------+
                                      | celery worker |
                                      +-------+-------+
                                              |
                                              v
                                      +---------------+
                                      |    ollama     |
                                      |    :11434     |
                                      +---------------+
```

components:

- fastapi: api, validation, routes, cors, migrations
- celery: background lead processing
- redis: celery broker and result backend
- postgresql: leads, events, scoring rules
- ollama: local llm inference
- react + vite: dashboard
- docker compose: local service orchestration

## processing pipeline

```text
1. receive lead
2. validate and store lead
3. enqueue background task
4. enrich company website
5. classify lead with llm
6. calculate deterministic score
7. generate lead summary
8. generate email draft for high-priority leads
9. update dashboard
10. optionally send email after user approval
```

## tech stack

| layer | technology |
|---|---|
| backend | python 3.11+, fastapi, uvicorn, pydantic |
| database | postgresql 15, sqlalchemy, alembic |
| worker | celery, redis |
| ai | ollama, llama3 |
| enrichment | requests, beautifulsoup4 |
| frontend | react 18, vite 5, axios |
| email | smtp |
| infrastructure | docker, docker compose |

## project structure

```text
ai-lead-qualification-agent/
|
+-- docker-compose.yml
+-- .env.example
+-- pyproject.toml
|
+-- src/
|   +-- main.py
|   +-- config.py
|   +-- api/
|   |   +-- routes/
|   +-- db/
|   |   +-- models/
|   |   +-- migrations/
|   +-- services/
|   |   +-- llm
|   |   +-- scoring
|   |   +-- enrichment
|   |   +-- email_sender
|   |   +-- lead_service
|   +-- worker/
|       +-- celery_app
|       +-- tasks
|
+-- lead-dashboard/
|   +-- src/
|   |   +-- App.jsx
|   |   +-- services/api.js
|   |   +-- components/
|   +-- package.json
|
+-- lead-capture/
    +-- src/
    |   +-- App.jsx
    |   +-- services/api.js
    +-- package.json
```

## requirements

- docker
- docker compose
- node 18+ for the react applications

## setup

clone the repository:

```bash
git clone https://github.com/haripriyatripathi/ai-lead-qualification-agent.git
cd ai-lead-qualification-agent
```

start backend services:

```bash
docker compose up -d
```

services:

- api: `http://localhost:8000`
- celery worker
- postgresql: `localhost:5432`
- redis: `localhost:6379`
- ollama: `localhost:11434`

### ollama model

the default model is `llama3`.

```bash
docker compose exec ollama ollama pull llama3
```

check installed models:

```bash
docker compose exec ollama ollama list
```

### dashboard

```bash
cd lead-dashboard
npm install
npm run dev
```

open:

```text
http://localhost:5173
```

### lead capture

from the project root, open another terminal:

```bash
cd lead-capture
npm install
npm run dev
```

open:

```text
http://localhost:5174
```

### api documentation

```text
http://localhost:8000/docs
```

## api

### submit lead

`post /leads`

```json
{
  "source": "web-form",
  "raw_payload": {
    "name": "jane smith",
    "email": "jane@acme.com",
    "company": "acme inc",
    "role": "vp of sales",
    "message": "we are evaluating ai tools for our sales team."
  }
}
```

response:

```json
{
  "id": 1,
  "status": "accepted"
}
```

the api returns `202` and the celery worker processes the lead asynchronously.

### routes

```text
get   /health
get   /health/ready
get   /scoring-rules
patch /scoring-rules/{rule_id}
get   /leads
post  /leads
get   /leads/{lead_id}
get   /leads/{lead_id}/email
post  /leads/{lead_id}/send-email
get   /analytics
```

## smtp configuration

email sending is optional.

create `.env` using `.env.example` and configure:

```env
smtp_host=smtp.gmail.com
smtp_port=587
smtp_username=your-email@gmail.com
smtp_password=your-app-password
smtp_from_email=your-email@gmail.com
```

restart services after changing environment variables:

```bash
docker compose down
docker compose up -d
```

## useful commands

```bash
# start services
docker compose up -d

# stop services
docker compose down

# service status
docker compose ps

# api logs
docker compose logs --tail=50 api

# worker logs
docker compose logs --tail=50 worker

# ollama logs
docker compose logs --tail=50 ollama

# run migrations
docker compose exec api alembic upgrade head
```

## environment variables

| variable | description |
|---|---|
| `database_url` | postgresql connection url |
| `redis_url` | redis connection url |
| `ollama_base_url` | ollama api url |
| `ollama_model` | llm model name |
| `smtp_host` | smtp server |
| `smtp_port` | smtp port |
| `smtp_username` | smtp username |
| `smtp_password` | smtp password |
| `smtp_from_email` | sender email |

see `.env.example` for the full configuration.

## development

the main processing services are separated into independent modules:

```text
api
 |
 +-- lead service
 +-- enrichment service
 +-- llm service
 +-- scoring service
 +-- email sender
 |
 +-- celery worker
```

long-running enrichment and llm tasks run in the background instead of blocking api requests.

## planned extensions

- n8n / make / zapier workflow integration
- crm integration
- richer company enrichment
- lead segmentation
- competitor data collection
- market intelligence workflows
- automated follow-up sequences
- scoring feedback loop
- improved logging and monitoring
- multi-agent orchestration

## license

mit

this repository is based on the original open-source project and retains the mit license. modifications in this fork should be documented separately from the original implementation.
