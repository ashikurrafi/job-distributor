#!/bin/bash

#SBATCH --account=<GROUPID>
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=3
#SBATCH --time=<HH:MM:SS>
#SBATCH --error=slurm_log/job_distributor-%J.err
#SBATCH --output=slurm_log/job_distributor-%J.out
#SBATCH --job-name=job_distributor
#SBATCH --mem-per-cpu=8192
#SBATCH --mail-type=begin,end,fail
#SBATCH --mail-user=<YOUR_EMAIL_ADDR>

# Script execution starts here
echo "Slurm nodes assigned: $SLURM_JOB_NODELIST"

# Make sure log directory exists
mkdir -p slurm_log

# Load Python 3 (not 2.7!)
module load python/python-3.11.4-gcc-12.2.0

# Create venv if not exists
if [ ! -d "venv" ]; then
    python3 -m venv venv
fi

# Activate venv
source venv/bin/activate

# Upgrade pip and install requirements
python -m pip install --upgrade pip
pip install --no-cache-dir -r requirements.txt

# Trap for cleanup
trap 'echo "Caught SIGTERM. Running cleanup..."; python stop.py; exit 0' SIGTERM

# Start main service
python start.py &
wait
