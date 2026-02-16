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


def calculate_date_for_week(
    week_number: int,
    start_date: datetime,
    day_of_week: int = 0
) -> datetime:
    """
    Calculate the date for a given week number.
    
    Args:
        week_number: The week number (1-indexed)
        start_date: The start date of week 1
        day_of_week: Day offset within the week (0=Monday, 6=Sunday, default 0)
    
    Returns:
        The calculated date for that week
    """
    days_offset = (week_number - 1) * 7 + day_of_week
    return start_date + timedelta(days=days_offset)


def parse_week_number(week_str: str) -> Optional[int]:
    """Extract week number from string like 'Week 1' or 'Week 10'."""
    match = re.search(r'Week\s*(\d+)', week_str, re.IGNORECASE)
    if match:
        return int(match.group(1))
    return None


def is_valid_week_column(header: str) -> bool:
    """Check if a header represents a week column."""
    week_num = parse_week_number(header)
    return week_num is not None


def parse_health_tracking_csv(
    filepath: str,
    start_date: datetime,
    end_date: Optional[datetime] = None,
    workout_name: str = "Workout",
    day_offset: int = 0
) -> list[dict]:
    """
    Parse a health tracking CSV file organized by weeks.
    
    Args:
        filepath: Path to the CSV file
        start_date: Start date for Week 1
        end_date: Optional end date (used to determine week calculation method)
        workout_name: Base name for workouts
        day_offset: Default day of week to schedule workouts (0=Mon, 6=Sun)
    
    Returns:
        List of workout entries in Strong CSV format
    """
    workouts = []
    
    with open(filepath, 'r', encoding='utf-8') as f:
        reader = csv.reader(f)
        rows = list(reader)
    
    if len(rows) < 2:
        return workouts
    
    header_row = rows[0]
    subheader_row = rows[1] if len(rows) > 1 else []
    
    week_columns = {}
    for idx, cell in enumerate(header_row):
        cell_str = str(cell).strip()
        # Skip Setup columns - only process Week X columns
        if 'Setup' in cell_str:
            continue
        week_num = parse_week_number(cell_str)
        if week_num:
            week_columns[week_num] = idx
    
    current_day = None
    for row_idx, row in enumerate(rows[2:], start=2):
        if not row or not row[0].strip():
            continue
        
        first_cell = row[0].strip()
        
        if first_cell.startswith('Day'):
            current_day = first_cell
            continue
        
        if first_cell in ['Upper', 'Lower', 'Push', 'Pull', 'Legs', 'Long Run']:
            current_day = first_cell
            continue
        
        exercise_name = first_cell
        if not exercise_name:
            continue
        
        for week_num, col_idx in week_columns.items():
            if col_idx >= len(row):
                continue
            
            sets_cell = row[col_idx] if col_idx < len(row) else ""
            
            if not sets_cell or sets_cell.strip() == "":
                continue
            
            try:
                sets = int(sets_cell) if sets_cell.strip() else None
            except ValueError:
                continue
            
            if sets is None or sets == 0:
                continue
            
            reps_idx = col_idx + 1
            weight_idx = col_idx + 2
            completed_idx = col_idx + 3
            notes_idx = col_idx + 4
            
            reps = None
            weight = None
            completed = True
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
                # Only include if TRUE - exclude FALSE entries
                if completed_val != 'TRUE':
                    continue
            
            if notes_idx < len(row):
                notes = row[notes_idx].strip()
            
            if reps is None or reps == 0:
                continue
            
            workout_date = calculate_date_for_week(week_num, start_date, day_offset)
            
            full_workout_name = f"{workout_name} - {current_day}" if current_day else workout_name
            
            for set_num in range(sets):
                workouts.append({
                    'Date': workout_date.strftime('%Y-%m-%d'),
                    'Workout Name': full_workout_name,
                    'Exercise Name': exercise_name,
                    'Weight': weight if weight else 0,
                    'Reps': reps,
                    'RPE': '',
                    'Notes': notes if set_num == 0 else ''
                })
    
    return workouts


def parse_ppl_csv(
    filepath: str,
    start_date: datetime,
    end_date: Optional[datetime] = None,
    day_offset: int = 0
) -> list[dict]:
    """
    Parse the PPL format CSV (first file format).
    
    This format has a complex header structure with Setup week and numbered weeks.
    """
    workouts = []
    
    with open(filepath, 'r', encoding='utf-8') as f:
        reader = csv.reader(f)
        rows = list(reader)
    
    if len(rows) < 3:
        return workouts
    
    header_row = rows[0]
    
    week_map = {}
    for idx, cell in enumerate(header_row):
        cell_str = str(cell).strip()
        # Skip Setup columns - only process Week X columns
        if 'Setup' in cell_str:
            continue
        week_num = parse_week_number(cell_str)
        if week_num:
            week_map[week_num] = idx
    
    current_day = None
    current_exercise = None
    
    for row_idx, row in enumerate(rows):
        if not row or not row[0].strip():
            continue
        
        first_cell = row[0].strip()
        
        if first_cell.startswith('Day'):
            current_day = first_cell
            current_exercise = None
            continue
        
        exercise_name = first_cell
        if exercise_name in ['Setup']:
            continue
        
        current_exercise = exercise_name
        
        for week_num, col_idx in week_map.items():
            if col_idx >= len(row):
                continue
            
            sets_cell = row[col_idx].strip() if col_idx < len(row) else ""
            
            if not sets_cell or sets_cell == "":
                continue
            
            try:
                sets = int(sets_cell) if sets_cell and sets_cell != '' else None
            except ValueError:
                continue
            
            if sets is None or sets == 0:
                continue
            
            reps_idx = col_idx + 1
            weight_idx = col_idx + 2
            completed_idx = col_idx + 3
            notes_idx = col_idx + 4
            
            reps = None
            weight = None
            completed = True
            notes = ""
            
            if reps_idx < len(row):
                reps_val = row[reps_idx].strip()
                if reps_val:
                    try:
                        reps = int(reps_val)
                    except ValueError:
                        pass
            
            if weight_idx < len(row):
                weight_val = row[weight_idx].strip()
                if weight_val and weight_val.upper() != 'N/A':
                    try:
                        weight = float(weight_val)
                    except ValueError:
                        pass
            
            if completed_idx < len(row):
                completed_val = row[completed_idx].strip().upper()
                # Only include if TRUE - exclude FALSE entries
                if completed_val != 'TRUE':
                    continue
            
            if notes_idx < len(row):
                notes = row[notes_idx].strip()
            
            if reps is None or reps == 0:
                continue
            
            week_for_date = week_num if week_num > 0 else 1
            workout_date = calculate_date_for_week(week_for_date, start_date, day_offset)
            
            full_workout_name = f"PPL - {current_day}" if current_day else "PPL Workout"
            
            for set_num in range(sets):
                workouts.append({
                    'Date': workout_date.strftime('%Y-%m-%d'),
                    'Workout Name': full_workout_name,
                    'Exercise Name': exercise_name,
                    'Weight': weight if weight else 0,
                    'Reps': reps,
                    'RPE': '',
                    'Notes': notes if set_num == 0 else ''
                })
    
    return workouts


def write_strong_csv(workouts: list[dict], output_path: str):
    """Write workouts to Strong CSV format."""
    fieldnames = ['Date', 'Workout Name', 'Exercise Name', 'Weight', 'Reps', 'RPE', 'Notes']
    
    workouts_sorted = sorted(workouts, key=lambda x: (x['Date'], x['Workout Name'], x['Exercise Name']))
    
    with open(output_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(workouts_sorted)


def merge_csv_files(file_configs: list[dict], output_path: str):
    """
    Merge multiple CSV files into a single Strong CSV.
    
    Args:
        file_configs: List of dicts with keys: filepath, start_date, end_date, workout_name, day_offset
        output_path: Path for the merged output
    """
    all_workouts = []
    
    for config in file_configs:
        filepath = config['filepath']
        start_date = config['start_date']
        workout_name = config.get('workout_name', 'Workout')
        day_offset = config.get('day_offset', 0)
        
        workouts = parse_health_tracking_csv(
            filepath,
            start_date,
            workout_name=workout_name,
            day_offset=day_offset
        )
        
        all_workouts.extend(workouts)
        print(f"Processed {filepath}: {len(workouts)} sets")
    
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
        '-s', '--start-date',
        help='Start date for Week 1 (YYYY-MM-DD). Applied to all files unless using --file-config'
    )
    parser.add_argument(
        '-w', '--workout-name',
        default='Workout',
        help='Base name for workouts (default: Workout)'
    )
    parser.add_argument(
        '-d', '--day-offset',
        type=int,
        default=0,
        help='Day of week for workouts: 0=Mon, 1=Tue, ..., 6=Sun (default: 0)'
    )
    parser.add_argument(
        '-f', '--file-config',
        action='append',
        help='Per-file config in format: filepath,start_date,workout_name,day_offset'
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
                print("Expected: filepath,start_date[,workout_name[,day_offset]]")
                return
            filepath = parts[0]
            start_date = datetime.strptime(parts[1], '%Y-%m-%d')
            workout_name = parts[2] if len(parts) > 2 else args.workout_name
            day_offset = int(parts[3]) if len(parts) > 3 else args.day_offset
            file_configs.append({
                'filepath': filepath,
                'start_date': start_date,
                'workout_name': workout_name,
                'day_offset': day_offset
            })
    else:
        # Use global args for all files
        if not args.start_date:
            print("Error: --start-date is required unless using --file-config")
            return
        
        start_date = datetime.strptime(args.start_date, '%Y-%m-%d')
        file_configs = []
        for filepath in args.input_files:
            file_configs.append({
                'filepath': filepath,
                'start_date': start_date,
                'workout_name': args.workout_name,
                'day_offset': args.day_offset
            })
    
    merge_csv_files(file_configs, args.output)


if __name__ == '__main__':
    main()
