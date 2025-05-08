import pandas as pd
import numpy as np
from datetime import datetime

def analyze_job_completion_times(csv_path='raw_dataset.csv'):
    # Read the CSV file
    try:
        df = pd.read_csv(csv_path)
        print(f"Successfully loaded CSV with {len(df)} rows")
    except Exception as e:
        print(f"Error loading CSV: {e}")
        return None, None, None, None
    
    # Print the column names to verify
    print(f"Columns in CSV: {df.columns.tolist()}")
    
    # Filter specifically for 'DONE' status
    if 'status' in df.columns:
        completed_jobs = df[df['status'] == 'DONE']
        print(f"\nFound {len(completed_jobs)} jobs with status 'DONE'")
    else:
        print("Warning: 'status' column not found in the CSV")
        completed_jobs = df
    
    # Check if we have any jobs with DONE status
    if len(completed_jobs) == 0:
        print("No jobs with 'DONE' status found in the CSV")
        return None, None, None, None
    
    # Make sure required columns exist
    required_cols = ['requested_by', 'request_timestamp', 'completion_timestamp']
    for col in required_cols:
        if col not in df.columns:
            print(f"Error: Required column '{col}' not found in the CSV")
            return None, None, None, None
    
    # Calculate job duration
    try:
        completed_jobs['job_duration'] = completed_jobs['completion_timestamp'] - completed_jobs['request_timestamp']
        
        # Filter out negative or zero durations (these are likely errors)
        valid_jobs = completed_jobs[completed_jobs['job_duration'] > 0]
        if len(valid_jobs) < len(completed_jobs):
            print(f"Filtered out {len(completed_jobs) - len(valid_jobs)} jobs with invalid durations")
        
        completed_jobs = valid_jobs
    except Exception as e:
        print(f"Error calculating job durations: {e}")
        return None, None, None, None
    
    # Check if we have any valid jobs to analyze
    if len(completed_jobs) == 0:
        print("No valid jobs found for analysis")
        return None, None, None, None
    
    print(f"Analyzing completion times for {len(completed_jobs)} jobs")
    
    # Find the first and last completed jobs
    earliest_request = completed_jobs.loc[completed_jobs['request_timestamp'].idxmin()]
    latest_completion = completed_jobs.loc[completed_jobs['completion_timestamp'].idxmax()]
    
    # Calculate statistics for each machine
    machine_stats = completed_jobs.groupby('requested_by')['job_duration'].agg([
        ('min', 'min'),
        ('max', 'max'),
        ('mean', 'mean'),
        ('count', 'count')
    ]).reset_index()
    
    # Convert seconds to hours and days
    machine_stats['min_hours'] = machine_stats['min'] / 3600
    machine_stats['max_hours'] = machine_stats['max'] / 3600
    machine_stats['mean_hours'] = machine_stats['mean'] / 3600
    machine_stats['min_days'] = machine_stats['min'] / (3600 * 24)
    machine_stats['max_days'] = machine_stats['max'] / (3600 * 24)
    machine_stats['mean_days'] = machine_stats['mean'] / (3600 * 24)
    
    # Sort by maximum job duration (descending)
    machine_stats = machine_stats.sort_values(by='max', ascending=False)
    
    # Global statistics
    stats = {
        'total_machines': len(machine_stats),
        'total_jobs': len(completed_jobs),
        'global_min_duration': completed_jobs['job_duration'].min(),
        'global_max_duration': completed_jobs['job_duration'].max(),
        'global_avg_duration': completed_jobs['job_duration'].mean(),
        'global_min_hours': completed_jobs['job_duration'].min() / 3600,
        'global_max_hours': completed_jobs['job_duration'].max() / 3600,
        'global_avg_hours': completed_jobs['job_duration'].mean() / 3600,
        'total_elapsed_time': latest_completion['completion_timestamp'] - earliest_request['request_timestamp'],
        'total_elapsed_hours': (latest_completion['completion_timestamp'] - earliest_request['request_timestamp']) / 3600,
        'total_elapsed_days': (latest_completion['completion_timestamp'] - earliest_request['request_timestamp']) / (3600 * 24)
    }
    
    return machine_stats, stats, earliest_request, latest_completion

def format_timestamp(timestamp):
    """Convert Unix timestamp to readable date/time format"""
    try:
        return datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S')
    except:
        return str(timestamp)

def format_duration(seconds):
    """Convert duration in seconds to days, hours, minutes format"""
    days = int(seconds // (24 * 3600))
    seconds %= (24 * 3600)
    hours = int(seconds // 3600)
    seconds %= 3600
    minutes = int(seconds // 60)
    seconds %= 60
    return f"{days} days, {hours} hours, {minutes} minutes, {int(seconds)} seconds"

if __name__ == "__main__":
    machine_stats, stats, first_job, last_job = analyze_job_completion_times()
    
    if machine_stats is not None and stats is not None:
        # Print the global statistics
        print("\n=== GLOBAL STATISTICS ===")
        print(f"Total completed jobs: {stats['total_jobs']}")
        print(f"Total unique machines: {stats['total_machines']}")
        print(f"Global minimum job duration: {format_duration(stats['global_min_duration'])}")
        print(f"Global maximum job duration: {format_duration(stats['global_max_duration'])}")
        print(f"Global average job duration: {format_duration(stats['global_avg_duration'])}")
        
        # Print info about first and last jobs
        print("\n=== TIMELINE INFORMATION ===")
        print("First job request:")
        print(f"  ID: {first_job['id']}")
        print(f"  Requested by: {first_job['requested_by']}")
        print(f"  Request timestamp: {format_timestamp(first_job['request_timestamp'])}")
        
        print("\nLast job completion:")
        print(f"  ID: {last_job['id']}")
        print(f"  Requested by: {last_job['requested_by']}")
        print(f"  Completion timestamp: {format_timestamp(last_job['completion_timestamp'])}")
        
        print("\nTotal elapsed time from first job request to last job completion:")
        print(f"  {format_duration(stats['total_elapsed_time'])}")
        
        # Print top 10 machines with highest maximum completion times
        print("\n=== TOP 10 MACHINES BY MAXIMUM COMPLETION TIME ===")
        pd.set_option('display.float_format', '{:.2f}'.format)
        top_machines = machine_stats.head(10)
        
        # Create a formatted table for display
        display_cols = ['requested_by', 'count', 'min', 'max', 'mean', 'min_hours', 'max_hours', 'mean_hours']
        display_df = top_machines[display_cols].copy()
        display_df.columns = ['Machine', 'Jobs', 'Min (s)', 'Max (s)', 'Avg (s)', 'Min (h)', 'Max (h)', 'Avg (h)']
        print(display_df.to_string(index=False))
        
        # Print bottom 10 machines with lowest maximum completion times
        print("\n=== BOTTOM 10 MACHINES BY MAXIMUM COMPLETION TIME ===")
        bottom_machines = machine_stats.tail(10).iloc[::-1]  # Reverse to show in ascending order
        display_df = bottom_machines[display_cols].copy()
        display_df.columns = ['Machine', 'Jobs', 'Min (s)', 'Max (s)', 'Avg (s)', 'Min (h)', 'Max (h)', 'Avg (h)']
        print(display_df.to_string(index=False))
        
        # Save the full results to a CSV file
        machine_stats.to_csv('machine_completion_times.csv', index=False)
        print("\nFull results saved to 'machine_completion_times.csv'")
    else:
        print("\nAnalysis failed. Check the error messages above.")
