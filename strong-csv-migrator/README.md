# Strong CSV Migrator

Converts workout tracking spreadsheets to Strong CSV format for import into Hevy app.

## What is the Strong CSV Format?

The Strong app (and Hevy when importing from Strong) uses a specific CSV format with the following columns:

| Column | Required | Description |
|--------|----------|-------------|
| Date | Yes | Workout date in YYYY-MM-DD format |
| Workout Name | Yes | Name of the workout routine |
| Exercise Name | Yes | Name of the exercise performed |
| Weight | Yes | Weight lifted (lbs or kg) |
| Reps | Yes | Number of repetitions |
| RPE | No | Rate of Perceived Exertion (1-10) |
| Notes | No | Exercise notes |

### Example

```csv
Date,Workout Name,Exercise Name,Weight,Reps,RPE,Notes
2024-08-05,PPL - Day 1 (Legs A),Leg Press,265,8,,
2024-08-05,PPL - Day 1 (Legs A),Leg Press,265,9,,
2024-08-05,PPL - Day 1 (Legs A),Seated Leg Curl,195,8,,
2024-08-12,PPL - Day 1 (Legs A),Leg Press,275,8,,
...
```

## Installation

No dependencies required. Uses Python standard library.

```bash
cd strong-csv-migrator
```

## Usage

### Basic Usage (single file)

```bash
uv run migrator.py input.csv -s 2024-08-04 -o historical_workouts.csv
```

### Multiple Files with Same Settings

```bash
uv run migrator.py file1.csv file2.csv -s 2024-08-04 -w "My Workout" -o output.csv
```

### Multiple Files with Different Start Dates

Use `-f` for per-file configuration:

```bash
uv run migrator.py \
  -f "file1.csv,2024-08-24,PPL,0" \
  -f "file2.csv,2025-07-06,ULPPL,0" \
  -o historical_workouts.csv
```

Format: `filepath,start_date,workout_name,day_offset`

### Specify Day of Week

By default, workouts are scheduled on Monday (day_offset=0). You can change this:

- `0` = Monday
- `1` = Tuesday
- `2` = Wednesday
- `3` = Thursday
- `4` = Friday
- `5` = Saturday
- `6` = Sunday

```bash
uv run migrator.py input.csv -s 2024-08-04 -d 6 -o output.csv  # Sunday
```

## Example

```bash
uv run migrator.py \
  -f "../old_format/Health Tracking (8_24_24 - 7_5_25) - PPL 8_24_24 - 7_5_25.csv,2024-08-24,PPL,0" \
  -f "../old_format/Health Tracking (7_6_25 - 2_13_26) - ULPPL 7_6_25 - 2_13_26.csv,2025-07-06,ULPPL,0" \
  -o historical_workouts.csv
```

### Date Calculation

The script calculates workout dates using the formula:

```
date = start_date + (week_number - 1) * 7 + day_offset
```

For example, if Week 1 starts on Monday 2024-08-05:
- Week 1, Monday = 2024-08-05
- Week 2, Monday = 2024-08-12
- Week 3, Monday = 2024-08-19

### Input Format

The tool expects CSV files organized by weeks, where:
- Each column represents a week (e.g., "Week 1", "Week 2")
- Each row contains an exercise
- Cells contain: Sets, Reps, Weight, Completed (TRUE/FALSE), Notes

### Processing Logic

1. **Parse headers**: Identify week columns from the header row
2. **Track workout context**: Detect day names (Day 1, Day 2, etc.)
3. **Extract sets**: For each week/exercise combination, create individual set entries
4. **Calculate dates**: Use the provided start date and week number
5. **Filter completed**: Only include sets marked as TRUE
6. **Merge & sort**: Combine all files and sort by date

## Importing to Hevy

1. Run the migrator to generate `historical_workouts.csv`
2. Open Hevy app
3. Go to Settings > Import Data
4. Select "Import from Strong"
5. Upload the generated CSV file

## Notes

- Only sets marked as "TRUE" (completed) are included
- Sets with 0 reps or empty weight are included (for bodyweight exercises)
- Setup columns are automatically skipped
- RPE is left empty by default (can be manually added later in Hevy)
