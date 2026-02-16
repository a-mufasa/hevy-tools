# Strong CSV Migrator

Migrates historical workout data from Google Sheets CSV format to Strong CSV format for importing into the Hevy app.

## Overview

This tool was built to migrate ~18 months of workout data (274 workouts, 3,345 sets) from Google Sheets tracking format into Hevy. It handles two workout programs:

- **PPL (Push, Pull, Legs)**: 23 weeks, 8-day cycle with A/B variations
- **ULPPL (Upper, Lower, Push, Pull, Legs)**: 30 weeks, 7-day cycle

Key features:
- Calculates workout dates **backwards from end date** (more reliable than parsing filenames)
- Filters by TRUE/FALSE completion column (skips incomplete exercises)
- Maps exercise names to Hevy-compatible names (prevents "Custom" exercises)
- Generates Strong CSV format that Hevy can import

## What is the Strong CSV Format?

The Strong app uses a semicolon-delimited CSV format. Hevy can import this format via "Import from Strong" option.

### Required Columns

| Column | Required | Description |
|--------|----------|-------------|
| Date | Yes | Workout date in `YYYY-MM-DD HH:MM:SS` format |
| Workout Name | Yes | Name of the workout routine |
| Exercise Name | Yes | Name of the exercise performed |
| Set Order | Yes | Order of the set within the exercise |
| Weight | Yes | Weight lifted (lbs or kg) |
| Weight Unit | Yes | Unit of weight (lbs or kg) |
| Reps | Yes | Number of repetitions |
| RPE | No | Rate of Perceived Exertion (1-10) |
| Distance | No | Distance (for cardio) |
| Distance Unit | No | Unit for distance (e.g., mi) |
| Seconds | Yes | Duration in seconds (use `0` if not applicable) |
| Notes | Yes | Exercise notes (use `-` if empty) |
| Workout Notes | Yes | Workout-level notes (use `-` if empty) |
| Workout Duration | Yes | Total workout duration (e.g., "1h") |

### Example Output

```csv
Date;Workout Name;Exercise Name;Set Order;Weight;Weight Unit;Reps;RPE;Distance;Distance Unit;Seconds;Notes;Workout Notes;Workout Duration
2024-08-24 17:30:00;PPL - Legs B;Leg Press;1;265;lbs;8;;;;0;-;-;1h
2024-08-24 17:30:00;PPL - Legs B;Leg Press;2;265;lbs;9;;;;0;-;-;1h
2024-08-24 17:30:00;PPL - Legs B;Seated Leg Curl (Machine);1;195;lbs;8;;;;0;-;-;1h
```

## Installation

No dependencies required - uses Python standard library only.

```bash
cd strong-csv-migrator
```

## Usage

### Basic Command

```bash
uv run migrator.py \
  -f "old_format/Health Tracking (8_24_24 - 7_5_25) - PPL 8_24_24 - 7_5_25.csv,2025-07-05,PPL" \
  -f "old_format/Health Tracking (7_6_25 - 2_13_26) - ULPPL 7_6_25 - 2_13_26.csv,2026-02-13,ULPPL" \
  -o historical_workouts.csv
```

### Command Options

- `-f "filepath,end_date,workout_name"` - Per-file configuration (required, can specify multiple times)
  - `filepath`: Path to input CSV file
  - `end_date`: Last workout date in `YYYY-MM-DD` format (NOT parsed from filename!)
  - `workout_name`: Name for this workout program (e.g., "PPL", "ULPPL")
- `-o output.csv` - Output file path (default: `historical_workouts.csv`)

### Date Calculation Logic

**Critical:** Dates are calculated **backwards from the end_date**, NOT forwards from a start date. This is more reliable because:

- End date is explicitly provided as a command parameter
- Filenames can be misleading, contain typos, or not match actual data
- Ensures the final workout lands exactly on the specified end date

**Workout Cycles:**

- **PPL**: 8-day cycle (Push A, Pull A, Legs A, Rest, Push B, Pull B, Legs B, Rest)
  - End date should be the last workout (typically Legs B)
- **ULPPL**: 7-day cycle (Upper, Lower, Rest, Push, Pull, Legs, Rest)
  - End date should be the last workout (typically Upper or the last logged workout)

**Example:** If PPL ends 2025-07-05 (Legs B):
```
Week 23, Legs B  = 2025-07-05 (0 days back)
Week 23, Pull B  = 2025-07-04 (1 day back)
Week 23, Push B  = 2025-07-03 (2 days back)
Week 22, Legs B  = 2025-06-27 (8 days back)
```

### Exercise Name Mapping

Edit `EXERCISE_NAME_MAP` in `migrator.py` to map your source exercise names to Hevy-compatible names. This prevents "Custom" exercises from being created in Hevy.

The map is organized by Hevy exercise name → array of source name variations:

```python
EXERCISE_NAME_MAP = {
    "Hammer Curl (Dumbbell)": ["Hammer Curl", "Seated Hammer Curl"],
    "Triceps Rope Pushdown": ["Tricep Pushdown", "Tricep Pushdowns"],
    "Seated Leg Curl (Machine)": ["Leg Curl", "Seated Leg Curl"],
    # Add your mappings...
}
```

### TRUE/FALSE Filtering

The migrator reads a "completed" column (containing TRUE/FALSE) for each exercise:
- **TRUE exercises**: Included in output
- **FALSE exercises**: Excluded (skipped)
- **Entire workout day with all FALSE**: Skipped entirely (like missing the gym)

This preserves the date structure so skipped days don't shift subsequent workout dates.

## Testing & QA

After generating `historical_workouts.csv`, use the calendar viewer to verify your data:

### View Full Calendar

```bash
uv run calendar_view.py
```

Shows all workouts organized by month:
```
================================================================================
WORKOUT CALENDAR VIEW
================================================================================
Date Range: 2024-08-24 to 2026-02-13
Total Workout Days: 274
================================================================================

August 2024
------------------------------------------------------------
2024-08-24 (Sat): PPL - Legs B
2024-08-25 (Sun): PPL - Push A
2024-08-27 (Tue): PPL - Pull A
...
```

### Summary Statistics

```bash
uv run calendar_view.py --summary
```

Shows workout counts and date coverage:
```
================================================================================
SUMMARY STATISTICS
================================================================================
Date Range: 2024-08-24 to 2026-02-13
Total Days in Range: 539
Workout Days: 274
Rest Days: 265

Workout Type Breakdown:
  PPL - Legs A: 22 days
  PPL - Legs B: 23 days
  PPL - Pull A: 22 days
  ...
================================================================================
```

### Find Gaps (Rest Periods)

```bash
uv run calendar_view.py --gaps 7
```

Finds gaps of 7+ days without workouts (useful to spot program transitions or missed weeks):
```
================================================================================
GAPS (7+ days without workouts)
================================================================================
2025-07-05 to 2025-07-25: 19 day gap
================================================================================
```

### Filter by Date Range

```bash
# View January 2026 only
uv run calendar_view.py --start 2026-01-01 --end 2026-01-31

# View everything from February 2026 onward
uv run calendar_view.py --start 2026-02-01
```

### Common Testing Scenarios

1. **Verify date accuracy**: Check that first/last workout dates match expectations
2. **Check for unexpected gaps**: Use `--gaps 3` to find 3+ day gaps (might indicate errors)
3. **Verify workout distribution**: Use `--summary` to ensure workout counts look correct
4. **Spot check specific periods**: Use `--start`/`--end` to examine specific date ranges

## Input Format

The tool expects Google Sheets CSV exports with this structure:
- Header row contains week labels: "Week 1", "Week 2", etc.
- Each week has 5 columns: Sets, Reps, Load, TRUE (completed flag), Notes
- Workout day headers: "Upper", "Lower", "Push A", "Pull B", etc. (single-row markers)
- Exercise rows follow under each workout day header

## Importing to Hevy

1. Run the migrator to generate `historical_workouts.csv`
2. Open Hevy app
3. Go to Profile > Settings > Export & Import Data
4. Tap "Import data"
5. Select "Import from Strong"
6. Upload the generated CSV file

**Note**: Hevy only allows one data import. If you need to revert, you must manually remove imported data before re-importing.

## Results

Final migration output:
- **Total**: 274 workouts, 3,345 sets
- **Date range**: August 24, 2024 → February 13, 2026 (539 days)
- **PPL program**: ~131 workouts (23 weeks)
- **ULPPL program**: ~143 workouts (30 weeks)
- **Gap between programs**: 19 days (July 5 → July 25, 2025)
