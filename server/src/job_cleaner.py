import pandas as pd
import time
import fcntl
import os
import logging
import json
import argparse

from math import floor

# ---------------- Constants ----------------
BASE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
CSV_FILE = ""
LOG_FILENAME = "job_cleaner.log"

STATUS_NOT_STARTED = "NOT_STARTED"
STATUS_SERVED = "SERVED"
STATUS_DONE = "DONE"
STATUS_ABORTED = "ABORTED"

ABORTED_JOB_RESET_TIMEOUT = 30 * 60
IDLE_TIMEOUT = 24 * 60 * 60
POLLING_INTERVAL = 10  # Default polling interval

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

# ---------------- Utilities ----------------

def get_message_as_json_list(message_str):
    try:
        existing_messages = json.loads(message_str)
        if not isinstance(existing_messages, list):
            existing_messages = []
    except json.JSONDecodeError:
        existing_messages = []
    return existing_messages

def load_jobs():
    try:
        with open(CSV_FILE, "r") as file:
            fcntl.flock(file, fcntl.LOCK_SH)
            jobs_df = pd.read_csv(file)
            fcntl.flock(file, fcntl.LOCK_UN)
        return jobs_df
    except Exception as e:
        logging.error(f"Error loading jobs: {str(e)}")
        return pd.DataFrame()

def save_jobs(jobs_df):
    try:
        with open(CSV_FILE, "w") as file:
            fcntl.flock(file, fcntl.LOCK_EX)
            jobs_df.to_csv(file, index=False)
            fcntl.flock(file, fcntl.LOCK_UN)
        logging.info("Successfully saved jobs to CSV.")
    except Exception as e:
        logging.error(f"Error saving jobs: {str(e)}")

# ---------------- Cleanup Logic ----------------

def reset_aborted_jobs(jobs_df, current_time):
    aborted_mask = jobs_df["status"] == STATUS_ABORTED
    if not aborted_mask.any():
        return False

    logging.info(f"Resetting {aborted_mask.sum()} ABORTED jobs to NOT_STARTED.")
    jobs_df.loc[aborted_mask, ["status", "requested_by", "request_timestamp", "completion_timestamp", "required_time", "last_ping_timestamp"]] = [
        STATUS_NOT_STARTED, "", 0, 0, 0, 0
    ]

    for index in jobs_df[aborted_mask].index:
        prev_requester = jobs_df.at[index, "requested_by"]
        messages = get_message_as_json_list(jobs_df.at[index, "message"])
        messages.append({
            "reason": f"Job Cleaner updated the job status to NOT STARTED due to previous failure at {prev_requester}!",
            "timestamp": current_time
        })
        jobs_df.at[index, "message"] = json.dumps(messages)

    return True

def reset_stale_served_jobs(jobs_df, current_time, idle_timeout):
    served_mask = (jobs_df["status"] == STATUS_SERVED) & (
        (current_time - jobs_df["last_ping_timestamp"]) > idle_timeout
    )
    if not served_mask.any():
        return False

    logging.info(f"Resetting {served_mask.sum()} SERVED jobs due to no ping.")

    for index in jobs_df[served_mask].index:
        prev_requester = jobs_df.at[index, "requested_by"]
        last_ping = jobs_df.at[index, "last_ping_timestamp"]
        minutes_silent = round((current_time - last_ping) / 60)

        messages = get_message_as_json_list(jobs_df.at[index, "message"])
        messages.append({
            "reason": f"Job Cleaner updated the job status to NOT STARTED because the server hasn't heard back from {prev_requester} for {minutes_silent} minutes!",
            "timestamp": current_time
        })
        jobs_df.at[index, "message"] = json.dumps(messages)

    jobs_df.loc[served_mask, ["status", "requested_by", "request_timestamp", "completion_timestamp", "required_time", "last_ping_timestamp"]] = [
        STATUS_NOT_STARTED, "", 0, 0, 0, 0
    ]

    return True

# ---------------- Main Cleanup Loop ----------------

def cleanup_loop():
    last_aborted_reset_time = 0
    last_idle_check_time = 0

    while True:
        now = time.time()
        jobs_df = load_jobs()
        if jobs_df.empty:
            logging.info("No jobs to clean up.")
        else:
            jobs_updated = False

            if now - last_aborted_reset_time >= ABORTED_JOB_RESET_TIMEOUT:
                logging.info("Running aborted job cleanup...")
                if reset_aborted_jobs(jobs_df, now):
                    jobs_updated = True
                last_aborted_reset_time = now

            if now - last_idle_check_time >= IDLE_TIMEOUT:
                logging.info("Running stale SERVED job timeout...")
                if reset_stale_served_jobs(jobs_df, now, IDLE_TIMEOUT):
                    jobs_updated = True
                last_idle_check_time = now

            if jobs_updated:
                save_jobs(jobs_df)
            else:
                logging.info("No updates made in this cycle.")

        time.sleep(POLLING_INTERVAL)

# ---------------- Entry Point ----------------

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Start job_cleaner background service")
    parser.add_argument("--jobDB", default="jobs.csv", help="CSV file (<filename>.csv) placed in the same directory as server.py")
    parser.add_argument("--expId", type=str, default="sim1", help="Give a unique name of your experiment")
    parser.add_argument("--abortedJobResetTimeout", type=int, default=1800, help="How often to reset aborted jobs (in seconds)")
    parser.add_argument("--idleTimeout", type=int, default=60, help="Max silence period for SERVED jobs (in seconds)")
    parser.add_argument("--pollingInterval", type=int, default=60, help="How often to poll for cleanup (in seconds)")
    args = parser.parse_args()

    createExpBaseDirectory(args)
    setup_log(args)

    CSV_FILE = os.path.join(BASE_DIR, args.expId, args.jobDB)
    ABORTED_JOB_RESET_TIMEOUT = args.abortedJobResetTimeout
    IDLE_TIMEOUT = args.idleTimeout
    POLLING_INTERVAL = args.pollingInterval

    logging.info("Job cleaner started.")
    cleanup_loop()
