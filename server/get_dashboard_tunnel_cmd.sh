#!/bin/bash

# ---------------------------
# Configuration
# ---------------------------
CONFIG_FILE="config.json"
PRIVATE_KEY_PATH="<PRIVATE_KEY_FILE>"   # Replace with your actual path
USERNAME="$USER"
LOGIN_NODE="hpc_host_name"
JOB_NAME="job_dist"
# ---------------------------

# 🧠 Check for jq
if ! command -v jq &> /dev/null; then
    echo "❌ 'jq' is required but not installed. Please install jq and try again."
    exit 1
fi

# 🧠 Load dashboard_port from config.json
if [ ! -f "$CONFIG_FILE" ]; then
    echo "❌ config.json not found in current directory."
    exit 1
fi

PORT=$(jq -r '.dashboard_port' "$CONFIG_FILE")

if [ -z "$PORT" ] || [ "$PORT" = "null" ]; then
    echo "❌ Could not extract 'dashboard_port' from config.json"
    exit 1
fi

LOCAL_PORT=$PORT
REMOTE_PORT=$PORT

# 🔍 Get the compute node for job with name $JOB_NAME
NODE=$(squeue -u "$USER" | awk -v job="$JOB_NAME" '$3 == job {print $NF; exit}')

if [ -z "$NODE" ]; then
    echo "❌ No running job found with name '$JOB_NAME' for user $USER."
    exit 1
fi

echo "📡 Monitoring port $PORT on node $NODE..."
echo "⏳ Waiting for dashboard to be deployed..."

# 🔁 Check every 1 second until port is open
while true; do
    IS_OPEN=$(ssh "$NODE" ss -ltn | grep -q ":$REMOTE_PORT" && echo "open" || echo "closed")
    
    if [ "$IS_OPEN" = "open" ]; then
        echo "✅ Dashboard is now live on $NODE:$PORT"

        # 🔑 Compose SSH command to be run on local machine
        SSH_CMD="ssh -L ${LOCAL_PORT}:${NODE}:${REMOTE_PORT} -i ${PRIVATE_KEY_PATH} ${USERNAME}@${LOGIN_NODE}"

        echo ""
        echo "👉 Run this SSH command from your local machine to access the dashboard:"
        echo "$SSH_CMD"
        break
    fi

    sleep 1
done
