import time
import os
import logging
import argparse
from database import JobDatabase

# ---------------- Constants ----------------
BASE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
DB_FILE = ""
LOG_FILENAME = "job_cleaner.log"

STATUS_PENDING = "PENDING"
STATUS_SERVED = "SERVED"
STATUS_DONE = "DONE"
STATUS_ABORTED = "ABORTED"

ABORTED_JOB_RESET_TIMEOUT = 30 * 60 # ideal time out for aborted jobs
IDLE_TIMEOUT = 60
POLLING_INTERVAL = 60  # Default polling interval

# ---------------- Setup ----------------

def createExpBaseDirectory(args):
    os.makedirs(os.path.join(BASE_DIR, args.expId), exist_ok=True)

def setup_log(args):
    LOG_FILE = os.path.join(BASE_DIR, args.expId, LOG_FILENAME)
    logging.basicConfig(
        filename=LOG_FILE,
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
    )

# ---------------- Cleanup Logic ----------------
# Database operations are now handled by the JobDatabase class

# ---------------- Main Cleanup Loop ----------------

def cleanup_loop(db):
    last_aborted_reset_time = 0
    last_idle_check_time = 0

    while True:
        now = time.time()
        jobs_updated = False

        if now - last_aborted_reset_time >= ABORTED_JOB_RESET_TIMEOUT:
            logging.info("Running aborted job cleanup...")
            count = db.reset_aborted_jobs()
            if count > 0:
                logging.info(f"Reset {count} ABORTED jobs to PENDING.")
                jobs_updated = True
            last_aborted_reset_time = now

        if now - last_idle_check_time >= IDLE_TIMEOUT:
            logging.info("Running stale SERVED job timeout...")
            count = db.reset_stale_served_jobs(IDLE_TIMEOUT)
            if count > 0:
                logging.info(f"Reset {count} SERVED jobs due to no ping.")
                jobs_updated = True
            last_idle_check_time = now

        if not jobs_updated:
            logging.info("No updates made in this cycle.")

        time.sleep(POLLING_INTERVAL)

# ---------------- Entry Point ----------------

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Start job_cleaner background service")
    parser.add_argument("--jobDB", default="jobs.db", help="SQLite database file (<filename>.db) placed in the same directory as server.py")
    parser.add_argument("--expId", type=str, default="sim1", help="Give a unique name of your experiment")
    parser.add_argument("--abortedJobResetTimeout", type=int, default=1800, help="How often to reset aborted jobs (in seconds)")
    parser.add_argument("--idleTimeout", type=int, default=60, help="Max silence period for SERVED jobs (in seconds)")
    parser.add_argument("--pollingInterval", type=int, default=60, help="How often to poll for cleanup (in seconds)")
    args = parser.parse_args()

    createExpBaseDirectory(args)
    setup_log(args)

    DB_FILE = os.path.join(BASE_DIR, args.expId, args.jobDB)
    ABORTED_JOB_RESET_TIMEOUT = args.abortedJobResetTimeout
    IDLE_TIMEOUT = args.idleTimeout
    POLLING_INTERVAL = args.pollingInterval

    # Initialize database connection
    db = JobDatabase(DB_FILE)

    logging.info("Job cleaner started.")
    cleanup_loop(db)
