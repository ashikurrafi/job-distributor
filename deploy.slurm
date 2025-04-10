#!/bin/bash

#SBATCH --account=myuksel
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=3
#SBATCH --time=10:00:00
#SBATCH --error=slurm_log/jobserver-%J.err
#SBATCH --output=slurm_log/jobserver-%J.out
#SBATCH --job-name=jobserver
#SBATCH --mem-per-cpu=16000
#SBATCH --mail-type=begin,end,fail
#SBATCH --mail-user=abdurroufbd97@gmail.com

# ✅ Script execution starts here
echo "Slurm nodes assigned: $SLURM_JOB_NODELIST"

# ✅ Make sure log directory exists
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
