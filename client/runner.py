import requests
import subprocess
import os
import socket
import time
import logging
import argparse
import signal
import sys
import json
import threading

# --------------- Read Config -------------------
CONFIG_PATH = "config.json"
with open(CONFIG_PATH, "r") as f:
    config = json.load(f)

expId = config["expId"]
job_server = config["job_server"]
port = config["port"]
run_command = config["run_command"]  # list, e.g., ["python", "main.py"]
machine_type = config["machine_type"]
heartBitInterval = config["heartBitInterval"] - 0.3  
# seconds, added 300 ms to avoid exact timing issues which will tolerate network latency

# --------------- Argument Parser ----------------
parser = argparse.ArgumentParser()
parser.add_argument("--process_id", type=int, default=0, help="Give a process id for log tracking")
args = parser.parse_args()

# --------------- Logger Setup ----------------
LOG_DIR = f"{expId}/logs"
os.makedirs(LOG_DIR, exist_ok=True)

username = "user" if os.getenv('USER') or os.getenv('USERNAME') is None else os.getenv('USER') or os.getenv('USERNAME')
runner_id = f"{username}@{socket.gethostname()}({machine_type})"
log_path = os.path.join(LOG_DIR, f"runner_{runner_id}_{args.process_id}.log")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(log_path),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# --------------- Constants ----------------
REQUEST_JOB_URL = f"{job_server}:{port}/request_job"
UPDATE_JOB_URL = f"{job_server}:{port}/update_job_status"
PING_URL = f"{job_server}:{port}/ping"

# Track the current child process
current_proc = None

# --------------- Cleanup Handler ----------------
def cleanup(signum=None, frame=None):
    global current_proc
    if current_proc and current_proc.poll() is None:
        logger.info(f"Terminating subprocess with PID {current_proc.pid}")
        try:
            os.killpg(os.getpgid(current_proc.pid), signal.SIGTERM)
        except Exception as e:
            logger.warning(f"Could not kill subprocess group: {e}")
    logger.info("Runner shutting down.")
    sys.exit(0)

signal.signal(signal.SIGINT, cleanup)
signal.signal(signal.SIGTERM, cleanup)

# --------------- Heartbeat Pinger ----------------
def ping_job(job_id, stop_event):
    while not stop_event.is_set():
        try:
            res = requests.post(PING_URL, json={"id": job_id})
            if res.status_code == 200:
                logger.info(f"Ping sent for job {job_id}")
            else:
                logger.warning(f"Ping failed for job {job_id}: {res.status_code} {res.text}")
        except Exception as e:
            logger.warning(f"Ping exception for job {job_id}: {e}")
        time.sleep(heartBitInterval)

# --------------- Job Status Update ----------------
def update_status(job_id, status, message):
    try:
        res = requests.post(UPDATE_JOB_URL, json={
            "job_id": job_id,
            "status": status,
            "message": message
        })
        if res.status_code == 200:
            logger.info(f"Job {job_id} status updated to {status}.")
        else:
            logger.warning(f"Failed to update status for job {job_id}: {res.text}")
    except Exception as e:
        logger.error(f"Error while updating job status: {str(e)}")

# --------------- Main Loop ----------------
def main():
    global current_proc
    logger.info(f"Runner started as {runner_id}_{args.process_id}")
    logger.info(f"Job Server URL: {job_server}:{port}")
    logger.info(f"Heart bit interval set to {heartBitInterval} seconds")

    while True:
        try:
            logger.info("Requesting a new job...")
            response = requests.post(REQUEST_JOB_URL, json={"requested_by": runner_id})

            if response.status_code == 404:
                logger.info("No more jobs available. Runner exiting.")
                break

            if response.status_code != 200:
                logger.error(f"Failed to request job. Status: {response.status_code}, Msg: {response.text}")
                time.sleep(2)
                continue

            job_info = response.json()
            job_id = job_info["job_id"]
            params = job_info["parameters"]

            logger.info(f"Job {job_id} assigned with params: {params}")

            # Build the command
            cmd = list(run_command)
            for key, value in params.items():
                cmd.extend([f"--{key}", str(value)])

            base_path = os.path.join(os.path.expanduser("~"), "data", "raw", expId, str(job_id))
            cmd.extend(["--base_path", base_path])
            logger.info(f"Running command: {' '.join(cmd)}")

            # Start heartbeat thread
            stop_event = threading.Event()
            pinger_thread = threading.Thread(target=ping_job, args=(job_id, stop_event))
            pinger_thread.start()

            # Run subprocess
            current_proc = subprocess.Popen(cmd, preexec_fn=os.setsid, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            stdout, stderr = current_proc.communicate()

            # Stop heartbeat
            stop_event.set()
            pinger_thread.join()

            if current_proc.returncode == 0:
                logger.info(f"Job {job_id} completed successfully.")
                update_status(job_id, "DONE", f"{runner_id} finished successfully.")
            else:
                logger.error(f"Job {job_id} failed. Error:\n{stderr}")
                update_status(job_id, "ABORTED", f"Execution failed at {runner_id}: {stderr[:200]}")

            current_proc = None

        except Exception as e:
            logger.exception(f"Unexpected error occurred: {str(e)}")
            time.sleep(3)

        if machine_type == "htc":
            break

# --------------- Entry Point ----------------
if __name__ == "__main__":
    main()
