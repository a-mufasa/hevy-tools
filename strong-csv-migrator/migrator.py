#!/usr/bin/env python3
"""
Strong CSV Migrator

Converts workout tracking spreadsheets (organized by week) to Strong CSV format
for import into Hevy app.
"""

import argparse
import csv
import re
from datetime import datetime, timedelta

# Exercise name mapping - grouped by Hevy name with source name variations
EXERCISE_NAME_MAP = {
    "Bench Press (Barbell)": ["Flat Bench Press"],
    "Bench Press (Dumbbell)": ["DB Flat Bench"],
    "Calf Press (Machine)": ["Calf Raise", "Calf Raises"],
    "Chest Dip (Weighted)": ["Weighted Dip"],
    "Chest Fly (Machine)": ["Chest Fly"],
    "Dead Bug": ["Dead Bugs"],
    "Dumbbell Row": ["DB Row"],
    "Face Pull": ["Face Pull", "Rear Delt"],
    "Hammer Curl (Dumbbell)": ["Hammer Curl", "Seated Hammer Curl"],
    "Hip Abduction (Machine)": ["Abductor (Outer)"],
    "Hip Adduction (Machine)": ["Adductor (Inner)"],
    "Incline Bench Press (Dumbbell)": ["DB Incline Bench"],
    "Incline Bench Press (Smith Machine)": ["Incline Smith Bench Press"],
    "Lat Pulldown (Cable)": ["Lat Pulldown"],
    "Lateral Raise (Dumbbell)": ["DB Lateral Raise", "Lateral Raise"],
    "Leg Extension (Machine)": ["Leg Extension"],
    "Leg Press Horizontal (Machine)": ["Leg Press"],
    "Low Cable Fly Crossovers": ["Incline Cable Fly"],
    "Lunge (Dumbbell)": ["Lunges"],
    "Preacher Curl (Dumbbell)": ["DB Preacher Curl", "Preacher Curl"],
    "Pull Up": ["Close Grip Pull-up"],
    "Romanian Deadlift (Dumbbell)": ["DB RDL"],
    "Rope Straight Arm Pulldown": ["Cable Pullover"],
    "Seated Chest Flys (Cable)": ["Cable Fly"],
    "Seated Leg Curl (Machine)": ["Leg Curl", "Seated Leg Curl"],
    "Seated Overhead Press (Dumbbell)": ["DB Overhead Press"],
    "Seated Row (Machine)": ["Row"],
    "Seated Shoulder Press (Machine)": ["Shoulder Press"],
    "Single Arm Cable Row": ["Single Arm Seated Row"],
    "Single Arm Lateral Raise (Cable)": ["Cable Lateral Raise"],
    "Single Arm Triceps Pushdown (Cable)": ["Single Arm Tricep Extension"],
    "Squat (Smith Machine)": ["Smith Squat"],
    "Straight Leg Deadlift": ["SLDL"],
    "Triceps Rope Pushdown": ["Tricep Pushdown", "Tricep Pushdowns", "Tricep Rope Extension"],
    "Wide Pull Up": ["Wide Grip Pull-up"],
}


def get_mapped_exercise_name(source_name: str) -> str:
    """
    Get the Hevy-compatible exercise name for a source exercise name.
    
    Args:
        source_name: Original exercise name from source CSV
        
    Returns:
        Mapped Hevy exercise name, or original name if no mapping exists
    """
    for hevy_name, source_names in EXERCISE_NAME_MAP.items():
        if source_name in source_names:
            return hevy_name
    return source_name


def get_week_columns(header_row: list[str]) -> dict[int, int]:
    """
    Get mapping of week number to column index, skipping Setup columns.
    
    Args:
        header_row: First row of CSV containing column headers
        
    Returns:
        Dict mapping week number to column index
    """
    week_map = {}
    for idx, cell in enumerate(header_row):
        cell_str = str(cell).strip()
        if 'Setup' in cell_str:
            continue
        week_match = re.search(r'Week\s*(\d+)', cell_str, re.IGNORECASE)
        if week_match:
            week_map[int(week_match.group(1))] = idx
    return week_map


def calculate_date_backwards(
    week_number: int,
    workout_day_index: int,
    end_date: datetime,
    cycle_days: int,
    total_weeks: int
) -> datetime:
    """
    Calculate workout date by working backwards from end_date.
    
    Args:
        week_number: Week number from spreadsheet (1-indexed)
        workout_day_index: Days back from end_date for this workout type
        end_date: Last workout date (anchor point)
        cycle_days: Days in one complete cycle (8 for PPL, 7 for ULPPL)
        total_weeks: Total number of weeks in the spreadsheet
        
    Returns:
        Calculated workout date
    """
    days_back = (total_weeks - week_number) * cycle_days + workout_day_index
    return end_date - timedelta(days=days_back)


def parse_health_tracking_csv(
    filepath: str,
    end_date: datetime,
    workout_name_prefix: str = "Workout",
    cycle_days: int = 8,
    workout_days_in_cycle: list[tuple[int, str]] = None,
    total_weeks: int = None
) -> list[dict]:
    """
    Parse a health tracking CSV file organized by weeks.
    
    Args:
        filepath: Path to the CSV file
        end_date: Last workout date (anchor point for backward calculation)
        workout_name_prefix: Base name for workouts (e.g., "PPL", "ULPPL")
        cycle_days: Days in one complete cycle (8 for PPL, 7 for ULPPL)
        workout_days_in_cycle: List of (days_back, workout_name) tuples for each workout type
        total_weeks: Total number of weeks (auto-detected if not provided)
    
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
    week_columns = get_week_columns(header_row)
    
    # Auto-detect total_weeks if not provided
    if total_weeks is None:
        total_weeks = max(week_columns.keys()) if week_columns else 0
    
    current_workout_day = None
    
    for row in rows[2:]:  # Skip header and subheader rows
        if not row or not row[0].strip():
            continue
        
        first_cell = row[0].strip()
        
        # Detect workout day headers (Day 1, Upper, Push A, etc.)
        if first_cell.startswith('Day') or first_cell in ['Upper', 'Lower', 'Push', 'Pull', 'Legs', 'Long Run']:
            current_workout_day = first_cell
            continue
        
        # Check for variations like "Push A", "Push B"
        for day_type in ['Push', 'Pull', 'Legs']:
            if first_cell.startswith(day_type):
                current_workout_day = first_cell
                break
        
        if not current_workout_day:
            continue
        
        exercise_name = first_cell
        
        # Find matching workout configuration from cycle
        workout_base = None
        workout_day_index = None
        
        for day_index, day_name in workout_days_in_cycle:
            if day_name in current_workout_day:
                workout_base = day_name
                workout_day_index = day_index
                break
        
        if workout_base is None:
            continue
        
        # Process each week column
        for week_num, col_idx in week_columns.items():
            if col_idx >= len(row):
                continue
            
            # Parse sets
            sets_cell = row[col_idx].strip()
            if not sets_cell:
                continue
            
            try:
                sets = int(sets_cell)
            except ValueError:
                continue
            
            if sets == 0:
                continue
            
            # Data columns after "Week X" are: Reps, Weight, Completed, Notes
            reps_idx = col_idx + 1
            weight_idx = col_idx + 2
            completed_idx = col_idx + 3
            notes_idx = col_idx + 4
            
            # Parse reps
            reps = None
            if reps_idx < len(row):
                reps_val = row[reps_idx].strip()
                if reps_val:
                    try:
                        reps = int(reps_val)
                    except ValueError:
                        pass
            
            if not reps:
                continue
            
            # Check if exercise was completed (TRUE in completed column)
            if completed_idx < len(row):
                completed_val = row[completed_idx].strip().upper()
                if completed_val != 'TRUE':
                    continue
            
            # Parse weight
            weight = 0
            if weight_idx < len(row):
                weight_val = row[weight_idx].strip()
                if weight_val and weight_val.upper() != 'N/A':
                    try:
                        weight = float(weight_val)
                    except ValueError:
                        pass
            
            # Parse notes (filter out YES/NO markers)
            notes = ""
            if notes_idx < len(row):
                notes_val = row[notes_idx].strip()
                if notes_val.upper() not in ('YES', 'NO', ''):
                    notes = notes_val
            
            # Calculate date
            workout_date = calculate_date_backwards(
                week_num,
                workout_day_index,
                end_date,
                cycle_days,
                total_weeks
            )
            
            full_workout_name = f"{workout_name_prefix} - {workout_base}"
            date_key = workout_date.strftime('%Y-%m-%d')
            exercise_key = (date_key, full_workout_name, exercise_name)
            
            # Track set order per exercise per workout
            current_set_order = set_order_counter.get(exercise_key, 0)
            
            # Create entries for each set
            for set_num in range(sets):
                current_set_order += 1
                workouts.append({
                    'Date': f"{date_key} 17:30:00",
                    'Workout Name': full_workout_name,
                    'Exercise Name': exercise_name,
                    'Set Order': current_set_order,
                    'Weight': weight,
                    'Reps': reps,
                    'Notes': notes if set_num == 0 else ''
                })
            
            set_order_counter[exercise_key] = current_set_order
    
    return workouts


def write_strong_csv(workouts: list[dict], output_path: str):
    """
    Write workouts to Strong CSV format (semicolon-delimited).
    
    Args:
        workouts: List of workout entries
        output_path: Output CSV file path
    """
    fieldnames = [
        'Date', 'Workout Name', 'Exercise Name', 'Set Order', 'Weight', 'Weight Unit',
        'Reps', 'RPE', 'Distance', 'Distance Unit', 'Seconds', 'Notes', 
        'Workout Notes', 'Workout Duration'
    ]
    
    # Sort by date, workout, exercise, and set order
    workouts_sorted = sorted(
        workouts, 
        key=lambda x: (x['Date'], x['Workout Name'], x['Exercise Name'], x['Set Order'])
    )
    
    with open(output_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, delimiter=';')
        writer.writeheader()
        
        for workout in workouts_sorted:
            exercise_name = workout['Exercise Name']
            mapped_name = get_mapped_exercise_name(exercise_name)
            
            row = {
                'Date': workout['Date'],
                'Workout Name': workout['Workout Name'],
                'Exercise Name': mapped_name,
                'Set Order': workout['Set Order'],
                'Weight': workout['Weight'],
                'Weight Unit': 'lbs',
                'Reps': workout['Reps'],
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
    """
    Merge multiple CSV files into a single Strong CSV.
    
    Args:
        file_configs: List of dicts with 'filepath', 'end_date', 'workout_name'
        output_path: Output CSV file path
    """
    all_workouts = []
    
    for config in file_configs:
        filepath = config['filepath']
        end_date = config['end_date']
        workout_name = config.get('workout_name', 'PPL')
        
        if end_date is None:
            print(f"Error: No end_date provided for {filepath}")
            continue
        
        # Define cycle parameters
        # IMPORTANT: end_date is the LAST workout date (anchor point)
        # workout_days tuples are (days_back, workout_name)
        
        if workout_name == "ULPPL":
            # ULPPL: 7-day cycle: Upper(0), Lower(1), Rest(2), Push(3), Pull(4), Legs(5), Rest(6)
            # End date = Upper (last Upper in the program = Feb 13)
            # Upper is day 0, so offset 0 means it lands on end_date
            # Other workouts have negative offsets to come AFTER Upper chronologically
            cycle_days = 7
            workout_days = [
                (0, "Upper"),   # Upper is day 0: end_date (Feb 13)
                (-1, "Lower"),  # Lower is day 1: 1 day after Upper
                (-3, "Push"),   # Push is day 3: 3 days after Upper  
                (-4, "Pull"),   # Pull is day 4: 4 days after Upper
                (-5, "Legs"),   # Legs is day 5: 5 days after Upper
            ]
        else:  # PPL
            # PPL: 8-day cycle: Push A, Pull A, Legs A, Rest, Push B, Pull B, Legs B, Rest
            # End date = Legs B (day 6 of cycle)
            cycle_days = 8
            workout_days = [
                (6, "Push A"),  # 6 days back from end_date
                (5, "Pull A"),  # 5 days back
                (4, "Legs A"),  # 4 days back
                (2, "Push B"),  # 2 days back
                (1, "Pull B"),  # 1 day back
                (0, "Legs B"),  # 0 days back (end_date)
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
    """Main entry point for the migrator."""
    parser = argparse.ArgumentParser(
        description='Convert health tracking CSVs to Strong CSV format for Hevy import',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Example usage:
  %(prog)s -f "file1.csv,2025-07-05,PPL" -f "file2.csv,2026-02-13,ULPPL"
  
Format for -f parameter: "filepath,end_date,workout_name"
  - filepath: Path to CSV file
  - end_date: Last workout date in YYYY-MM-DD format
  - workout_name: PPL or ULPPL
        """
    )
    parser.add_argument(
        '-f', '--file-config',
        action='append',
        required=True,
        metavar='CONFIG',
        help='Per-file config: "filepath,end_date,workout_name"'
    )
    parser.add_argument(
        '-o', '--output',
        default='historical_workouts.csv',
        help='Output CSV file (default: historical_workouts.csv)'
    )
    
    args = parser.parse_args()
    
    file_configs = []
    for config_str in args.file_config:
        parts = config_str.split(',')
        if len(parts) < 2:
            print(f"Error: Invalid format: {config_str}")
            print('Expected: "filepath,end_date,workout_name"')
            print('Example: "data.csv,2025-07-05,PPL"')
            return
        
        filepath = parts[0].strip()
        
        try:
            end_date = datetime.strptime(parts[1].strip(), '%Y-%m-%d')
        except (ValueError, IndexError):
            print(f"Error: Invalid date format: {parts[1]}")
            print("Expected format: YYYY-MM-DD")
            return
        
        workout_name = parts[2].strip() if len(parts) > 2 else 'PPL'
        
        if workout_name not in ['PPL', 'ULPPL']:
            print(f"Warning: Unknown workout type '{workout_name}', using PPL")
            workout_name = 'PPL'
        
        file_configs.append({
            'filepath': filepath,
            'end_date': end_date,
            'workout_name': workout_name
        })
    
    merge_csv_files(file_configs, args.output)


if __name__ == '__main__':
    main()
