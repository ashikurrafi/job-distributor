#!/bin/bash

# ---------------------------
# Configuration (edit these)
# ---------------------------
LOCAL_PORT=5050
REMOTE_PORT=5050
PRIVATE_KEY_PATH="$HOME/.ssh/id_rsa"      # Use full path for safety
USERNAME="arouf"                          # Your HPC username
LOGIN_NODE="stokes.ist.ucf.edu"           # Or newton.ist.ucf.edu
# ---------------------------

# Get the compute node from squeue
NODE=$(squeue -u "$USER" | awk 'NR==2 {print $NF}')

if [ -z "$NODE" ]; then
    echo "Error: No running job found for user $USER."
    exit 1
fi

echo "Detected compute node (Job Distributor): $NODE"
echo "Setting up SSH tunnel from localhost:${LOCAL_PORT} to ${NODE}:${REMOTE_PORT} via ${LOGIN_NODE}"

# Compose SSH command
SSH_CMD="ssh -L ${LOCAL_PORT}:${NODE}:${REMOTE_PORT} -i ${PRIVATE_KEY_PATH} ${USERNAME}@${LOGIN_NODE}"

# Echo the command
echo "Run this SSH command from your local machine"
echo "$SSH_CMD"
