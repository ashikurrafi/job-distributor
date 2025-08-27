import time
import logging
import os
from flask import Flask, jsonify, request
from datetime import datetime
import json
import argparse
from pyngrok import ngrok
from database import JobDatabase

app = Flask(__name__)

BASE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
DB_FILE = ""
LOG_FILENAME = "server.log"

def createExpBaseDirectory(args):
    os.makedirs(os.path.join(BASE_DIR, args.expId), exist_ok=True)

def setup_log(args):
    LOG_FILE = os.path.join(BASE_DIR, args.expId, LOG_FILENAME)
    logging.basicConfig(
        filename=LOG_FILE,
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
    )



# Initialize database connection
db = None

STATUS_PENDING = "PENDING"
STATUS_SERVED = "SERVED"
STATUS_DONE = "DONE"
STATUS_ABORTED = "ABORTED"

def format_timestamp(timestamp):
    if timestamp < 0:
        return "N/A"
    """Convert timestamp to human-readable format."""
    return datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S') if timestamp else "N/A"

@app.route("/request_job", methods=["POST"])
def request_job():
    """Assign a PENDING job to a requester and mark it as SERVED."""
    # Track API request
    db.track_api_request("Job Request", "POST")
    
    data = request.json or {}
    requested_by = data.get("requested_by")

    if not requested_by:
        logging.warning("Job request failed: No requester identification provided.")
        return jsonify({"error": "Requester identification is required"}), 400

    job = db.request_job(requested_by)
    if not job:
        logging.info("No PENDING jobs available.")
        return jsonify({"error": "No available jobs"}), 404

    logging.info(f"Job {job['id']} assigned to {requested_by} and marked as SERVED.")
    return jsonify({"job_id": job['id'], "parameters": job['parameters'], "status": STATUS_SERVED}), 200


@app.route("/update_job_status", methods=["POST"])
def update_job_status():
    """Update job status as DONE or ABORTED."""
    # Track API request
    db.track_api_request("Job Status Update", "POST")
    
    data = request.json or {}
    job_id = data.get("job_id")
    status = data.get("status")
    message = data.get("message", "")

    if not isinstance(job_id, int) or status not in [STATUS_DONE, STATUS_ABORTED]:
        logging.warning(f"Invalid job status update request: job_id={job_id}, status={status}")
        return jsonify({"error": "Invalid job_id or status"}), 400

    success = db.update_job_status(job_id, status, message)
    if not success:
        return jsonify({"error": "Job not found or not in SERVED status"}), 404

    if status == STATUS_DONE:
        logging.info(f"Job {job_id} marked as DONE.")
    else:
        logging.info(f"Job {job_id} ABORTED. Reason: {message or 'No reason provided'}.")

    return jsonify({"message": f"Job {job_id} updated to {status}", "job_id": job_id}), 200

@app.route("/ping", methods=["POST"])
def ping_job():
    """Update last_ping_timestamp for a SERVED job."""
    # Track API request
    db.track_api_request("Job Ping", "POST")
    
    data = request.json or {}
    job_id = data.get("id")

    if not isinstance(job_id, int):
        logging.warning(f"Invalid ping request: job_id={job_id}")
        return jsonify({"error": "Invalid job_id"}), 400

    success = db.ping_job(job_id)
    if not success:
        return jsonify({"error": "Job not found or not in SERVED state"}), 404

    now = round(time.time())
    logging.info(f"Ping received for job {job_id}. Updated last_ping_timestamp.")
    return jsonify({"message": f"Ping received for job {job_id}", "timestamp": now}), 200


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Start the Flask server")
    parser.add_argument("--host", default="0.0.0.0", help="IP address to bind to")
    parser.add_argument("--jobDB", default="jobs.db", help="SQLite database file (<filename>.db) placed in the same directory as server.py")
    parser.add_argument("--enableNgrok", default=False, help="Enable ngrok for external access")
    parser.add_argument("--port", type=int, default=5000, help="Port number to listen on")
    parser.add_argument("--expId", type=str, default="sim1", help="Give an unique name")
    args = parser.parse_args()
    createExpBaseDirectory(args)
    setup_log(args)
    logging.info(f"Starting Flask server on {args.host}:{args.port}...")
    DB_FILE = os.path.join(BASE_DIR, args.expId, args.jobDB)
    
    # Initialize database connection
    db = JobDatabase(DB_FILE)
    
    if args.enableNgrok == True:
        logging.info("Starting ngrok tunnel...")
        public_url = ngrok.connect(args.port)
        print(f" >> job_server : {public_url}")
        logging.info(f"ngrok tunnel established at {public_url}")
    app.run(host=args.host, port=args.port)  


# python server.py --expId=sim1 --jobDB=jobs.db --host=0.0.0.0 --port=5000