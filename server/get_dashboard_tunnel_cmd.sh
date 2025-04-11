#!/bin/bash

# ---------------------------
# Configuration
# ---------------------------
CONFIG_FILE="config.json"
PRIVATE_KEY_PATH="<PRIVATE_KEY_FILE>"   # Replace with your actual path
USERNAME="$USER"
LOGIN_NODE="stokes.ist.ucf.edu"
JOB_NAME="job_dist"
# ---------------------------

# 🧠 Extract dashboard_port from config.json using jq
if ! command -v jq &> /dev/null; then
    echo "❌ 'jq' is required but not installed. Please install jq and try again."
    exit 1
fi

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

# 🔍 Check if dashboard port is open on compute node
IS_OPEN=$(ssh -i ${PRIVATE_KEY_PATH} ${USERNAME}@${LOGIN_NODE} "ssh $NODE ss -ltn | grep -q ':$REMOTE_PORT' && echo 'open' || echo 'closed'")

if [ "$IS_OPEN" = "open" ]; then
    # ✅ Compose SSH command
    SSH_CMD="ssh -L ${LOCAL_PORT}:${NODE}:${REMOTE_PORT} -i ${PRIVATE_KEY_PATH} ${USERNAME}@${LOGIN_NODE}"

    # 💡 Output the tunnel command
    echo "📡 Detected compute node: $NODE"
    echo "🌐 Dashboard port: $PORT is active!"
    echo ""
    echo "👉 Run this SSH command from your local machine:"
    echo "$SSH_CMD"
else
    echo "⏳ Waiting for dashboard to be deployed on $NODE:$PORT..."
fi
