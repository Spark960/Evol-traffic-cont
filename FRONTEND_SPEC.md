# Frontend Developer Handoff — Smart City Traffic Simulation

## Project Overview

**Title:** Evolutionary Traffic Control: Optimizing Intersection Throughput using Genetic Algorithms and V2I Priority Preemption

**What this project does:** We built an autonomous traffic controller for a 4-way intersection (North, South, East, West) that uses a **Genetic Algorithm** to dynamically adapt signal timings based on real-time traffic volume. It also handles **emergency vehicle overrides** (RFID-triggered).

**Your job:** Build the 2D visual frontend that connects to the Python backend via REST polling. You are building a "TV monitor" — the backend handles ALL simulation logic, you just **draw what it tells you to draw**.

---

## Architecture

```
┌─────────────────────────┐       HTTP GET (every 100ms)       ┌────────────────────────┐
│    Python Backend        │ ◄──────────────────────────────── │   JS/HTML Frontend      │
│    (Flask on port 5000)  │ ──────────────────────────────►   │   (Your code)           │
│                          │       JSON responses               │                        │
│  - Simulation engine     │                                    │  - Canvas/WebGL render  │
│  - GA controller         │                                    │  - Intersection visual  │
│  - Traffic physics       │                                    │  - Live charts/graphs   │
│  - Metrics collection    │                                    │  - Emergency alerts     │
└─────────────────────────┘                                    └────────────────────────┘
```

**Communication method:** Simple REST polling. No WebSockets. You call `fetch()` in a `setInterval` loop.

**Base URL:** `http://127.0.0.1:5000`

---

## How to Start the Backend

Your teammate (me) runs this in a terminal:

```bash
cd backend
pip install -r requirements.txt
python main.py --mode ga --hour 8
```

The backend will print:
```
============================================================
  Evolutionary Traffic Signal Control
============================================================
  Mode       : GA
  Start Hour : 8:00
  Seed       : 42
  API Port   : 5000
============================================================

[API] Server starting on http://127.0.0.1:5000
```

The `/state` endpoint is immediately available. Just open your `index.html` in the browser.

---

## API Endpoints — Full Reference

### 1. `GET /state` — The Main Loop Endpoint

**Poll this every 100ms.** This is the heartbeat of your frontend.

**Response:**
```json
{
  "timestamp": 4523,
  "sim_time_seconds": 452.3,
  "sim_hour": 8,
  "lights": {
    "NS": "GREEN",
    "EW": "RED"
  },
  "queues": {
    "N": 12,
    "S": 8,
    "E": 3,
    "W": 5
  },
  "emergency_active": false,
  "emergency_direction": null,
  "controller_mode": "ga",
  "current_timings": {
    "ns_green": 38.5,
    "ew_green": 21.5
  },
  "stats": {
    "total_wait_vs": 15234.5,
    "total_cleared": 1245,
    "total_arrived": 1302,
    "avg_wait": 12.24
  }
}
```

**Field-by-field breakdown:**

| Field | Type | What It Means | How You Use It |
|-------|------|---------------|----------------|
| `timestamp` | int | Tick counter (increments by 1 each tick) | Internal tracking, frame counter |
| `sim_time_seconds` | float | Simulated wall-clock seconds elapsed | Display as "Simulation Time" |
| `sim_hour` | int | Current hour of day in simulation (0–23) | Display as "Current Hour: 8:00 AM" |
| `lights.NS` | string | North/South light colour: `"GREEN"`, `"YELLOW"`, or `"RED"` | Colour the N and S traffic lights |
| `lights.EW` | string | East/West light colour: `"GREEN"`, `"YELLOW"`, or `"RED"` | Colour the E and W traffic lights |
| `queues.N` | int | Vehicles waiting at North approach | Draw N cars queued up |
| `queues.S` | int | Vehicles waiting at South approach | Draw S cars queued up |
| `queues.E` | int | Vehicles waiting at East approach | Draw E cars queued up |
| `queues.W` | int | Vehicles waiting at West approach | Draw W cars queued up |
| `emergency_active` | bool | Is an ambulance override happening right now? | Show emergency overlay/flash |
| `emergency_direction` | string or null | Which direction the ambulance is on (`"N"`, `"S"`, `"E"`, or `"W"`), or `null` | Highlight that direction |
| `controller_mode` | string | `"ga"` or `"fixed"` | Display which controller is active |
| `current_timings.ns_green` | float | Current green duration for NS phase (seconds) | Show in a "Current Timings" panel |
| `current_timings.ew_green` | float | Current green duration for EW phase (seconds) | Show in a "Current Timings" panel |
| `stats.total_wait_vs` | float | Cumulative vehicle-seconds of delay | Raw metric (use `avg_wait` instead) |
| `stats.total_cleared` | int | Total vehicles that have passed through | Display as "Vehicles Cleared" |
| `stats.total_arrived` | int | Total vehicles that have arrived | Display as "Vehicles Arrived" |
| `stats.avg_wait` | float | Average wait time per vehicle in seconds | **Key metric** — display prominently |

---

### 2. `GET /metrics` — Summary Statistics

**Poll every 1–2 seconds** (not every frame — this is for the dashboard panel).

**Response:**
```json
{
  "avg_wait_time": 18.45,
  "avg_queue_length": 6.32,
  "total_throughput": 1245,
  "ticks_recorded": 4523
}
```

| Field | What to Display |
|-------|-----------------|
| `avg_wait_time` | "Avg Wait: 18.5s" in a big stat card |
| `avg_queue_length` | "Avg Queue: 6.3 vehicles" |
| `total_throughput` | "Throughput: 1,245 vehicles" |
| `ticks_recorded` | How many ticks of data we have |

---

### 3. `GET /metrics/queues` — Queue History (for Live Charts)

**Poll every 2–5 seconds.** Returns the last 600 data points (~60 seconds of simulation).

**Response:**
```json
[
  {"tick": 3900, "N": 10, "S": 7, "E": 3, "W": 2, "total": 22},
  {"tick": 3901, "N": 11, "S": 7, "E": 2, "W": 3, "total": 23},
  {"tick": 3902, "N": 10, "S": 8, "E": 2, "W": 3, "total": 23},
  ...
]
```

Use this to render a **line chart** showing queue lengths over time. You can use Chart.js or any charting library.

---

### 4. `GET /config` — Controller Info

**Poll once on page load**, or when user switches views.

**Response:**
```json
{
  "controller_mode": "ga",
  "controller": "GAController(ns=38.5s, ew=21.5s, generations_run=150, fitness=0.0345)",
  "current_timings": {
    "ns_green": 38.5,
    "ew_green": 21.5
  }
}
```

---

### 5. `GET /history` — GA Evolution Log

**Poll every 5–10 seconds.** Only useful when running in `ga` mode.

**Response:**
```json
[
  {
    "generation": 30,
    "best_fitness": 0.034521,
    "best_ns_green": 35.2,
    "best_ew_green": 24.8,
    "queues_at_evolution": {"N": 8, "S": 5, "E": 2, "W": 3}
  },
  {
    "generation": 60,
    "best_fitness": 0.038912,
    "best_ns_green": 38.5,
    "best_ew_green": 21.5,
    "queues_at_evolution": {"N": 12, "S": 7, "E": 3, "W": 4}
  }
]
```

Use this for an "Evolution Progress" chart, showing how the GA's timings adapt over time.

---

## Your Frontend Polling Code (Copy-Paste Starter)

```javascript
const API_BASE = 'http://127.0.0.1:5000';

// ── Main state loop — 10 fps ──
setInterval(async () => {
    try {
        const res = await fetch(`${API_BASE}/state`);
        const state = await res.json();

        // Update your canvas/UI here
        updateTrafficLights(state.lights);           // {NS: "GREEN", EW: "RED"}
        drawVehicleQueues(state.queues);              // {N: 12, S: 8, E: 3, W: 5}
        updateStatsPanel(state.stats);                // avg_wait, total_cleared, etc.
        updateTimingsDisplay(state.current_timings);  // {ns_green: 38.5, ew_green: 21.5}
        updateSimClock(state.sim_hour, state.sim_time_seconds);

        if (state.emergency_active) {
            showEmergencyOverlay(state.emergency_direction);
        } else {
            hideEmergencyOverlay();
        }

    } catch (err) {
        console.error('Backend offline:', err);
    }
}, 100);  // 100ms = 10 times per second

// ── Metrics panel — every 2 seconds ──
setInterval(async () => {
    try {
        const res = await fetch(`${API_BASE}/metrics`);
        const metrics = await res.json();
        updateMetricsDashboard(metrics);
    } catch (err) { /* ignore */ }
}, 2000);

// ── Queue chart data — every 3 seconds ──
setInterval(async () => {
    try {
        const res = await fetch(`${API_BASE}/metrics/queues`);
        const queueData = await res.json();
        updateQueueChart(queueData);
    } catch (err) { /* ignore */ }
}, 3000);
```

---

## What the Frontend Should Have (Visual Components)

### 1. Intersection View (Main Visual)

A top-down 2D view of the 4-way intersection:

```
                    ▲ North
                    │
         ┌──────────┼──────────┐
         │  N Queue  │          │
         │  ■ ■ ■ ■  │          │
         │           │          │
   ◄─────┤    🚦     │     🚦   ├──────►
   West  │  (center) │ (center) │  East
         │           │          │
         │          │  ■ ■ ■   │
         │          │  S Queue  │
         └──────────┼──────────┘
                    │
                    ▼ South
```

- **Traffic lights**: 4 lights at the intersection, coloured based on `state.lights.NS` and `state.lights.EW`
  - GREEN = `#2ecc71`
  - YELLOW = `#f1c40f`
  - RED = `#e74c3c`
- **Vehicle queues**: Draw small rectangles (cars) lined up on each approach. The number of cars = `state.queues.N`, `state.queues.S`, etc.
  - When a direction has GREEN, animate cars moving through the intersection
  - When RED, cars queue up and stop
- **Emergency**: When `state.emergency_active == true`, flash the active direction's lane in red/blue, show an ambulance emoji (🚑) or icon

### 2. Stats Dashboard (Side Panel or Bottom Bar)

Display these values prominently:

| Stat | Source | Display Format |
|------|--------|----------------|
| Current Hour | `state.sim_hour` | "🕐 8:00 AM" |
| Controller | `state.controller_mode` | "🧬 Genetic Algorithm" or "⏱ Fixed-Time" |
| Avg Wait Time | `state.stats.avg_wait` | "⏳ 18.5 seconds" |
| Vehicles Cleared | `state.stats.total_cleared` | "🚗 1,245 cleared" |
| Vehicles Arrived | `state.stats.total_arrived` | "📥 1,302 arrived" |
| NS Green Time | `state.current_timings.ns_green` | "↕ NS: 38.5s" |
| EW Green Time | `state.current_timings.ew_green` | "↔ EW: 21.5s" |

### 3. Live Queue Chart

A **line chart** (use Chart.js or similar) showing queue lengths over time:
- X-axis: time (tick number)
- Y-axis: vehicles in queue
- 4 lines: N (blue), S (cyan), E (orange), W (red)
- Data comes from `GET /metrics/queues`

### 4. GA Evolution Chart (Optional but Impressive)

If in GA mode, show how the GA adapts timings over time:
- X-axis: evolution run number
- Y-axis: green duration (seconds)
- 2 lines: NS green (green line), EW green (orange line)
- Data comes from `GET /history`

---

## Recommended Frontend File Structure

```
frontend/
├── index.html          # Main page, includes canvas + dashboard
├── css/
│   └── style.css       # All styling
├── js/
│   ├── main.js         # Entry point, sets up polling loops
│   ├── api.js          # fetch() calls to backend endpoints
│   ├── renderer.js     # Canvas drawing logic for intersection
│   ├── charts.js       # Chart.js setup for live graphs
│   └── ui.js           # DOM updates for stats panel
└── assets/
    ├── car.png         # Car sprite (optional, can use rectangles)
    └── ambulance.png   # Ambulance sprite (optional)
```

---

## Important Rules

1. **The frontend is a DUMB client.** It does NOT decide light colours, does NOT move cars, does NOT calculate wait times. The backend does everything. You just render the JSON.

2. **Poll `/state` at 100ms intervals.** This is the main loop. Don't poll faster (wastes CPU), don't poll slower (looks laggy).

3. **Handle backend offline gracefully.** Wrap every `fetch()` in try/catch. If the backend isn't running, show a "Connecting..." overlay. Don't crash.

4. **CORS is handled.** The backend already uses `flask-cors`, so your `fetch()` calls from `file://` or `localhost` will work fine.

5. **Vehicle queue drawing:** You don't need to track individual car positions. Just draw N rectangles lined up along each road. The number of rectangles = the queue count from the API.

6. **Light colour values are strings:** `"GREEN"`, `"YELLOW"`, or `"RED"` — always uppercase. Map these to CSS colours in your renderer.

7. **Emergency override is rare:** The `emergency_active` flag will be `true` only occasionally (for ~15 seconds when an ambulance triggers). Make sure the visual effect is dramatic — flashing, ambulance icon, siren overlay.

---

## How to Test Without Backend

If you want to develop offline, create a mock `state` object in your JS:

```javascript
const MOCK_STATE = {
    timestamp: 100,
    sim_time_seconds: 100.0,
    sim_hour: 8,
    lights: { NS: "GREEN", EW: "RED" },
    queues: { N: 8, S: 5, E: 12, W: 3 },
    emergency_active: false,
    emergency_direction: null,
    controller_mode: "ga",
    current_timings: { ns_green: 35.0, ew_green: 25.0 },
    stats: {
        total_wait_vs: 5000.0,
        total_cleared: 450,
        total_arrived: 500,
        avg_wait: 11.1
    }
};

// Use MOCK_STATE instead of fetch() during development
```

Then swap in real `fetch()` calls when ready to connect to the backend.

---

## Quick Summary

| What | Details |
|------|---------|
| Backend runs at | `http://127.0.0.1:5000` |
| Main endpoint | `GET /state` (poll at 100ms) |
| Metrics endpoint | `GET /metrics` (poll at 2s) |
| Chart data | `GET /metrics/queues` (poll at 3s) |
| Config info | `GET /config` (poll once on load) |
| GA history | `GET /history` (poll at 5s) |
| Light values | `"GREEN"`, `"YELLOW"`, `"RED"` (uppercase strings) |
| Queue values | Integer vehicle counts per direction |
| Emergency | `emergency_active: true/false`, `emergency_direction: "N"/"S"/"E"/"W"/null` |
| Controller modes | `"ga"` or `"fixed"` |
