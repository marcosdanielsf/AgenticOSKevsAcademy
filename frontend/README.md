# Socialfy Dashboard

Frontend dashboard for the Socialfy multi-agent lead generation system.

## Features

- Real-time agent monitoring (23 agents across 6 squads)
- System health visualization
- Pipeline controls (start/stop)
- Task statistics and success rates

## Setup

```bash
# Install dependencies
npm install

# Run development server
npm run dev
```

Open [http://localhost:3000](http://localhost:3000)

## Backend Connection

The dashboard connects to the FastAPI backend at `http://localhost:8000`.

Start the backend first:
```bash
cd ../implementation
python api_server.py
```

## Architecture

```
frontend/
├── src/
│   ├── components/
│   │   ├── SquadCard.tsx      # Agent squad visualization
│   │   └── StatsCard.tsx      # Statistics cards
│   ├── lib/
│   │   └── api.ts             # API client
│   ├── pages/
│   │   ├── _app.tsx
│   │   ├── _document.tsx
│   │   └── index.tsx          # Main dashboard
│   └── styles/
│       └── globals.css        # Tailwind + custom styles
├── package.json
├── tailwind.config.js
└── next.config.js
```

## Squad Colors

| Squad | Color | Icon |
|-------|-------|------|
| Outbound | Blue | 🎯 |
| Inbound | Green | 📥 |
| Infrastructure | Gray | ⚙️ |
| Security | Red | 🛡️ |
| Performance | Yellow | ⚡ |
| Quality | Purple | ✅ |
