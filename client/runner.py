import requests
import subprocess
import os
import socket
import time
import logging
import argparse

# ---------------- Argument Parser ----------------
parser = argparse.ArgumentParser()
parser.add_argument("--api_url", type=str, default="http://127.0.0.1:5000", help="Base URL for the job server API")
parser.add_argument("--process_id", type=int, default=0, help="Give a process id for log tracking")
parser.add_argument("--expId", type=str, default="exp0", help="Give an exp id")
args = parser.parse_args()

# ---------------- Logger Setup ----------------
LOG_DIR = f"{args.expId}/logs"
os.makedirs(LOG_DIR, exist_ok=True)

runner_id = f"{os.getenv('USER') or os.getenv('USERNAME')}@{socket.gethostname()}"
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

# ---------------- Constants ----------------
REQUEST_JOB_URL = f"{args.api_url}/request_job"
UPDATE_JOB_URL = f"{args.api_url}/update_job_status"

# ---------------- Main Loop ----------------
def main():
    logger.info(f"🚀 Runner started as {runner_id}_{args.process_id}")
    logger.info(f"🌐 API URL: {args.api_url}")

    while True:
        try:
            logger.info("📡 Requesting a new job...")
            response = requests.post(REQUEST_JOB_URL, json={"requested_by": runner_id})

            if response.status_code == 404:
                logger.info("✅ No more jobs available. Runner exiting.")
                break

            if response.status_code != 200:
                logger.error(f"❌ Failed to request job. Status: {response.status_code}, Msg: {response.text}")
                time.sleep(2)
                continue

            job_info = response.json()
            job_id = job_info["job_id"]
            params = job_info["parameters"]

            logger.info(f"📦 Job {job_id} assigned with params: {params}")

            # Dynamically build the command
            cmd = ["python", "simple_run.py", "--job_id", str(job_id), "--expId", str(args.expId)]
            for key, value in params.items():
                cmd.extend([f"--{key}", str(value)])

            logger.info(f"▶️ Running command: {' '.join(cmd)}")
            result = subprocess.run(cmd, capture_output=True, text=True)

            if result.returncode == 0:
                logger.info(f"✅ Job {job_id} completed successfully.")
                update_status(job_id, "DONE", f"{runner_id} Job finished successfully.")
            else:
                logger.error(f"❌ Job {job_id} failed. Error:\n{result.stderr}")
                update_status(job_id, "ABORTED", f"Execution failed at {runner_id}: {result.stderr[:200]}")

        except Exception as e:
            logger.exception(f"💥 Unexpected error occurred: {str(e)}")
            time.sleep(3)

# ---------------- Job Status Update ----------------
def update_status(job_id, status, message):
    try:
        res = requests.post(UPDATE_JOB_URL, json={
            "job_id": job_id,
            "status": status,
            "message": message
        })
        if res.status_code == 200:
            logger.info(f"📤 Job {job_id} status updated to {status}.")
        else:
            logger.warning(f"⚠️ Failed to update status for job {job_id}: {res.text}")
    except Exception as e:
        logger.error(f"❌ Error while updating job status: {str(e)}")

# ---------------- Entry Point ----------------
if __name__ == "__main__":
    main()
