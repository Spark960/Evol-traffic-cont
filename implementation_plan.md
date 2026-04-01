# Backend Implementation Plan — Evolutionary Traffic Signal Control

Build the complete Python backend: simulation engine, GA optimizer, fixed-time baseline, data pipeline, metrics collection, and Flask API.

## Proposed Changes

### Core — Simulation Engine

#### [NEW] [intersection.py](file:///l:/vs%20code%20projects/Evol-traffic-cont/backend/core/intersection.py)

The central state machine for the 4-way intersection.
- **Phases**: `NS_GREEN`, `NS_YELLOW`, `EW_GREEN`, `EW_YELLOW` with transition logic
- **Queues**: Dict of `{N: int, S: int, E: int, W: int}` vehicle counts
- **Phase timer**: Counts down green/yellow duration, auto-transitions
- **`tick()` method**: Advances timer by 1 tick, discharges vehicles during green, transitions phases
- Yellow duration: 4 seconds (fixed, realistic)
- Configurable green durations per phase

#### [NEW] [vehicle_physics.py](file:///l:/vs%20code%20projects/Evol-traffic-cont/backend/core/vehicle_physics.py)

Constants and utility functions for discharge modeling.
- `SATURATION_FLOW_RATE = 0.5` vehicles/second (1 car per 2s headway)
- `discharge(queue_length, green_seconds, tick_duration)` → vehicles cleared per tick
- `calculate_wait_contribution(queue_length)` → cumulative wait added per tick

#### [NEW] [ga_controller.py](file:///l:/vs%20code%20projects/Evol-traffic-cont/backend/core/ga_controller.py)

The Genetic Algorithm optimizer. Runs periodically (every 60 sim-seconds), NOT per-tick.
- **Chromosome**: `[NS_green_duration, EW_green_duration]` — 2 genes
- **Gene range**: `[10, 60]` seconds, total cycle ≤ 120s
- **Population**: 30 individuals
- **Generations**: 50 per evolution run
- **Selection**: Tournament (k=3)
- **Crossover**: Single-point, rate=0.8
- **Mutation**: Gaussian (σ=5), rate=0.05
- **Elitism**: Top 2 preserved
- **Fitness**: `1 / (1 + simulated_avg_wait_time)` — evaluates each chromosome by running a mini-simulation of one full signal cycle with current queue data
- **Interface**: `evolve(current_queues) → (ns_green, ew_green)` and `get_current_timings() → (ns_green, ew_green)`

#### [NEW] [fixed_time_controller.py](file:///l:/vs%20code%20projects/Evol-traffic-cont/backend/core/fixed_time_controller.py)

Baseline controller with static timings.
- Default: NS=30s, EW=30s (configurable)
- Same interface as GA: `get_current_timings() → (ns_green, ew_green)`

---

### Data Pipeline

#### [NEW] [traffic_generator.py](file:///l:/vs%20code%20projects/Evol-traffic-cont/backend/data_pipeline/traffic_generator.py)

Converts Kaggle Metro Interstate hourly volumes into per-tick vehicle arrivals.
- Loads CSV, extracts hourly `traffic_volume` column
- Splits directionally: NS=60%, EW=40% (documented assumption)
- Further splits each direction in half (N=30%, S=30%, E=20%, W=20%)
- Converts to λ (lambda) per tick: `hourly_volume * direction_split / 3600 * tick_duration`
- Returns per-tick arrivals via `numpy.random.poisson(λ)` for each direction
- `get_arrivals(hour, tick_duration) → {N: int, S: int, E: int, W: int}`

#### [NEW] [rfid_handler.py](file:///l:/vs%20code%20projects/Evol-traffic-cont/backend/data_pipeline/rfid_handler.py)

Handles emergency vehicle events from the 4-way intersection dataset.
- Loads the Traffic Signal Control CSV
- Filters rows where `RFID == 1`
- `check_emergency(current_queues) → (bool, priority_direction)`
- When triggered: returns which direction to force green for 15 seconds

---

### Metrics

#### [NEW] [collector.py](file:///l:/vs%20code%20projects/Evol-traffic-cont/backend/metrics/collector.py)

Tracks simulation performance data for comparison graphs.
- Per-tick logging: queue lengths, wait times, throughput (vehicles cleared)
- Aggregation methods: `avg_wait_time()`, `avg_queue_length()`, `total_throughput()`
- `export_data() → list[dict]` for graphing
- `reset()` for between-experiment cleanup

---

### Server

#### [NEW] [api.py](file:///l:/vs%20code%20projects/Evol-traffic-cont/backend/server/api.py)

Flask REST API for frontend communication.
- `GET /state` → current intersection state JSON (lights, queues, timestamp, ambulance status)
- `GET /metrics` → aggregated metrics JSON
- `GET /config` → current controller type and parameters
- CORS enabled via `flask-cors`

---

### Orchestration

#### [NEW] [main.py](file:///l:/vs%20code%20projects/Evol-traffic-cont/backend/main.py)

Entry point that ties everything together.
- `threading.Lock()` for thread-safe state sharing
- Simulation loop in daemon thread with fixed 100ms timestep
- Per-tick logic:
  1. Generate arrivals via `traffic_generator`
  2. Add vehicles to intersection queues
  3. Check RFID handler for emergency override
  4. If emergency → force green on priority direction for 15s
  5. Else → use GA or fixed-time controller timings
  6. Tick intersection (discharge vehicles, transition phases)
  7. Record metrics
  8. Update shared state dict (under lock)
- GA re-evolution triggered every 60 simulated seconds
- CLI args to select controller type (`--mode ga` or `--mode fixed`)

#### [NEW] [requirements.txt](file:///l:/vs%20code%20projects/Evol-traffic-cont/backend/requirements.txt)

Dependencies: `flask`, `flask-cors`, `numpy`, `pandas`

---

## Verification Plan

### Automated Smoke Test

A script at `backend/tests/smoke_test.py` that:
1. Creates an `Intersection`, sets queues manually
2. Runs 100 ticks, verifies queues decrease during green phases
3. Creates a `GAController`, runs `evolve()` with sample queues, verifies output timings are within `[10, 60]` range
4. Creates a `FixedTimeController`, verifies output timings match configured values
5. Creates a `MetricsCollector`, logs sample data, verifies `avg_wait_time()` returns a sensible number

**Command**: `cd l:\vs code projects\Evol-traffic-cont\backend && python -m pytest tests/smoke_test.py -v`

### Manual Verification

1. **Start backend**: `cd l:\vs code projects\Evol-traffic-cont\backend && python main.py --mode ga`
2. **Hit state endpoint**: Open browser to `http://127.0.0.1:5000/state` — should return JSON with lights, queues, timestamp
3. **Hit metrics endpoint**: Open `http://127.0.0.1:5000/metrics` — should return avg wait time and throughput numbers
4. **Observe queue changes**: Refresh `/state` several times over ~10 seconds, verify timestamp increases and queues change
