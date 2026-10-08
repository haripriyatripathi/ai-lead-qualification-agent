# Lead Capture (Submit Lead Form)

Standalone frontend for submitting leads to the AI lead qualification agent. Runs separately from the analytics dashboard.

## Run

```bash
npm install
npm run dev
```

Runs at **http://localhost:5174** (dashboard uses 5173).

## Usage

1. Fill the form (Name, Email, Company, Role, Message).
2. Click **Submit Lead** — sends `POST http://localhost:8000/leads` with `source: "web-form"`.
3. After success, use **Go to Dashboard** to open the analytics dashboard (http://localhost:5173) and see the lead.

Ensure the backend API is running at `http://localhost:8000`.
