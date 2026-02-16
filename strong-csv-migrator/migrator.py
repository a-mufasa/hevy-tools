#!/usr/bin/env python3
"""
Strong CSV Migrator

Converts workout tracking spreadsheets (organized by week) to Strong CSV format
for import into Hevy app.
"""

import csv
import argparse
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

# Exercise name mapping - map your exercises to Hevy-compatible names
EXERCISE_NAME_MAP = {
    "Abductor (Outer)": "Hip Abduction (Machine)",
    "Adductor (Inner)": "Hip Adduction (Machine)",
    "Cable Fly": "Seated Chest Flys (Cable)",
    "Cable Lateral Raise": "Single Arm Lateral Raise (Cable)",
    "Cable Pullover": "Rope Straight Arm Pulldown",
    "Calf Raise": "Calf Press (Machine)",
    "Calf Raises": "Calf Press (Machine)",
    "Chest Fly": "Chest Fly (Machine)",
    "Close Grip Pull-up": "Pull Up",
    "DB Flat Bench": "Bench Press (Dumbbell)",
    "DB Incline Bench": "Incline Bench Press (Dumbbell)",
    "DB Lateral Raise": "Lateral Raise (Dumbbell)",
    "DB Overhead Press": "Seated Overhead Press (Dumbbell)",
    "DB Preacher Curl": "Preacher Curl (Dumbbell)",
    "DB RDL": "Romanian Deadlift (Dumbbell)",
    "DB Row": "Dumbbell Row",
    "Dead Bugs": "Dead Bug",
    "Face Pull": "Face Pull",
    "Flat Bench Press": "Bench Press (Barbell)",
    "Hammer Curl": "Hammer Curl (Dumbbell)",
    "Incline Cable Fly": "Low Cable Fly Crossovers",
    "Incline Smith Bench Press": "Incline Bench Press (Smith Machine)",
    "Lat Pulldown": "Lat Pulldown (Cable)",
    "Lateral Raise": "Lateral Raise (Dumbbell)",
    "Leg Curl": "Seated Leg Curl (Machine)",
    "Leg Extension": "Leg Extension (Machine)",
    "Leg Press": "Leg Press Horizontal (Machine)",
    "Lunges": "Lunge (Dumbbell)",
    "Preacher Curl": "Preacher Curl (Dumbbell)",
    "Rear Delt": "Face Pull",
    "Row": "Seated Row (Machine)",
    "SLDL": "Straight Leg Deadlift",
    "Seated Hammer Curl": "Hammer Curl (Dumbbell)",
    "Seated Leg Curl": "Seated Leg Curl (Machine)",
    "Shoulder Press": "Seated Shoulder Press (Machine)",
    "Single Arm Seated Row": "Single Arm Cable Row",
    "Single Arm Tricep Extension": "Single Arm Triceps Pushdown (Cable)",
    "Smith Squat": "Squat (Smith Machine)",
    "Tricep Pushdown": "Triceps Rope Pushdown",
    "Tricep Pushdowns": "Triceps Rope Pushdown",
    "Tricep Rope Extension": "Triceps Rope Pushdown",
    "Weighted Dip": "Chest Dip (Weighted)",
    "Wide Grip Pull-up": "Wide Pull Up",
}


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
    workout_day_index: int,
    end_date: datetime,
    cycle_days: int,
    total_weeks: int
) -> datetime:
    """
    Calculate date working backwards from end_date.
    
    Args:
        week_number: The week number (1-indexed, from spreadsheet)
        workout_day_index: Index of this workout within the cycle (0=first)
        end_date: The end date (last workout date)
        cycle_days: Days in one complete cycle (8 for PPL, 7 for ULPPL)
        total_weeks: Total number of weeks in the spreadsheet
    Returns:
        The calculated date
    """
    # Week max_week_number maps to end_date
    # Week 1 is the earliest, furthest back
    # days_back = (max_week_number - week_number) * cycle_days + workout_day_index
    days_back = (total_weeks - week_number) * cycle_days + workout_day_index
    return end_date - timedelta(days=days_back)


def parse_health_tracking_csv(
    filepath: str,
    end_date: datetime,
    workout_name_prefix: str = "Workout",
    cycle_days: int = 8,
    workout_days_in_cycle: list = None,
    total_weeks: int = None
) -> list[dict]:
    """
    Parse a health tracking CSV file organized by weeks.
    
    Args:
        filepath: Path to the CSV file
        end_date: End date for calculation (last workout date)
        workout_name_prefix: Base name for workouts (e.g., "PPL", "ULPPL")
        cycle_days: Days in one complete cycle (8 for PPL, 7 for ULPPL)
        workout_days_in_cycle: List of (day_index, workout_name) for each workout day
        total_weeks: Total number of weeks in the spreadsheet (auto-detected if not provided)
    
    Returns:
        List of workout entries in Strong CSV format
    """
    if workout_days_in_cycle is None:
        workout_days_in_cycle = [(0, "Push"), (1, "Pull"), (2, "Legs")]
    
    workouts = []
    set_order_counter = {}
    
    with open(filepath, 'r', encoding='utf-8') as f:
        reader = csv.reader(f)
        rows = list(reader)
    
    if len(rows) < 2:
        return workouts
    
    header_row = rows[0]
    week_columns = get_week_number_for_columns(header_row)
    
    # Auto-detect total_weeks if not provided
    if total_weeks is None:
        total_weeks = max(week_columns.keys()) if week_columns else 0
    
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
        
        # Find matching workout day from our cycle
        workout_base = None
        workout_day_index = None
        
        for wd_index, wd_name in workout_days_in_cycle:
            if current_day == wd_name or wd_name in current_day:
                workout_base = wd_name
                workout_day_index = wd_index
                break
        
        if workout_base is None:
            continue
        
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
            
            # Calculate date backwards from end date
            workout_date = calculate_date_backwards(
                week_num,
                workout_day_index,
                end_date,
                cycle_days,
                total_weeks
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
        end_date = config['end_date']
        workout_name = config.get('workout_name', 'PPL')
        
        if end_date is None:
            print(f"Error: No end_date provided for {filepath}")
            continue
        
        # Define cycle parameters
        # IMPORTANT: end_date represents the LAST workout, so we work backwards from there
        # For PPL: 8-day cycle: Push A(0), Pull A(1), Legs A(2), Rest(3), Push B(4), Pull B(5), Legs B(6), Rest(7)
        # For ULPPL: 7-day cycle: Upper(0), Lower(1), Rest(2), Push(3), Pull(4), Legs(5), Rest(6)
        if workout_name == "ULPPL":
            # End date = day 0 (Upper), so Upper is the last workout
            cycle_days = 7
            workout_days = [
                (0, "Upper"),     # Upper = day 0 (end_date)
                (1, "Lower"),     # Lower = day 1
                (3, "Push"),      # Push = day 3
                (4, "Pull"),      # Pull = day 4
                (5, "Legs"),      # Legs = day 5
            ]
        else:
            # PPL: End date = day 6 (Legs B), so index = 6 means end_date itself
            cycle_days = 8
            workout_days = [
                (6 - 0, "Push A"),   # Push A = day 6 (end_date)
                (6 - 1, "Pull A"),   # Pull A = day 5
                (6 - 2, "Legs A"),   # Legs A = day 4
                (6 - 4, "Push B"),   # Push B = day 2
                (6 - 5, "Pull B"),   # Pull B = day 1
                (6 - 6, "Legs B"),   # Legs B = day 0
            ]
        
        workouts = parse_health_tracking_csv(
            filepath,
            end_date,
            workout_name_prefix=workout_name,
            cycle_days=cycle_days,
            workout_days_in_cycle=workout_days
        )
        
        all_workouts.extend(workouts)
        print(f"Processed {filepath}: {len(workouts)} sets (end_date={end_date.strftime('%Y-%m-%d')}, {cycle_days}-day cycle)")
    
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
        help='Input CSV files to process'
    )
    parser.add_argument(
        '-o', '--output',
        default='historical_workouts.csv',
        help='Output CSV file (default: historical_workouts.csv)'
    )
    parser.add_argument(
        '-f', '--file-config',
        action='append',
        help='Per-file config: filepath,end_date,workout_name'
    )
    
    args = parser.parse_args()
    
    if not args.input_files and not args.file_config:
        old_format_dir = Path('old_format')
        if old_format_dir.exists():
            args.input_files = [str(f) for f in sorted(old_format_dir.glob('*.csv'))]
            print(f"Found {len(args.input_files)} CSV files in old_format/")
        else:
            print("Error: No input files specified")
            return
    
    if args.file_config:
        file_configs = []
        for config_str in args.file_config:
            parts = config_str.split(',')
            if len(parts) < 2:
                print(f"Error: Invalid format: {config_str}")
                print("Expected: filepath,end_date,workout_name")
                return
            filepath = parts[0]
            
            try:
                end_date = datetime.strptime(parts[1], '%Y-%m-%d')
            except (ValueError, IndexError):
                print(f"Error: Invalid end_date: {parts[1]}")
                return
            
            workout_name = parts[2] if len(parts) > 2 else 'PPL'
            
            file_configs.append({
                'filepath': filepath,
                'end_date': end_date,
                'workout_name': workout_name
            })
    else:
        print("Error: Please specify files with -f option")
        print("Example: -f \"old_format/file.csv,2025-07-05,PPL\"")
        return
    
    merge_csv_files(file_configs, args.output)


if __name__ == '__main__':
    main()
