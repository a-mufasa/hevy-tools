# Strong CSV Migrator

Converts workout tracking spreadsheets to Strong CSV format for import into Hevy app.

## What is the Strong CSV Format?

The Strong app (and Hevy when importing from Strong) uses a specific CSV format with semicolon delimiters. **This format has strict requirements** - see the [Hevy Import Guide](https://www.reddit.com/r/Hevy/comments/17g64va/importing_historical_workout_data_into_hevy_a/) for details.

### Required Columns

| Column | Required | Description |
|--------|----------|-------------|
| Date | Yes | Workout date in `YYYY-MM-DD HH:MM:SS` format |
| Workout Name | Yes | Name of the workout routine |
| Exercise Name | Yes | Name of the exercise performed (mapped to Hevy-compatible names) |
| Set Order | Yes | Order of the set within the exercise |
| Weight | Yes | Weight lifted (lbs or kg) |
| Weight Unit | Yes | Unit of weight (lbs or kg) |
| Reps | Yes | Number of repetitions |
| RPE | No | Rate of Perceived Exertion (1-10) |
| Distance | No | Distance (for cardio) |
| Distance Unit | No | Unit for distance (e.g., mi) |
| Seconds | Yes | Duration in seconds (must have a value) |
| Notes | Yes | Exercise notes (must have a value, cannot be empty) |
| Workout Notes | Yes | Workout-level notes (must have a value, cannot be empty) |
| Workout Duration | Yes | Total workout duration (e.g., "30m" or "1h") |

### Important Import Requirements

Based on community testing ([source](https://www.reddit.com/r/Hevy/comments/17g64va/importing_historical_workout_data_into_hevy_a/)):

- **Date** must include time: `YYYY-MM-DD HH:MM:SS` (e.g., `2024-08-24 17:30:00`)
- **Notes** and **Workout Notes** must have values (cannot be empty)
- **Seconds** must have a value (use `0` if not applicable)
- **Workout Duration** must have a value (e.g., `30m`, `1h`)
- **Distance Unit** should be `mi` (with dot)

### Example Output

```csv
Date;Workout Name;Exercise Name;Set Order;Weight;Weight Unit;Reps;RPE;Distance;Distance Unit;Seconds;Notes;Workout Notes;Workout Duration
2024-08-24 17:30:00;PPL;Leg Press;1;265;lbs;8;0;;0;-;-;1h
2024-08-24 17:30:00;PPL;Leg Press;2;265;lbs;9;0;;0;-;-;1h
2024-08-24 17:30:00;PPL;Seated Leg Curl;1;195;lbs;8;0;;0;-;-;1h
```

## Installation

```bash
cd strong-csv-migrator
```

No additional dependencies required. Uses Python standard library.

## Usage

### Run the Migrator

```bash
uv run migrator.py \
  -f "old_format/Health Tracking (8_24_24 - 7_5_25) - PPL 8_24_24 - 7_5_25.csv,2025-07-05,PPL" \
  -f "old_format/Health Tracking (7_6_25 - 2_13_26) - ULPPL 7_6_25 - 2_13_26.csv,2026-02-13,ULPPL"
```

### Command Options

- `-f "filepath,end_date,workout_name"` - Per-file configuration (can specify multiple)
- `-o output.csv` - Output file (default: `historical_workouts.csv`)

### Exercise Name Mapping

Edit the `EXERCISE_NAME_MAP` dictionary in `migrator.py` to map your exercise names to Hevy-compatible names. This prevents "Custom" exercises from being created.

```python
EXERCISE_NAME_MAP = {
    "Cable Lateral Raise": "Single Arm Lateral Raise (Cable)",
    "DB Flat Bench": "Dumbbell Bench Press",
    # Add your mappings here...
}
```

### Date Calculation

The script calculates dates **working backwards from the end date**, not forwards from start date. This is more reliable because:

- The end date is explicitly provided (e.g., the last workout in the file)
- Filenames can be misleading or contain typos
- The actual logged data may not match the filename date range

**PPL (Push, Pull, Legs):** 8-day cycle: Push, Pull, Legs, Rest, Push, Pull, Legs, Rest

**ULPPL (Upper, Lower, Push, Pull, Legs):** 7-day cycle: Upper, Lower, Rest, Push, Pull, Legs, Rest

The date, Legs, is calculated as:

```
date = end_date - ((week_number - 1) * cycle_days + workout_day_index)
```

For example, with PPL ending on 2025-07-05 (Saturday):
- Week 23, Legs (day 2) = 2025-07-05
- Week 23, Pull (day 1) = 2025-07-04
- Week 22, Legs (day 2) = 2025-06-27
- Week 1, Push (day 0) = working backwards ~23 weeks

## Input Format

The tool expects CSV files organized by weeks (like Google Sheets exports), where:
- Each column represents a week (e.g., "Week 1", "Week 2")
- Each row contains an exercise
- Cells contain: Sets, Reps, Weight, Completed (TRUE/FALSE), Notes

## Importing to Hevy

1. Run the migrator to generate `historical_workouts.csv`
2. Open Hevy app
3. Go to Profile > Settings > Export & Import Data
4. Tap "Import data"
5. Select "Import from Strong"
6. Upload the generated CSV file

**Note**: You can only do one data import. If you need to revert, you can remove imported data and re-import.

## Processing Logic

1. **Parse headers**: Identify week columns from the header row
2. **Track workout context**: Detect day names (Day 1, Day 2, Push, Pull, Legs, etc.)
3. **Extract sets**: For each week/exercise combination, create individual set entries
4. **Calculate dates**: Use the provided **end_date** and work backwards through the cycle
5. **Filter completed**: Only include sets marked as TRUE
6. **Apply exercise mapping**: Map exercise names to Hevy-compatible names
7. **Merge & sort**: Combine all files and sort by date

## Notes

- Only sets marked as "TRUE" (completed) are included
- "Yes" and "No" markers in the Notes column are filtered out (they were just completion markers)
- Actual exercise notes are preserved
- Setup columns are automatically skipped
- Default workout time: 5:30 PM (17:30)
- Default workout duration: 1 hour
