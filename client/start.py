import json
import os
import subprocess
import logging
import socket

# ---------------- Load Config ----------------
CONFIG_PATH = "config.json"
with open(CONFIG_PATH, "r") as f:
    config = json.load(f)

exp_id = config["expId"]
job_server = config["job_server"]
port = config["port"]
num_processes = config["number_of_parallel_process"]

api_url = f"{job_server}:{port}"
exp_dir = os.path.join(exp_id)
os.makedirs(exp_dir, exist_ok=True)

# ---------------- Logger Setup ----------------
user = os.getenv("USER") or os.getenv("USERNAME") or "unknown_user"
host = socket.gethostname()
log_filename = f"start_{user}@{host}.log"
log_path = os.path.join(exp_dir, log_filename)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(log_path),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# ---------------- Launch Runners ----------------
processes = []

logger.info(f"🚀 Starting {num_processes} runners for experiment '{exp_id}'")
logger.info(f"📡 API URL: {api_url}")
for i in range(1, num_processes + 1):
    cmd = [
        "python", "runner.py",
        "--api_url", api_url,
        "--process_id", str(i),
        "--expId", exp_id
    ]
    log_file = os.path.join(exp_dir, f"runner_{i}.log")
    logger.info(f"📌 Launching runner {i}: {' '.join(cmd)} → {log_file}")

    with open(log_file, "w") as logf:
        proc = subprocess.Popen(cmd, stdout=logf, stderr=logf)
        processes.append(proc)

# ---------------- Wait for Completion ----------------
for i, proc in enumerate(processes, start=1):
    proc.wait()
    logger.info(f"✅ Runner {i} completed.")
