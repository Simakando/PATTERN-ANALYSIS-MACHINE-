# VF Signal Detector — BetPawa Virtual Football

A real-time signal and pattern detector for **BetPawa Virtual Football**, focused on **Over 3.5 Goals** markets across all virtual leagues.

---

## Features

- 🔍 **9 pattern detection algorithms** (odds ranges, team signals, H2H, streaks, draw odds, etc.)
- ⚡ **Auto-records signals** appearing in ≥10 matches
- 🤖 **Anti-bot prevention** (UA rotation, human-like delays, session management)
- 📊 **Live dashboard** with filtering, sorting, and detail views
- 📥 **Downloadable** — CSV report + JSON data files
- ♻️ **Background polling** (auto-fetches every 90–180 seconds)
- 📱 **Mobile-friendly** responsive design

---

## Leagues Tracked

| ID | League |
|----|--------|
| VFL | Virtual Football League |
| VFWC | Virtual World Cup |
| VFEC | Virtual Euro Cup |
| VFLC | Virtual Champions League |
| VFAFC | Virtual Africa Cup |
| VFPL | Virtual Premier League |
| VFLL | Virtual La Liga |
| VFBL | Virtual Bundesliga |
| VFSA | Virtual Serie A |

---

## Pattern Types Detected

1. **Odds Range** — Over 3.5 odds bracket → hit rate analysis
2. **Team Signal** — Teams consistently in high-scoring games
3. **League Pattern** — League-level over 3.5 rates
4. **Head-to-Head** — Specific matchup scoring patterns
5. **Odds Ratio Signal** — Favourite vs underdog impact on goals
6. **Draw Odds Pattern** — Draw price as goals predictor
7. **Underdog Signal** — Away underdog/favourite goal patterns
8. **Scoreline Pattern** — Most frequent scorelines
9. **Consecutive Streak** — Over 3.5 hot streaks by league

---

## Quick Start

### 1. Clone & install

```bash
git clone https://github.com/YOUR_USERNAME/betpawa-vf-detector.git
cd betpawa-vf-detector
pip install -r requirements.txt
```

### 2. Run locally

```bash
python app.py
```

Open `http://localhost:5000` in your browser.

### 3. Collect data

- Click **▶ START** for continuous background polling (auto-refreshes every 90–180s)
- Or click **⟳ SCAN NOW** for a single immediate scan
- Patterns appear automatically once ≥10 matches qualify

### 4. Download results

- **CSV Report** — Human-readable, opens in Excel/Sheets on your phone
- **JSON Patterns** — Raw pattern data for further analysis
- **JSON Matches** — All collected match results

---

## Deploy to Render / Railway / Fly.io

### Render (Free tier)

1. Fork this repo to GitHub
2. Go to [render.com](https://render.com) → New Web Service
3. Connect your GitHub repo
4. Set:
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `python app.py`
5. Deploy ✅

### Railway

```bash
railway init
railway up
```

---

## Anti-Bot Measures

The scraper uses these techniques to avoid detection:

| Measure | Implementation |
|---------|----------------|
| User-Agent rotation | Pool of 10 real mobile + desktop UAs |
| Human-like delays | Random 1.2–4.5s between requests |
| Session warming | Visits main page first to get cookies |
| Rate limit handling | 60+ second backoff on 429 responses |
| Jitter | ±20% randomness on all timing |
| Distraction pauses | 8% chance of 5–12s extra pause |
| Realistic headers | Accept-Language, Sec-Fetch-* headers |

---

## Data Schema

### Match object
```json
{
  "match_id": "abc123def456",
  "league": "Virtual Premier League",
  "home_team": "Man City",
  "away_team": "Liverpool",
  "home_score": 3,
  "away_score": 1,
  "total_goals": 4,
  "over35": true,
  "start_time": "2025-01-01T12:00:00",
  "odds": {
    "over35": 1.85,
    "under35": 1.95,
    "home_win": 1.70,
    "draw": 3.50,
    "away_win": 4.20
  }
}
```

### Pattern object
```json
{
  "type": "Odds Range",
  "league": "ALL",
  "description": "Over 3.5 odds in range 1.51–1.80 → 71.3% hit rate",
  "occurrences": 142,
  "over35_rate": 71.3,
  "avg_goals": 3.9,
  "signal_strength": 73.5,
  "details": "Odds range: 1.51–1.80 | Matches: 142 | Over3.5: 101"
}
```

---

## Notes

- Virtual football uses a **Poisson goal distribution** (λ ≈ 2.75/match)
- BetPawa virtual matches run every ~3 minutes, 24/7
- When live API is unreachable, the scraper falls back to **statistically-accurate simulation** so pattern development can continue offline
- Pattern qualification threshold: **≥10 occurrences** (configurable in `pattern_engine.py`)

---

## License

MIT — use freely, use responsibly.
