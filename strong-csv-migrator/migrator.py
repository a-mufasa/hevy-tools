#!/usr/bin/env python3
"""
Strong CSV Migrator

Converts workout tracking spreadsheets (organized by week) to Strong CSV format
for import into Hevy app.

Strong CSV Format (required columns):
    - Date: Workout date (YYYY-MM-DD)
    - Workout Name: Name of the workout routine
    - Exercise Name: Name of the exercise
    - Weight: Weight lifted (lbs/kg)
    - Reps: Number of repetitions

Optional columns:
    - RPE: Rate of Perceived Exertion (1-10)
    - Notes: Exercise notes
"""

import csv
import argparse
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

# Exercise name mapping - map your exercises to Hevy-compatible names
# Edit this dictionary to map your exercise names to Hevy's exercise names
# This prevents "Custom" exercises from being created
EXERCISE_NAME_MAP = {
    "Abductor (Outer)": "Abductor (Outer)",
    "Adductor (Inner)": "Adductor (Inner)",
    "Cable Fly": "Cable Fly",
    "Cable Lateral Raise": "Single Arm Lateral Raise (Cable)",
    "Cable Pullover": "Cable Pullover",
    "Calf Raise": "Calf Raise",
    "Calf Raises": "Calf Raise",
    "Chest Fly": "Chest Fly",
    "Close Grip Pull-up": "Close Grip Pull-up",
    "DB Flat Bench": "Dumbbell Bench Press",
    "DB Incline Bench": "Incline Dumbbell Press",
    "DB Lateral Raise": "Dumbbell Lateral Raise",
    "DB Overhead Press": "Dumbbell Shoulder Press",
    "DB Preacher Curl": "Dumbbell Preacher Curl",
    "DB RDL": "Romanian Deadlift (Dumbbell)",
    "DB Row": "Dumbbell Row",
    "Dead Bugs": "Dead Bug",
    "Face Pull": "Face Pull",
    "Flat Bench Press": "Barbell Bench Press",
    "Hammer Curl": "Dumbbell Hammer Curl",
    "Incline Cable Fly": "Incline Cable Fly",
    "Incline Smith Bench Press": "Incline Smith Machine Bench Press",
    "Lat Pulldown": "Lat Pulldown",
    "Lateral Raise": "Lateral Raise",
    "Leg Curl": "Lying Leg Curl",
    "Leg Extension": "Leg Extension",
    "Leg Press": "Leg Press",
    "Lunges": "Walking Lunges",
    "Preacher Curl": "EZ Bar Preacher Curl",
    "Rear Delt": "Rear Delt Fly",
    "Row": "Barbell Row",
    "SLDL": "Stiff Leg Deadlift",
    "Seated Hammer Curl": "Seated Dumbbell Curl",
    "Seated Leg Curl": "Seated Leg Curl",
    "Shoulder Press": "Overhead Press",
    "Single Arm Seated Row": "Single Arm Cable Row",
    "Single Arm Tricep Extension": "Single Arm Tricep Extension",
    "Smith Squat": "Smith Machine Squat",
    "Tricep Pushdown": "Tricep Pushdown",
    "Tricep Pushdowns": "Tricep Pushdown",
    "Tricep Rope Extension": "Tricep Rope Pushdown",
    "Weighted Dip": "Weighted Dip",
    "Wide Grip Pull-up": "Wide Grip Pull-up",
}

# Workout schedules - maps workout types to day of week (0=Monday)
# PPL: Push(Mon), Pull(Tue), Legs(Wed), rest(Thu), then repeat
PPL_WORKOUT_SCHEDULE = {
    "Push": 0,   # Monday
    "Push A": 0, # Monday
    "Push B": 0, # Monday (if different day needed)
    "Pull": 1,   # Tuesday
    "Pull A": 1, # Tuesday
    "Pull B": 1, # Tuesday
    "Legs": 2,   # Wednesday
    "Legs A": 2, # Wednesday
    "Legs B": 2, # Wednesday
}

# ULPPL: Upper(Mon), Lower(Tue), Push(Wed), Pull(Thu), Legs(Fri)
ULPPL_WORKOUT_SCHEDULE = {
    "Upper": 0,   # Monday
    "Lower": 1,   # Tuesday
    "Push": 2,    # Wednesday
    "Pull": 3,    # Thursday
    "Legs": 4,    # Friday
}


def parse_start_date_from_filename(filepath: str) -> Optional[datetime]:
    """Extract start date from filename like 'Health Tracking (8_24_24 - 7_5_25) - PPL.csv'"""
    filename = Path(filepath).name
    # Match pattern: (MM_DD_YY - ...)
    match = re.search(r'\((\d+)_(\d+)_(\d+)\s*-', filename)
    if match:
        start_month, start_day, start_year = match.groups()
        # Handle 2-digit year
        start_year = int(start_year)
        if start_year < 100:
            start_year += 2000
        return datetime(start_year, int(start_month), int(start_day))
    return None


def get_week_number_for_columns(header_row: list) -> dict:
    """Get mapping of week number to column index, skipping Setup columns."""
    week_map = {}
    for idx, cell in enumerate(header_row):
        cell_str = str(cell).strip()
        if 'Setup' in cell_str:
            continue
        week_num = re.search(r'Week\s*(\d+)', cell_str, re.IGNORECASE)
        if week_num:
            week_map[int(week_num.group(1))] = idx
    return week_map


def calculate_date_backwards(
    week_number: int,
    workout_day_of_week: int,
    end_date: datetime,
    days_per_week: int = 3
) -> datetime:
    """
    Calculate date working backwards from end date.
    
    Args:
        week_number: The week number (1-indexed)
        workout_day_of_week: Day of week for this workout (0=Monday, 4=Friday)
        end_date: The end date (reference point, typically the last workout)
        days_per_week: Number of workout days per week (3 for PPL, 5 for ULPPL)
    
    Returns:
        The calculated date
    """
    # Calculate how many days to go back from end_date
    # End date is the last workout, so we need to count backwards
    
    # Total workout days to go back = (weeks - 1) * days_per_week + workout_day_of_week
    total_workout_days_back = (week_number - 1) * days_per_week + workout_day_of_week
    
    # Each week has 7 days, but we only count workout days
    # But actually we need to count calendar days, not just workout days
    
    # Let's think about it differently:
    # If week_number=1, workout_day=0 (Monday), and end_date is Friday of the last week
    # We need to go back (week_number-1)*7 + (days_per_week - 1 - workout_day_of_week) days
    
    # Actually, simpler approach: calculate from start of week 1
    # Week 1 starts days_per_week*7 before end_date minus the remaining days
    
    # More straightforward: calculate forward from a reference point
    # But since we know end_date, let's calculate backwards more precisely
    
    # The end_date is the last scheduled workout (typically the last week, last workout day)
    # To find a specific workout:
    # - Find the date of the last workout of the last week
    # - Go back by (total_weeks - week_number) * 7 + (last_day_of_week - target_day_of_week)
    
    # Simpler: work with calendar days. Each week has 7 days.
    # From end of week N to start of week 1: (N-1) * 7 days
    # Within a week, adjust by the day of week difference
    
    return end_date


def calculate_date_for_week(
    week_number: int,
    start_date: datetime,
    workout_day_of_week: int = 0,
    days_per_week: int = 3
) -> datetime:
    """
    Calculate the date for a given week number, working forwards from start_date.
    
    Args:
        week_number: The week number (1-indexed)
        start_date: The start date of week 1 (can be any day - we'll find the Monday)
        workout_day_of_week: Day of week for this workout (0=Monday, 1=Tuesday, etc.)
        days_per_week: Number of workout days per week
    
    Returns:
        The calculated date
    """
    # Find the Monday of the week containing start_date
    # If start_date is a Monday, use it. Otherwise find the previous Monday.
    start_dow = start_date.weekday()  # 0=Monday, 6=Sunday
    monday_of_week1 = start_date - timedelta(days=start_dow)
    
    # Each workout "week" has 7 calendar days
    days_offset = (week_number - 1) * 7 + workout_day_of_week
    return monday_of_week1 + timedelta(days=days_offset)


def get_workout_day_type(workout_name: str, schedule: dict = None) -> Optional[tuple]:
    """
    Determine the workout type and its day of week.
    Returns (workout_base_type, day_of_week) or None if not recognized
    
    Args:
        workout_name: The workout day name (e.g., "Push", "Upper", "Push A")
        schedule: The schedule to use (PPL_WORKOUT_SCHEDULE or ULPPL_WORKOUT_SCHEDULE)
    """
    workout_name = workout_name.strip()
    
    # If schedule is provided, use only that schedule
    if schedule:
        for key, day in schedule.items():
            if workout_name == key or workout_name.startswith(key + " "):
                return (key, day)
        return None
    
    # Otherwise check both schedules (prefer longer/more specific matches)
    # Check ULPPL first (more specific with Upper, Lower)
    for key, day in ULPPL_WORKOUT_SCHEDULE.items():
        if workout_name == key or workout_name.startswith(key + " "):
            return (key, day)
    
    # Then check PPL
    for key, day in PPL_WORKOUT_SCHEDULE.items():
        if workout_name == key or workout_name.startswith(key + " "):
            # Extract base type
            base_type = key.replace(" A", "").replace(" B", "")
            return (base_type, day)
    
    return None


def parse_health_tracking_csv(
    filepath: str,
    start_date: datetime,
    workout_name_prefix: str = "Workout",
    days_per_week: int = 3
) -> list[dict]:
    """
    Parse a health tracking CSV file organized by weeks.
    
    Args:
        filepath: Path to the CSV file
        start_date: Start date for Week 1 (should be a Monday)
        workout_name_prefix: Base name for workouts (e.g., "PPL", "ULPPL")
        days_per_week: Number of workout days per week (3 for PPL, 5 for ULPPL)
    
    Returns:
        List of workout entries in Strong CSV format
    """
    workouts = []
    set_order_counter = {}
    
    with open(filepath, 'r', encoding='utf-8') as f:
        reader = csv.reader(f)
        rows = list(reader)
    
    if len(rows) < 2:
        return workouts
    
    header_row = rows[0]
    week_columns = get_week_number_for_columns(header_row)
    
    # Determine schedule based on workout_name_prefix
    schedule = ULPPL_WORKOUT_SCHEDULE if days_per_week == 5 else PPL_WORKOUT_SCHEDULE
    
    current_day = None
    for row_idx, row in enumerate(rows[2:], start=2):
        if not row or not row[0].strip():
            continue
        
        first_cell = row[0].strip()
        
        # Detect workout day
        if first_cell.startswith('Day'):
            current_day = first_cell
            continue
        
        if first_cell in ['Upper', 'Lower', 'Push', 'Pull', 'Legs', 'Long Run']:
            current_day = first_cell
            continue
        
        # Check for Push A, Pull A, Legs A, etc.
        for day_type in ['Push', 'Pull', 'Legs']:
            if first_cell.startswith(day_type) and (len(first_cell) == len(day_type) or first_cell[len(day_type)] in [' ', 'A', 'B']):
                current_day = first_cell
                break
        
        if not current_day:
            continue
            
        exercise_name = first_cell
        if not exercise_name:
            continue
        
        # Get workout type and day of week
        workout_info = get_workout_day_type(current_day, schedule)
        if not workout_info:
            continue
            
        workout_base, day_of_week = workout_info
        
        for week_num, col_idx in week_columns.items():
            if col_idx >= len(row):
                continue
            
            sets_cell = row[col_idx].strip() if col_idx < len(row) else ""
            
            if not sets_cell or sets_cell == "":
                continue
            
            try:
                sets = int(sets_cell) if sets_cell else None
            except ValueError:
                continue
            
            if sets is None or sets == 0:
                continue
            
            # Data columns after "Week X" label
            reps_idx = col_idx + 1
            weight_idx = col_idx + 2
            completed_idx = col_idx + 3
            notes_idx = col_idx + 4
            
            reps = None
            weight = None
            notes = ""
            
            if reps_idx < len(row):
                reps_val = row[reps_idx].strip()
                if reps_val:
                    try:
                        reps = int(reps_val)
                    except ValueError:
                        reps = None
            
            if weight_idx < len(row):
                weight_val = row[weight_idx].strip()
                if weight_val and weight_val.upper() != 'N/A':
                    try:
                        weight = float(weight_val)
                    except ValueError:
                        weight = None
            
            if completed_idx < len(row):
                completed_val = row[completed_idx].strip().upper()
                if completed_val != 'TRUE':
                    continue
            
            if notes_idx < len(row):
                notes = row[notes_idx].strip()
                if notes.upper() in ('YES', 'NO'):
                    notes = ''
            
            if reps is None or reps == 0:
                continue
            
            # Calculate date forwards from start date
            workout_date = calculate_date_for_week(
                week_num, 
                start_date, 
                day_of_week,
                days_per_week
            )
            
            full_workout_name = f"{workout_name_prefix} - {workout_base}"
            
            # Get current set order
            date_key = workout_date.strftime('%Y-%m-%d')
            exercise_key = (date_key, full_workout_name, exercise_name)
            current_set_order = set_order_counter.get(exercise_key, 0)
            
            for set_num in range(sets):
                current_set_order += 1
                date_with_time = date_key + " 17:30:00"
                workouts.append({
                    'Date': date_with_time,
                    'Workout Name': full_workout_name,
                    'Exercise Name': exercise_name,
                    'Set Order': current_set_order,
                    'Weight': weight if weight else 0,
                    'Reps': reps,
                    'RPE': '',
                    'Notes': notes if set_num == 0 else ''
                })
            
            set_order_counter[exercise_key] = current_set_order
    
    return workouts


def write_strong_csv(workouts: list[dict], output_path: str):
    """Write workouts to Strong CSV format (semicolon-delimited)."""
    fieldnames = ['Date', 'Workout Name', 'Exercise Name', 'Set Order', 'Weight', 'Weight Unit', 'Reps', 'RPE', 'Distance', 'Distance Unit', 'Seconds', 'Notes', 'Workout Notes', 'Workout Duration']
    
    workouts_sorted = sorted(workouts, key=lambda x: (x['Date'], x['Workout Name'], x['Exercise Name'], x.get('Set Order', 1)))
    
    with open(output_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, delimiter=';')
        writer.writeheader()
        for workout in workouts_sorted:
            exercise_name = workout.get('Exercise Name', '')
            mapped_name = EXERCISE_NAME_MAP.get(exercise_name, exercise_name)
            
            row = {
                'Date': workout['Date'],
                'Workout Name': workout['Workout Name'],
                'Exercise Name': mapped_name,
                'Set Order': workout.get('Set Order', 1),
                'Weight': workout.get('Weight', ''),
                'Weight Unit': 'lbs',
                'Reps': workout.get('Reps', ''),
                'RPE': '',
                'Distance': '',
                'Distance Unit': '',
                'Seconds': '0',
                'Notes': workout.get('Notes') or '-',
                'Workout Notes': '-',
                'Workout Duration': '1h'
            }
            writer.writerow(row)


def merge_csv_files(file_configs: list[dict], output_path: str):
    """Merge multiple CSV files into a single Strong CSV."""
    all_workouts = []
    
    for config in file_configs:
        filepath = config['filepath']
        start_date = config['start_date']
        workout_name = config.get('workout_name', 'Workout')
        days_per_week = config.get('days_per_week', 3)
        
        # Try to parse start date from filename if not provided
        if start_date is None:
            start_date = parse_start_date_from_filename(filepath)
        
        if start_date is None:
            print(f"Warning: Could not parse start date from {filepath}, using current date")
            start_date = datetime.now()
        
        workouts = parse_health_tracking_csv(
            filepath,
            start_date,
            workout_name_prefix=workout_name,
            days_per_week=days_per_week
        )
        
        all_workouts.extend(workouts)
        print(f"Processed {filepath}: {len(workouts)} sets (start_date={start_date.strftime('%Y-%m-%d')}, {days_per_week} days/week)")
    
    if all_workouts:
        write_strong_csv(all_workouts, output_path)
        print(f"\nTotal: {len(all_workouts)} sets written to {output_path}")
    else:
        print("No workouts found.")


def main():
    parser = argparse.ArgumentParser(
        description='Convert health tracking CSVs to Strong CSV format for Hevy import'
    )
    parser.add_argument(
        'input_files',
        nargs='*',
        help='Input CSV files to process. Defaults to all CSV files in old_format/ if not specified'
    )
    parser.add_argument(
        '-o', '--output',
        default='historical_workouts.csv',
        help='Output CSV file (default: historical_workouts.csv)'
    )
    parser.add_argument(
        '-f', '--file-config',
        action='append',
        help='Per-file config in format: filepath,start_date,workout_name,days_per_week'
    )
    
    args = parser.parse_args()
    
    # If no input files specified, look for CSVs in old_format/ directory
    if not args.input_files and not args.file_config:
        old_format_dir = Path('old_format')
        if old_format_dir.exists():
            args.input_files = [str(f) for f in sorted(old_format_dir.glob('*.csv'))]
            print(f"Found {len(args.input_files)} CSV files in old_format/")
        else:
            print("Error: No input files specified and old_format/ directory not found")
            return
    
    # Handle per-file configs
    if args.file_config:
        file_configs = []
        for config_str in args.file_config:
            parts = config_str.split(',')
            if len(parts) < 2:
                print(f"Error: Invalid file config format: {config_str}")
                print("Expected: filepath,start_date,workout_name,days_per_week")
                return
            filepath = parts[0]
            
            # Parse start date
            if len(parts) > 1 and parts[1]:
                try:
                    start_date = datetime.strptime(parts[1], '%Y-%m-%d')
                except ValueError:
                    start_date = None
            else:
                start_date = None
            
            workout_name = parts[2] if len(parts) > 2 else 'Workout'
            days_per_week = int(parts[3]) if len(parts) > 3 else 3
            
            file_configs.append({
                'filepath': filepath,
                'start_date': start_date,
                'workout_name': workout_name,
                'days_per_week': days_per_week
            })
    else:
        # Use defaults for files found in old_format/
        file_configs = []
        for filepath in args.input_files:
            # Try to parse start date from filename
            start_date = parse_start_date_from_filename(filepath)
            
            # Determine workout type based on filename
            if 'ULPPL' in filepath.upper():
                workout_name = 'ULPPL'
                days_per_week = 5
            else:
                workout_name = 'PPL'
                days_per_week = 3
            
            file_configs.append({
                'filepath': filepath,
                'start_date': start_date,
                'workout_name': workout_name,
                'days_per_week': days_per_week
            })
    
    merge_csv_files(file_configs, args.output)


if __name__ == '__main__':
    main()
