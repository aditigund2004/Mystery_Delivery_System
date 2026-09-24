# FastBox Mystery Delivery System

A Python logistics simulator built to the assignment spec: given
warehouses, delivery agents, and packages, it assigns each package to
the nearest agent, simulates one day of deliveries, and reports each
agent's performance plus the most efficient agent.

## Project layout

```
fastbox_delivery/
├── delivery_system.py     # Core logic: parsing, distance, assignment,
│                           # simulation, reporting, and all bonus features
├── run_all_tests.py        # Batch-runs every data/test_case_*.json file
├── data.json                # The sample input from the assignment PDF
├── data/                    # The 10 provided test cases
│   └── test_case_1.json ... test_case_10.json
├── reports/                 # Generated after running run_all_tests.py
└── README.md
```

## How it works

1. **Parsing** (`load_data`) — reads the JSON file and does light
   structural validation (`warehouses` / `agents` / `packages` keys
   must be present).

2. **Distance** (`euclidean_distance`) — standard straight-line
   distance between two `(x, y)` points.

3. **Assignment** (`assign_packages`) — for every package, finds the
   agent whose *starting position* is closest to that package's
   warehouse (Euclidean distance), exactly as the spec describes.

4. **Simulation** (`simulate_deliveries`) — each agent then works
   through its assigned packages **in order**, travelling from
   wherever it currently is to the warehouse (pickup), then to the
   destination (drop-off), and repeating for the next package. This
   means `total_distance` reflects a realistic day of travel, not just
   isolated warehouse→destination hops.

5. **Report** (`generate_report`) — for each agent:
   - `packages_delivered`
   - `total_distance` (rounded to 2 decimals)
   - `efficiency` = `total_distance / packages_delivered` (lower is
     better — it's the average distance the agent covers per
     package)
   - `best_agent` — the agent with the **lowest** efficiency among
     agents who delivered at least one package
   - The report also includes a `_warning` field if delivered packages
     don't add up to the input total (they always do in the provided
     test cases — see below).

6. **Save** (`save_report`) — writes the report as pretty-printed
   `report.json`.

## Usage

Run against the sample data from the assignment PDF:

```bash
python delivery_system.py
```

Run against any other input file:

```bash
python delivery_system.py --input data/test_case_3.json --output report_3.json
```

Run against all 10 provided test cases at once and get a summary
table + per-case reports in `reports/`:

```bash
python run_all_tests.py
```

All 10 provided test cases pass with **100% of packages delivered**
and no warnings.

## Bonus features (all implemented)

### 1. Random delivery delays
```bash
python delivery_system.py --delays --delay-prob 0.3 --max-delay 30 --seed 42
```
Each delivery has a `--delay-prob` chance of a random delay (0 to
`--max-delay` minutes). Delays add `total_delay_minutes` and
`delayed_packages` to the report for each agent. Delays cost time, not
distance, so they don't change `total_distance` — they model real-world
friction (traffic, weather) without breaking the core distance/efficiency
metrics. Pass `--seed` for a reproducible run.

### 2. ASCII route visualization
```bash
python delivery_system.py --ascii
```
Prints an ASCII grid: `W` = warehouse, `.` = a leg of an agent's route,
and a digit/letter = where each agent ended their day. A legend maps
each glyph to its agent id.

### 3. New agent joining mid-day
```bash
python delivery_system.py --new-agent "A4:20,20:2"
```
Format: `AGENT_ID:x,y:join_after_package_index`. Packages before that
index are assigned among the original roster only; packages from that
index onward are assigned considering the new agent too. Useful for
modeling a shift change or an on-call agent being called in.

### 4. Export top performer to CSV
```bash
python delivery_system.py --export-csv top_performer.csv
```
Writes the best agent's row (id + all its stats) to a CSV file.

All bonus flags can be combined, e.g.:
```bash
python delivery_system.py --input data/test_case_5.json --ascii --delays --seed 7 --export-csv best.csv
```

## Design notes / assumptions

- The spec's example report numbers appear to be illustrative
  placeholders (they don't correspond to running the actual algorithm
  on the spec's own sample data), so this implementation prioritizes
  a sensible, well-documented simulation over matching those exact
  numbers.
- Assignment uses each agent's **starting** position only (a single
  snapshot), per "Assign each package to the nearest agent based on
  Euclidean distance from agent to warehouse." Agents are not
  reassigned mid-route based on their evolving position — that would
  be a fundamentally different (load-balancing) algorithm and isn't
  what the spec asks for.
- `efficiency` is defined as average distance per package delivered
  (lower is more efficient); `best_agent` is whichever agent has the
  lowest value.
- Coordinates are treated as plain `(x, y)` numbers with no units;
  Euclidean distance is used throughout as instructed.





the problem i face during the code is what if the the packge not exists then i add that part of the logic in the code