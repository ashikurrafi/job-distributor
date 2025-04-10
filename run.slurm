#!/bin/bash

#SBATCH --account=myuksel
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=3
#SBATCH --time=10:00:00
#SBATCH --error=jobserver-%J.err
#SBATCH --output=jobserver-%J.out
#SBATCH --job-name=jobserver
#SBATCH --mem-per-cpu=16000
#SBATCH --mail-type=begin,end,fail
#SBATCH --mail-user=abdurroufbd97@gmail.com

echo "Slurm nodes assigned: $SLURM_JOB_NODELIST"

# Load Python
module load python/python-3.11.4-gcc-12.2.0

# Activate venv
source venv/bin/activate

# Upgrade pip and install dependencies
python -m pip install --upgrade pip
pip install --no-cache-dir -r requirements.txt

# Handle SIGTERM from scancel
trap 'echo "Caught SIGTERM. Attempting cleanup..."; python stop.py; exit 0' SIGTERM

# Launch main service
srun --ntasks=1 python start.py &
wait