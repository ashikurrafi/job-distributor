#!/bin/bash

# Look for job with NAME=job_distributor and get its JOBID
JOBID=$(squeue -u "$USER" | awk '$3 == "job_distributor" {print $1; exit}')

# Check if a matching job was found
if [ -z "$JOBID" ]; then
    echo "No job found with name 'job_distributor' for user $USER."
    exit 1
fi

echo "Found job 'job_distributor' with JOBID: $JOBID"
echo "Cancelling job..."
scancel "$JOBID"

# Confirm result
if [ $? -eq 0 ]; then
    echo "Job $JOBID cancelled successfully."
else
    echo "Failed to cancel job $JOBID."
fi
