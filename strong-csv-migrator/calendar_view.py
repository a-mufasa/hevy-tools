#!/usr/bin/env python3
"""
Calendar View Generator

Reads historical_workouts.csv (Strong CSV format) and displays a calendar view
of workouts for easy QA/verification.
"""

import argparse
import csv
from collections import defaultdict
from datetime import datetime


def parse_strong_csv(filepath: str) -> dict:
    """
    Parse Strong CSV format and group by date.
    
    Args:
        filepath: Path to historical_workouts.csv
        
    Returns:
        Dict mapping date string to list of workout types
    """
    workouts_by_date = defaultdict(set)
    
    with open(filepath, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f, delimiter=';')
        for row in reader:
            date_str = row['Date'].split()[0]  # Get just the date part (YYYY-MM-DD)
            workout_name = row['Workout Name']
            workouts_by_date[date_str].add(workout_name)
    
    return workouts_by_date


def print_calendar_view(workouts_by_date: dict, start_date: str = None, end_date: str = None):
    """
    Print a calendar view of workouts.
    
    Args:
        workouts_by_date: Dict mapping date to set of workout names
        start_date: Optional start date filter (YYYY-MM-DD)
        end_date: Optional end date filter (YYYY-MM-DD)
    """
    # Get all dates and sort them
    all_dates = sorted(workouts_by_date.keys())
    
    if not all_dates:
        print("No workouts found.")
        return
    
    # Apply date filters
    if start_date:
        all_dates = [d for d in all_dates if d >= start_date]
    if end_date:
        all_dates = [d for d in all_dates if d <= end_date]
    
    if not all_dates:
        print(f"No workouts found between {start_date} and {end_date}")
        return
    
    print(f"\n{'='*80}")
    print(f"WORKOUT CALENDAR VIEW")
    print(f"{'='*80}")
    print(f"Date Range: {all_dates[0]} to {all_dates[-1]}")
    print(f"Total Workout Days: {len(all_dates)}")
    print(f"{'='*80}\n")
    
    current_month = None
    
    for date_str in all_dates:
        date_obj = datetime.strptime(date_str, '%Y-%m-%d')
        month_year = date_obj.strftime('%B %Y')
        
        # Print month header when month changes
        if month_year != current_month:
            if current_month is not None:
                print()  # Blank line between months
            print(f"\n{month_year}")
            print("-" * 60)
            current_month = month_year
        
        # Format workout names
        workouts = sorted(workouts_by_date[date_str])
        workout_str = ", ".join(workouts)
        
        # Get day of week
        day_name = date_obj.strftime('%a')
        
        print(f"{date_str} ({day_name:>3}): {workout_str}")


def print_summary(workouts_by_date: dict):
    """
    Print summary statistics.
    
    Args:
        workouts_by_date: Dict mapping date to set of workout names
    """
    all_dates = sorted(workouts_by_date.keys())
    
    if not all_dates:
        print("No workouts found.")
        return
    
    # Count workout types
    workout_type_counts = defaultdict(int)
    for workouts in workouts_by_date.values():
        for workout in workouts:
            workout_type_counts[workout] += 1
    
    # Find gaps (missing days between first and last workout)
    start_date = datetime.strptime(all_dates[0], '%Y-%m-%d')
    end_date = datetime.strptime(all_dates[-1], '%Y-%m-%d')
    total_days = (end_date - start_date).days + 1
    workout_days = len(all_dates)
    rest_days = total_days - workout_days
    
    print(f"\n{'='*80}")
    print(f"SUMMARY STATISTICS")
    print(f"{'='*80}")
    print(f"Date Range: {all_dates[0]} to {all_dates[-1]}")
    print(f"Total Days in Range: {total_days}")
    print(f"Workout Days: {workout_days}")
    print(f"Rest Days: {rest_days}")
    print(f"\nWorkout Type Breakdown:")
    for workout_type, count in sorted(workout_type_counts.items()):
        print(f"  {workout_type}: {count} days")
    print(f"{'='*80}\n")


def find_gaps(workouts_by_date: dict, min_gap_days: int = 7):
    """
    Find gaps of N or more days without workouts.
    
    Args:
        workouts_by_date: Dict mapping date to set of workout names
        min_gap_days: Minimum gap size to report (default 7 days)
    """
    all_dates = sorted(workouts_by_date.keys())
    
    if len(all_dates) < 2:
        return
    
    gaps = []
    
    for i in range(len(all_dates) - 1):
        current_date = datetime.strptime(all_dates[i], '%Y-%m-%d')
        next_date = datetime.strptime(all_dates[i + 1], '%Y-%m-%d')
        gap_days = (next_date - current_date).days - 1
        
        if gap_days >= min_gap_days:
            gaps.append((all_dates[i], all_dates[i + 1], gap_days))
    
    if gaps:
        print(f"\n{'='*80}")
        print(f"GAPS ({min_gap_days}+ days without workouts)")
        print(f"{'='*80}")
        for start, end, days in gaps:
            print(f"{start} to {end}: {days} day gap")
        print(f"{'='*80}\n")
    else:
        print(f"\nNo gaps of {min_gap_days}+ days found.\n")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='View workout calendar from Strong CSV format',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                           # Show all workouts
  %(prog)s --start 2026-01-01        # Show workouts from Jan 2026
  %(prog)s --start 2026-01-01 --end 2026-01-31  # Show January 2026
  %(prog)s --summary                 # Show summary statistics
  %(prog)s --gaps 5                  # Find gaps of 5+ days
        """
    )
    parser.add_argument(
        'input_file',
        nargs='?',
        default='historical_workouts.csv',
        help='Input CSV file (default: historical_workouts.csv)'
    )
    parser.add_argument(
        '--start',
        help='Start date filter (YYYY-MM-DD)'
    )
    parser.add_argument(
        '--end',
        help='End date filter (YYYY-MM-DD)'
    )
    parser.add_argument(
        '--summary',
        action='store_true',
        help='Show summary statistics'
    )
    parser.add_argument(
        '--gaps',
        type=int,
        metavar='N',
        help='Find gaps of N or more days without workouts'
    )
    
    args = parser.parse_args()
    
    # Parse the CSV
    workouts_by_date = parse_strong_csv(args.input_file)
    
    # Show summary if requested
    if args.summary:
        print_summary(workouts_by_date)
    
    # Find gaps if requested
    if args.gaps:
        find_gaps(workouts_by_date, args.gaps)
    
    # Always show calendar view (unless only summary/gaps requested)
    if not (args.summary or args.gaps):
        print_calendar_view(workouts_by_date, args.start, args.end)


if __name__ == '__main__':
    main()
