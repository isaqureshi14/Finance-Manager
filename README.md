# FinWise — AI-Powered Finance Management System

A full-stack personal finance app with AI insights powered by Claude.

## Tech Stack
- **Backend**: Python (Flask) + SQLAlchemy
- **Database**: SQLite (auto-created on first run)
- **Frontend**: HTML + Tailwind CSS + Chart.js (via CDN)
- **AI**: Anthropic Claude API (claude-sonnet-4-6)

## Setup & Run

### 1. Install dependencies
```bash
cd finwise
pip install -r requirements.txt
```

### 2. Set your Anthropic API Key
```bash
# Mac/Linux
export ANTHROPIC_API_KEY="your-api-key-here"

# Windows (CMD)
set ANTHROPIC_API_KEY=your-api-key-here

# Windows (PowerShell)
$env:ANTHROPIC_API_KEY="your-api-key-here"
```
Get your key at: https://console.anthropic.com

### 3. Run the app
```bash
python app.py
```

### 4. Open in browser
```
http://localhost:5000
```

## Features

### Pages
| Page | Description |
|------|-------------|
| **Setup** | One-time profile setup (name, age, income) |
| **Dashboard** | Balance, income/expense stats, charts, recent transactions |
| **Transactions** | Add, edit, delete, filter all transactions |
| **Budgets** | Set monthly spending limits per category with progress bars |
| **Categories** | Manage income & expense categories |
| **AI Insights** | Claude-powered analysis (General, Savings Tips, Forecast) |
| **Reports** | 12-month trend charts & monthly breakdown table |

### AI Insights (Age-Aware)
- **General Analysis** — 4 prioritized insights based on your spending
- **Savings Tips** — 3 actionable savings recommendations
- **Next Month Forecast** — Predicted income, expenses, and risk areas
- All insights are tailored to your age group (Teen / Young Adult / Adult / Mid-Career / Pre-Retirement / Senior)

## Project Structure
```
finwise/
├── app.py                  # Main Flask app (routes, models, AI)
├── requirements.txt        # Python dependencies
├── instance/
│   └── finwise.db          # SQLite database (auto-created)
└── templates/
    ├── base.html           # Sidebar layout + design system
    ├── setup.html          # Onboarding page
    ├── dashboard.html      # Main dashboard
    ├── transactions.html   # Transaction CRUD
    ├── budgets.html        # Budget tracker
    ├── categories.html     # Category manager
    ├── insights.html       # AI insights panel
    └── reports.html        # Monthly reports
```

## Design System
- **Colors**: Dark navy base (#080c14), Emerald green (#10b981), Amber (#f59e0b)
- **Typography**: Plus Jakarta Sans (UI) + JetBrains Mono (numbers)
- **Charts**: Chart.js with dark theme
- **Layout**: Fixed sidebar + scrollable content area
