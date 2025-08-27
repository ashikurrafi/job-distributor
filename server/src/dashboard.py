import logging
import os
import json
from datetime import datetime
from flask import Flask, render_template_string, jsonify, request
from collections import defaultdict
from datetime import timedelta
import pytz
import argparse
from pyngrok import ngrok
from database import JobDatabase

app = Flask(__name__)

# -------------------------- CONFIG --------------------------
BASE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
DB_FILE = ""
LOG_FILENAME = "dashboard.log"
EXP_ID = "sim100"
def createExpBaseDirectory(args):
    os.makedirs(os.path.join(BASE_DIR, args.expId), exist_ok=True)

def setup_log(args):
    LOG_FILE = os.path.join(BASE_DIR, args.expId, LOG_FILENAME)
    logging.basicConfig(
        filename=LOG_FILE,
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
    )

STATUS_PENDING = "PENDING"
STATUS_SERVED = "SERVED"
STATUS_DONE = "DONE"
STATUS_ABORTED = "ABORTED"

# Initialize database connection
db = None

# Load configuration
def load_config():
    """Load configuration from config.json"""
    config_path = os.path.join(BASE_DIR, "config.json")
    try:
        with open(config_path, 'r') as f:
            return json.load(f)
    except Exception as e:
        logging.error(f"Error loading config: {e}")
        return {"status_change_pin": "1234"}  # Default fallback

config = load_config()

# --------------------- HELPER FUNCTIONS -----------------------
def load_jobs():
    """Load jobs from the SQLite database."""
    try:
        jobs = db.get_all_jobs()
        
        # Add machine field for compatibility
        for job in jobs:
            if not job["requested_by"] or job["requested_by"].strip() == "":
                job["machine"] = "Unassigned"
            else:
                job["machine"] = job["requested_by"].split("_")[0]
        
        return jobs
    except Exception as e:
        logging.error(f"Error loading jobs from database: {e}")
        return []

def format_timestamp(timestamp):
    """Convert a Unix timestamp to human-readable format using client's local timezone."""
    if timestamp < 0 or not timestamp:
        return "N/A"
    # Return the raw timestamp for client-side formatting
    return timestamp

def format_time(seconds):
    """Convert minutes to hh:mm:ss format."""
    return str(timedelta(seconds=round(seconds)))

def calculate_machine_stats(jobs):
    """Calculate statistics for each machine group."""
    machine_stats = defaultdict(lambda: {"count": 0, "total_time": 0, "instances": set()})
    total_completed = len([job for job in jobs if job["status"] == STATUS_DONE])
    
    for job in jobs:
        if job["status"] == STATUS_DONE:
            machine_name = job["requested_by"].split("_")[0]  # Extract machine prefix
            machine_stats[machine_name]["count"] += 1
            machine_stats[machine_name]["total_time"] += job["required_time"]
            machine_stats[machine_name]["instances"].add(job["requested_by"])
    
    for machine, data in machine_stats.items():
        data["average_time"] = format_time((data["total_time"] / data["count"]) if data["count"] else 0)
        data["percentage"] = (data["count"] / total_completed * 100) if total_completed else 0
        data["percentage"] = round(data["percentage"], 2)
        data["instance_count"] = len(data["instances"])
    
    return machine_stats

# ------------------------- JOB STATISTICS --------------------- 
@app.route("/job_stats", methods=["GET"])
def job_stats():
    # Track API request
    db.track_api_request("Job Statistics", "GET")
    
    jobs = load_jobs()
    interval = request.args.get("interval", "hourly")
    machine = request.args.get("machine", "all")
    # Use UTC for server-side calculations, let client handle timezone conversion
    now = datetime.now(pytz.utc).timestamp()
    job_counts = defaultdict(int)
    total_jobs_completed = 0

    filtered_jobs = [job for job in jobs if job["status"] == STATUS_DONE and (machine == "all" or job["machine"] == machine)]
    
    if interval == "minutely":
        start_time = now - 1800
        # Return timestamps for client-side formatting
        x_labels = [start_time + i * 60 for i in range(30)]
        for job in filtered_jobs:
            if job["completion_timestamp"] >= start_time:
                minute = int((job["completion_timestamp"] - start_time) // 60)
                job_counts[minute] += 1
                total_jobs_completed += 1
    elif interval == "hourly":
        start_time = now - 86400
        # Return timestamps for client-side formatting
        x_labels = [start_time + i * 3600 for i in range(24)]
        for job in filtered_jobs:
            if job["completion_timestamp"] >= start_time:
                hour = int((job["completion_timestamp"] - start_time) // 3600)
                job_counts[hour] += 1
                total_jobs_completed += 1
    else:
        first_day = min(job["completion_timestamp"] for job in filtered_jobs)
        days_elapsed = int((now - first_day) // 86400 + 1)
        # Return timestamps for client-side formatting
        x_labels = [first_day + i * 86400 for i in range(days_elapsed)]
        for job in filtered_jobs:
            day = int((job["completion_timestamp"] - first_day) // 86400)
            job_counts[day] += 1
            total_jobs_completed += 1

    y_values = [job_counts[i] for i in range(len(x_labels))]
    return jsonify({"labels": x_labels, "values": y_values, "total_jobs": total_jobs_completed, "timestamps": True})

@app.route("/api_stats", methods=["GET"])
def api_stats():
    """Return API statistics in JSON format."""
    # Track API request
    db.track_api_request("API Statistics", "GET")
    
    stats = db.get_api_stats()
    return jsonify({"api_stats": stats})

@app.route("/database_info", methods=["GET"])
def get_database_info():
    """Get database information including indexes and table sizes."""
    # Track API request
    db.track_api_request("Database Info", "GET")
    
    info = db.get_database_info()
    return jsonify(info)

@app.route("/change_job_status", methods=["POST"])
def change_job_status():
    """Change job status for DONE, ABORTED, or PENDING jobs."""
    # Track API request
    db.track_api_request("Change Job Status", "POST")
    
    try:
        data = request.get_json()
        job_id = data.get('job_id')
        new_status = data.get('new_status')
        reason = data.get('reason', '')
        pin = data.get('pin', '')
        
        if job_id is None or new_status is None:
            return jsonify({"success": False, "error": "Missing job_id or new_status"}), 400
        
        # Validate PIN
        config_pin = config.get('status_change_pin', '1234')  # Default fallback
        if pin != config_pin:
            return jsonify({"success": False, "error": "Invalid PIN"}), 401
        
        success = db.change_job_status(job_id, new_status, reason)
        
        if success:
            return jsonify({"success": True, "message": f"Job {job_id} status changed to {new_status}"})
        else:
            return jsonify({"success": False, "error": "Failed to change job status"}), 400
            
    except Exception as e:
        logging.error(f"Error changing job status: {e}")
        return jsonify({"success": False, "error": str(e)}), 500




# ------------------------ DASHBOARD ROUTE ---------------------
@app.route("/", methods=["GET"])
def dashboard():
    """Display job statistics and job details in an HTML page with column-based sorting icons."""
    # Track API request
    db.track_api_request("Dashboard", "GET")
    
    expId = EXP_ID
    jobs = load_jobs()
    total_jobs = len(jobs)
    machine_names = sorted(set(job["machine"] for job in jobs))
    total_jobs_served = sum(1 for job in jobs if job["status"] == STATUS_SERVED)
    total_jobs_completed = sum(1 for job in jobs if job["status"] == STATUS_DONE)
    total_jobs_aborted = sum(1 for job in jobs if job["status"] == STATUS_ABORTED)

    machine_stats = calculate_machine_stats(jobs)
    api_stats = db.get_api_stats()
    
    # Calculate total API requests
    total_api_requests = sum(stat['request_count'] for stat in api_stats)
        
    
    
    
    
    avg_completion_time = ""
    if total_jobs_completed > 0:
        total_time = sum(j["required_time"] for j in jobs if j["status"] == STATUS_DONE)
        avg_completion_time = format_time(total_time / total_jobs_completed)

    # ---------------------- HTML TEMPLATE ----------------------
    html_template = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Job Dashboard</title>
        <script src="https://code.jquery.com/jquery-3.7.1.min.js"></script>
        <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css">
        <link rel="stylesheet" href="https://cdn.datatables.net/2.3.1/css/dataTables.dataTables.min.css">
        <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
        <script src="https://cdn.datatables.net/2.3.1/js/dataTables.min.js"></script>
        <style>
            * {
                box-sizing: border-box;
            }
            
            body { 
                font-family: Arial, sans-serif;
                margin: 0;
                padding: 0;
                background: #f8f9fa;
                min-height: 100vh;
            }
            
            .container {
                max-width: 1920px;
                width: 100%;
                height: 100vh;
                margin: 0 auto;
                background: white;
                display: flex;
                flex-direction: column;
                overflow: hidden;
            }
            
            .header {
                background: #f2f2f2;
                color: #333;
                padding: 20px 30px;
                text-align: center;
                flex-shrink: 0;
                border-bottom: 1px solid #ddd;
            }
            
            .header h1 {
                margin: 0;
                font-size: 2.2rem;
                font-weight: bold;
            }
            
            .header h1 i {
                margin-right: 10px;
                font-size: 2rem;
            }
            

            
            .main-content {
                flex: 1;
                display: flex;
                overflow: hidden;
            }
            
            .dashboard-grid {
                display: flex;
                width: 100%;
                height: 100%;
                gap: 0;
            }
            
            .sidebar {
                width: 408px;
                background: white;
                border-right: 1px solid #ddd;
                padding: 20px;
                overflow-y: auto;
                flex-shrink: 0;
                display: flex;
                flex-direction: column;
                gap: 20px;
                direction: rtl;
            }
            
            .sidebar > * {
                direction: ltr;
            }
            }
            
            .stats-card {
                background: white;
                border-radius: 12px;
                padding: 20px 25px;
                box-shadow: 0px 1px 15px 8px rgba(0, 0, 0, 0.08);
                border: none;
            }
            
            .stats-card h3 {
                margin: 0 0 20px 0;
                font-size: 1.4rem;
                font-weight: bold;
                color: #333;
                border-bottom: 2px solid #f0f0f0;
                padding-bottom: 10px;
            }
            
            .experiment-info {
                background: #f9f9f9;
                padding: 15px;
                border-radius: 8px;
                margin-bottom: 20px;
                border-left: 4px solid #2196F3;
            }
            
            .experiment-info p {
                margin: 10px 0;
                font-size: 16px;
                color: #555;
            }
            
            .experiment-info strong {
                color: #333;
                font-weight: bold;
            }
            
            .stats-grid {
                display: grid;
                grid-template-columns: 1fr 1fr;
                gap: 15px;
                margin: 20px 0;
            }
            
            .stat-item {
                text-align: center;
                padding: 15px 10px;
                background: white;
                border-radius: 8px;
                border: 1px solid #e0e0e0;
                box-shadow: 0 2px 4px rgba(0,0,0,0.05);
                transition: transform 0.2s ease;
            }
            
            .stat-item:hover {
                transform: translateY(-2px);
                box-shadow: 0 4px 8px rgba(0,0,0,0.1);
            }
            
            .stat-icon {
                font-size: 1.8rem;
                margin-bottom: 10px;
                display: block;
            }
            
            .stat-label {
                font-size: 14px;
                color: #666;
                margin-bottom: 8px;
                font-weight: 500;
            }
            
            .stat-value {
                font-weight: bold;
                color: #333;
                font-size: 1.5rem;
            }
            
            .chart-container {
                flex: 1;
                background: white;
                padding: 20px;
                display: flex;
                flex-direction: column;
                overflow: hidden;
            }
            
            .chart-wrapper {
                flex: 1;
                position: relative;
                min-height: 0;
            }
            
            #jobChart {
                width: 100% !important;
                height: 100% !important;
            }
            
            .tabs {
                display: flex;
                gap: 10px;
                margin: 20px 0;
                padding: 0;
                justify-content: center;
                flex-shrink: 0;
            }
            
            .tab-button {
                background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%);
                color: #495057;
                border: 2px solid #dee2e6;
                padding: 10px 18px;
                cursor: pointer;
                font-size: 14px;
                font-weight: 600;
                border-radius: 8px;
                transition: all 0.3s ease;
                position: relative;
                min-width: 120px;
                display: flex;
                align-items: center;
                justify-content: center;
                gap: 6px;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                flex: 1;
                max-width: 150px;
            }
            
            .tab-button:hover {
                background: linear-gradient(135deg, #e9ecef 0%, #dee2e6 100%);
                transform: translateY(-2px);
                box-shadow: 0 4px 8px rgba(0,0,0,0.15);
            }
            
            .tab-button.active {
                background: linear-gradient(135deg, #2c3e50 0%, #34495e 100%);
                color: white;
                border-color: #2c3e50;
                transform: translateY(-2px);
                box-shadow: 0 6px 12px rgba(44,62,80,0.3);
            }
            
            .tab-button.active::before {
                content: '';
                position: absolute;
                bottom: -8px;
                left: 50%;
                transform: translateX(-50%);
                width: 0;
                height: 0;
                border-left: 8px solid transparent;
                border-right: 8px solid transparent;
                border-top: 8px solid #2c3e50;
            }
            
            .tab-button i {
                font-size: 16px;
            }
            
            .tab-button .tab-count {
                background: rgba(255,255,255,0.2);
                color: inherit;
                padding: 1px 6px;
                border-radius: 8px;
                font-size: 11px;
                font-weight: bold;
                margin-left: 4px;
            }
            
            .tab-button.active .tab-count {
                background: rgba(255,255,255,0.3);
            }
            
            /* Notification System */
            .notification {
                position: fixed;
                top: 20px;
                right: 20px;
                z-index: 10000;
                max-width: 400px;
                border-radius: 8px;
                box-shadow: 0 4px 12px rgba(0,0,0,0.15);
                animation: slideInRight 0.3s ease-out;
                font-family: Arial, sans-serif;
            }
            
            @keyframes slideInRight {
                from {
                    transform: translateX(100%);
                    opacity: 0;
                }
                to {
                    transform: translateX(0);
                    opacity: 1;
                }
            }
            
            .notification-content {
                display: flex;
                align-items: center;
                justify-content: space-between;
                padding: 16px 20px;
                border-radius: 8px;
            }
            
            .notification-message {
                flex: 1;
                margin-right: 12px;
                font-size: 14px;
                font-weight: 500;
            }
            
            .notification-close {
                background: none;
                border: none;
                font-size: 18px;
                cursor: pointer;
                padding: 0;
                width: 20px;
                height: 20px;
                display: flex;
                align-items: center;
                justify-content: center;
                border-radius: 50%;
                transition: background-color 0.2s;
            }
            
            .notification-close:hover {
                background-color: rgba(0,0,0,0.1);
            }
            
            .notification-success {
                background: linear-gradient(135deg, #d4edda 0%, #c3e6cb 100%);
                border: 1px solid #c3e6cb;
                color: #155724;
            }
            
            .notification-error {
                background: linear-gradient(135deg, #f8d7da 0%, #f5c6cb 100%);
                border: 1px solid #f5c6cb;
                color: #721c24;
            }
            
            .notification-warning {
                background: linear-gradient(135deg, #fff3cd 0%, #ffeaa7 100%);
                border: 1px solid #ffeaa7;
                color: #856404;
            }
            
            .notification-info {
                background: linear-gradient(135deg, #d1ecf1 0%, #bee5eb 100%);
                border: 1px solid #bee5eb;
                color: #0c5460;
            }
            
            .tabcontent {
                display: none;
                padding: 20px 0;
            }
            
            .tabcontent.active {
                display: block;
            }
            
            .form-group {
                margin: 16px 0;
            }
            
            .form-label {
                display: block;
                margin-bottom: 8px;
                font-size: 16px;
                font-weight: 500;
                color: #374151;
            }
            
            .form-select {
                width: 100%;
                padding: 12px 16px;
                border: 1px solid #d1d5db;
                border-radius: 8px;
                background: white;
                font-size: 16px;
                color: #374151;
                cursor: pointer;
                transition: border-color 0.2s ease;
            }
            
            .form-select:focus {
                outline: none;
                border-color: #667eea;
                box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
            }
            
            .btn {
                background-color: #f2f2f2;
                color: #000;
                border: none;
                padding: 16px 20px;
                border-radius: 6px;
                font-weight: normal;
                cursor: pointer;
                width: 100%;
                margin-bottom: 12px;
                box-shadow: none;
                font-size: 16px;
                min-height: 50px;
            }
            
            .btn:hover {
                background-color: #e6e6e6;
            }
            
            .api-stats {
                max-height: 300px;
                overflow-y: auto;
            }
            
            .api-stat-item {
                display: flex;
                justify-content: space-between;
                align-items: center;
                padding: 12px 0;
                border-bottom: 1px solid #f1f5f9;
            }
            
            .api-stat-item:last-child {
                border-bottom: none;
            }
            
            .api-endpoint {
                font-weight: 500;
                color: #1e293b;
                font-size: 0.875rem;
            }
            
            .api-method {
                font-size: 0.75rem;
                color: #64748b;
                margin-top: 2px;
            }
            
            .api-count {
                background: #3498db;
                color: white;
                padding: 4px 8px;
                border-radius: 4px;
                font-size: 0.75rem;
                font-weight: 500;
            }
            
            .tabcontent {
                flex: 1;
                overflow-y: auto;
                padding: 0;
            }
            
            .table-wrapper {
                height: 100%;
                overflow: auto;
                background: white;
                border-radius: 8px;
                border: 1px solid #dee2e6;
                position: relative;
            }
            
            .table-watermark {
                position: absolute;
                top: 50%;
                left: 50%;
                transform: translate(-50%, -50%);
                text-align: center;
                z-index: 10;
                pointer-events: none;
                opacity: 0.4;
            }
            
            .table-watermark i {
                font-size: 4rem;
                color: #ccc;
                margin-bottom: 10px;
                display: block;
            }
            
            .table-watermark .watermark-text {
                font-size: 1.2rem;
                color: #999;
                font-weight: 500;
            }
            
            .status-badge {
                display: inline-block;
                padding: 4px 8px;
                border-radius: 12px;
                font-size: 0.75rem;
                font-weight: 600;
                text-transform: uppercase;
                letter-spacing: 0.5px;
            }
            
            .status-not-started {
                background-color: #f8f9fa;
                color: #6c757d;
                border: 1px solid #dee2e6;
            }
            
            .status-served {
                background-color: #fff3cd;
                color: #856404;
                border: 1px solid #ffeaa7;
            }
            
            .status-done {
                background-color: #d4edda;
                color: #155724;
                border: 1px solid #c3e6cb;
            }
            
            .status-aborted {
                background-color: #f8d7da;
                color: #721c24;
                border: 1px solid #f5c6cb;
            }
            
            .myTable {
                width: 100%;
                border-collapse: collapse;
                table-layout: fixed;
                margin: 0;
                font-size: 0.875rem;
            }
            
            .myTable th {
                background: #f2f2f2;
                color: #333;
                font-weight: bold;
                padding: 8px;
                text-align: left;
                border-bottom: 1px solid #ddd;
                border-right: 1px solid #ddd;
                position: sticky;
                top: 0;
                z-index: 10;
            }
            
            .myTable th:last-child {
                border-right: none;
            }
            
            .myTable td {
                padding: 8px;
                border-bottom: 1px solid #f2f2f2;
                border-right: 1px solid #f2f2f2;
                vertical-align: top;
                word-wrap: break-word;
                overflow-wrap: break-word;
            }
            
            .myTable td:last-child {
                border-right: none;
            }
            
            .myTable tr:hover {
                background-color: #f5f5f5;
            }
            
            .myTable tr:nth-child(even) {
                background-color: #f9f9f9;
            }
            
            .myTable tr:nth-child(even):hover {
                background-color: #f5f5f5;
            }
            
            /* Fixed column widths */
            .myTable th:nth-child(1), .myTable td:nth-child(1) { width: 80px; } /* ID */
            .myTable th:nth-child(2), .myTable td:nth-child(2) { width: 140px; } /* Machine */
            .myTable th:nth-child(3), .myTable td:nth-child(3) { width: 160px; } /* Requested At */
            .myTable th:nth-child(4), .myTable td:nth-child(4) { width: 160px; } /* Started At */
            .myTable th:nth-child(5), .myTable td:nth-child(5) { width: 160px; } /* Completed At */
            .myTable th:nth-child(6), .myTable td:nth-child(6) { width: 120px; } /* Duration */
            .myTable th:nth-child(7), .myTable td:nth-child(7) { width: 140px; } /* Job History */
            
            .myTable td.clickable {
                cursor: pointer;
                color: #3498db;
            }
            
            .myTable td.clickable:hover {
                background-color: #e3f2fd;
                color: #2980b9;
            }
            
            .view-details-btn {
                background-color: #f2f2f2;
                color: #000;
                padding: 8px 10px;
                border: none;
                border-radius: 6px;
                cursor: pointer;
                font-size: 14px;
                font-weight: normal;
                box-shadow: none;
            }
            
            .view-details-btn:hover {
                background-color: #e6e6e6;
            }
            
            .sort-icon {
                cursor: pointer;
                margin-left: 0.3em;
                font-size: 0.9em;
                color: #333;
                font-weight: bold;
            }

            /* Modal Styling */
            .modal {
                display: none;
                position: fixed;
                z-index: 1000;
                left: 0;
                top: 0;
                width: 100%;
                height: 100%;
                background-color: rgba(0, 0, 0, 0.4);
            }
            .modal-content {
                background-color: white;
                margin: 5% auto;
                padding: 20px;
                border: 1px solid #888;
                width: 50%;
                text-align: left;
                border-radius: 10px;
                box-shadow: 0px 4px 8px rgba(0, 0, 0, 0.2);
                font-family: Arial, sans-serif;
                overflow-y: auto;
                max-height: calc(100% - 20%);
            }
            .close {
                float: right;
                font-size: 28px;
                font-weight: bold;
                cursor: pointer;
            }

            /* Timeline Styling */
            .timeline {
                position: relative;
            }
            .timeline-item {
                position: relative;
                padding: 10px 0;
                border:1px solid #007bff;
                border-left:3px solid #007bff;
                padding-left:20px;
                margin-bottom:5px;
                border-radius:6px;
            }
            .timeline-item::before {
                content: "●";
                color: #007bff;
                position: absolute;
                left: 6px;
                top: 10px;
                font-size: 14px;
            }
            .timestamp {
                color: #666;
                font-size: 12px;
                font-style: italic;
            }
            .message {
                font-size: 16px;
                font-weight: bold;
            }
            .stats-box {
                background-color: white;
                border-radius: 12px;
                padding: 20px 25px;
                box-shadow: 0px 1px 15px 8px rgba(0, 0, 0, 0.08);
                display: flex;
                flex-direction: column;
                gap: 6px;
                font-family: Arial, sans-serif;
                width: 280px;
            }
            .stats-box p {
                margin: 5px 0;
                font-size: 14px;
                color: #333;
            }
            .stats-box select {
                width: 100%;
                padding: 5px;
                border-radius: 5px;
                border: 1px solid #ccc;
                margin-top: 0px;
            }
            
            .hidden {
                display: none;
            }

            #parametersTable table {
                width: 100%;
                border-collapse: collapse;
                margin-top: 10px;
            }

            #parametersTable th, #parametersTable td {
                border: 1px solid #ccc;
                padding: 8px;
                text-align: left;
            }

            #parametersTable th {
                background-color: #f5f5f5;
            }
                padding: 8px;
                text-align: left;
            }

            #parametersTable th {
                background-color: #f5f5f5;
            }


        </style>
        <style>
            body { font-family: Arial, sans-serif; }
            .modal-2 {
                display: none;
                position: fixed;
                z-index: 1000;
                left: 0;
                top: 0;
                width: 100%;
                height: 100%;
                background-color: rgba(0, 0, 0, 0.4);
            }
            .modal-content-2 {
                background-color: white;
                margin: 5% auto;
                overflow-y: auto;
                max-height: calc(100% - 20%);
                padding: 20px;
                border-radius: 10px;
                width: 60%;
                text-align: center;
                box-shadow: 0px 4px 8px rgba(0, 0, 0, 0.2);
            }
            table.stats-table td:first-child, table.stats-table th:first-child {
                position: sticky;
                left: 0;
            }
            .close {
                float: right;
                font-size: 28px;
                font-weight: bold;
                cursor: pointer;
            }
            .stats-table {
                width: 100%;
                border-collapse: collapse;
                font-size: 16px;
            }
            .stats-table th, .stats-table td {
                padding: 10px;
                text-align: center;
            }
            .stats-table th {
                background-color: #f2f2f2;
                color: black;
                font-weight: bold;
            }
            .modal-button {
                padding: 12px 24px;
                font-size: 16px;
                cursor: pointer;
                background-color: #f2f2f2;
                color: black;
                border: none;
                border-radius: 5px;
                width: 260px;
            }
            #chart-container {
                height: 420px;
                flex: auto;
                justify-content: center;
                align-items: center;
                background-color: white;
                border-radius: 12px;
                padding: 15px;
                box-shadow: 0px 1px 15px 8px rgba(0, 0, 0, 0.08);
            }
            canvas {
                max-width: 100%;
                max-height: 100%;
            }

            .total-jobs-box {
                position: relative;
                bottom: 10px;
                left: 10px;
                background-color: white;
                border-radius: 6px;
                padding: 8px 12px;
                font-size: 14px;
                font-weight: bold;
                color: #333;
                box-shadow: 2px 2px 5px rgba(0, 0, 0, 0.1);
                display: inline-block;
            }
            
            
            
            #jobChart {
                max-width: 100%;
                max-height: 100%;
                width: auto !important;
                height: auto !important;
            }

            /* Progress Bar Styles */
            .progress-container {
                position: relative;
                margin: 20px 0;
                padding: 15px;
                background: #f9f9f9;
                border-radius: 8px;
                border: 1px solid #e0e0e0;
            }
            
            .progress-container h4 {
                margin: 0 0 12px 0;
                font-size: 16px;
                color: #333;
                font-weight: bold;
            }
            
            .progress-bar {
                background-color: #e0e0e0;
                border-radius: 10px;
                overflow: hidden;
                height: 20px;
                box-shadow: inset 0 2px 4px rgba(0,0,0,0.1);
            }
            
            .progress-fill {
                height: 100%;
                border-radius: 10px;
                transition: width 0.3s ease;
                background: linear-gradient(90deg, #4CAF50 0%, #45a049 100%);
                position: relative;
                overflow: hidden;
            }
            
            .progress-fill::after {
                content: '';
                position: absolute;
                top: 0;
                left: 0;
                right: 0;
                bottom: 0;
                background: linear-gradient(90deg, 
                    transparent 0%, 
                    rgba(255,255,255,0.3) 50%, 
                    transparent 100%);
                animation: shine 2s infinite;
            }
            
            @keyframes shine {
                0% { transform: translateX(-100%); }
                100% { transform: translateX(100%); }
            }
            
            .progress-text {
                display: flex;
                justify-content: space-between;
                font-size: 14px;
                margin-top: 10px;
                color: #555;
            }

        </style>
        <script>
            function openModal() {
                document.getElementById("statsModal").style.display = "block";
            }
            function closeModal() {
                document.getElementById("statsModal").style.display = "none";
            }
        </script>
        <script>
            function openTab(tabName) {
                var i, tabcontent, tablinks;
                tabcontent = document.getElementsByClassName("tabcontent");
                for (i = 0; i < tabcontent.length; i++) {
                    tabcontent[i].classList.remove("active");
                }
                tablinks = document.getElementsByClassName("tab-button");
                for (i = 0; i < tablinks.length; i++) {
                    tablinks[i].classList.remove("active");
                }
                document.getElementById(tabName).classList.add("active");
                event.currentTarget.classList.add("active");
            }

            function showMessageModal(jobId, message, parameters, currentStatus) {
                const modal = document.getElementById("messageModal");
                const jobIdSpan = document.getElementById("jobId");
                const messageTimeline = document.getElementById("messageTimeline");
                const parametersTable = document.getElementById("parametersTable");
                const toggleBtn = document.getElementById("toggleParamsBtn");
                const statusChangeSection = document.getElementById("statusChangeSection");
                const statusChangeTitle = document.getElementById("statusChangeTitle");

                // Set Job ID
                jobIdSpan.textContent = jobId;

                // Only show status change for DONE, ABORTED, or PENDING jobs
                if (currentStatus === 'DONE' || currentStatus === 'ABORTED' || currentStatus === 'PENDING') {
                    statusChangeSection.style.display = 'block';
                    
                    // Set title based on current status
                    if (currentStatus === 'DONE') {
                        statusChangeTitle.textContent = 'Change Job Status to PENDING';
                    } else if (currentStatus === 'ABORTED') {
                        statusChangeTitle.textContent = 'Change Job Status to PENDING';
                    } else if (currentStatus === 'PENDING') {
                        statusChangeTitle.textContent = 'Change Job Status to DONE';
                    }
                } else {
                    statusChangeSection.style.display = 'none';
                }

                // Clear old contents
                messageTimeline.innerHTML = "";
                parametersTable.innerHTML = "";
                parametersTable.classList.add("hidden");
                toggleBtn.innerHTML = "&#9654; View Parameters"; // ➤ icon

                try {
                    // Show parameters table
                    if (parameters && typeof parameters === "object") {
                        const table = document.createElement("table");
                        table.innerHTML = `<tr><th>Key</th><th>Value</th></tr>`;
                        for (let key in parameters) {
                            const row = document.createElement("tr");
                            row.innerHTML = `<td>${key}</td><td>${parameters[key]}</td>`;
                            table.appendChild(row);
                        }
                        parametersTable.appendChild(table);
                    }

                    // Show job history (newest first)
                    const parsedMessage = JSON.parse(JSON.stringify(message)).reverse();

                    parsedMessage.forEach(entry => {
                        const item = document.createElement("div");
                        item.classList.add("timeline-item");

                        const timestamp = new Date(entry.timestamp * 1000).toLocaleString("en-US", {
                            weekday: "long",
                            year: "numeric",
                            month: "short",
                            day: "numeric",
                            hour: "2-digit",
                            minute: "2-digit",
                            second: "2-digit",
                            hour12: true
                        });

                        item.innerHTML = `
                            <div class="message">${entry.reason}</div>
                            <div class="timestamp">${timestamp}</div>
                        `;
                        messageTimeline.appendChild(item);
                    });

                } catch (e) {
                    messageTimeline.innerHTML = "<p>Invalid message format</p>";
                }

                modal.style.display = "block";
            }

            function toggleParams() {
                const parametersTable = document.getElementById("parametersTable");
                const toggleBtn = document.getElementById("toggleParamsBtn");

                if (parametersTable.classList.contains("hidden")) {
                    parametersTable.classList.remove("hidden");
                    toggleBtn.innerHTML = "&#9660; Hide Parameters"; // ▼
                } else {
                    parametersTable.classList.add("hidden");
                    toggleBtn.innerHTML = "&#9654; View Parameters"; // ➤
                }
            }

            function closeMessageModal() {
                document.getElementById("messageModal").style.display = "none";
            }

            function changeJobStatus() {
                const jobId = document.getElementById("jobId").textContent;
                const reason = document.getElementById("statusChangeReason").value;
                const pin = document.getElementById("statusChangePin").value;
                const title = document.getElementById("statusChangeTitle").textContent;
                
                // Determine new status from title
                let newStatus = "";
                if (title.includes("to PENDING")) {
                    newStatus = "PENDING";
                } else if (title.includes("to DONE")) {
                    newStatus = "DONE";
                }
                
                if (!newStatus) {
                    showNotification("Unable to determine target status", "error");
                    return;
                }
                
                if (!pin) {
                    showNotification("Please enter the 4-digit PIN", "warning");
                    return;
                }
                
                if (pin.length !== 4 || !/^\d{4}$/.test(pin)) {
                    showNotification("PIN must be exactly 4 digits", "warning");
                    return;
                }
                
                // Show loading state
                const changeBtn = document.getElementById("changeStatusBtn");
                const originalText = changeBtn.textContent;
                changeBtn.textContent = "Changing...";
                changeBtn.disabled = true;
                
                fetch('/change_job_status', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        job_id: parseInt(jobId),
                        new_status: newStatus,
                        reason: reason,
                        pin: pin
                    })
                })
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        showNotification("Status changed successfully!", "success");
                        // Reset form
                        document.getElementById("statusChangeReason").value = "";
                        document.getElementById("statusChangePin").value = "";
                        // Close modal after a short delay
                        setTimeout(() => {
                            closeMessageModal();
                            location.reload();
                        }, 1500);
                    } else {
                        showNotification("Error: " + (data.error || "Failed to change status"), "error");
                    }
                })
                .catch(error => {
                    console.error('Error:', error);
                    showNotification("Error changing status: " + error.message, "error");
                })
                .finally(() => {
                    // Reset button state
                    changeBtn.textContent = originalText;
                    changeBtn.disabled = false;
                });
            }

            function showNotification(message, type = "info") {
                // Remove existing notifications
                const existingNotifications = document.querySelectorAll('.notification');
                existingNotifications.forEach(notification => notification.remove());
                
                // Create notification element
                const notification = document.createElement('div');
                notification.className = `notification notification-${type}`;
                notification.innerHTML = `
                    <div class="notification-content">
                        <span class="notification-message">${message}</span>
                        <button class="notification-close" onclick="this.parentElement.parentElement.remove()">×</button>
                    </div>
                `;
                
                // Add to page
                document.body.appendChild(notification);
                
                // Auto-remove after 5 seconds for success/info, 8 seconds for warnings/errors
                const autoRemoveTime = (type === "success" || type === "info") ? 5000 : 8000;
                setTimeout(() => {
                    if (notification.parentElement) {
                        notification.remove();
                    }
                }, autoRemoveTime);
            }

            window.onclick = function(event) {
                const modal = document.getElementById("messageModal");
                if (event.target === modal) {
                    modal.style.display = "none";
                }
            };

            /**
            * Sort an HTML table (tbody rows) by a specific column index.
            * tableId: the ID of the <table> element
            * colIndex: the zero-based index of the column to sort
            * dataType: "string" | "number" for how values are compared
            * iconRef: The <span> element that was clicked (to track asc/desc)
            */
            function sortTable(tableId, colIndex, dataType, iconRef) {
                const table = document.getElementById(tableId);
                const tbody = table.querySelector("tbody");
                const rows = Array.from(tbody.querySelectorAll("tr"));

                // Check or toggle ascending/descending state on the icon
                let ascending = iconRef.getAttribute("data-ascending") === "true" ? false : true;
                iconRef.setAttribute("data-ascending", ascending ? "true" : "false");

                rows.sort((rowA, rowB) => {
                    const cellA = rowA.children[colIndex].innerText.trim();
                    const cellB = rowB.children[colIndex].innerText.trim();

                    // For numeric columns
                    if (dataType === "number") {
                        const valA = parseFloat(cellA) || 0;
                        const valB = parseFloat(cellB) || 0;
                        return ascending ? valA - valB : valB - valA;
                    } 
                    // Otherwise string compare
                    if (ascending) {
                        return cellA.localeCompare(cellB);
                    } else {
                        return cellB.localeCompare(cellA);
                    }
                });

                // Re-insert sorted rows into the table
                rows.forEach(row => tbody.appendChild(row));
            }
        </script>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1><i class="fas fa-chart-line"></i> Job Distribution Dashboard</h1>
            </div>
            
            <div class="main-content">
        
        <div id="statsModal" class="modal-2">
            <div class="modal-content-2">
                <span class="close" onclick="closeModal()">&times;</span>
                <h2>Machine Specific Stats</h2>
                <div style="text-align: center; margin-bottom: 20px;">
                    <div style="display: inline-block; position: relative; width: 80px; height: 80px;">
                        <svg width="80" height="80" style="transform: rotate(-90deg);">
                            <circle cx="40" cy="40" r="35" stroke="#e0e0e0" stroke-width="6" fill="none"></circle>
                            <circle cx="40" cy="40" r="35" stroke="#4CAF50" stroke-width="6" fill="none" 
                                stroke-dasharray="{{ 2 * 3.14159 * 35 }}" 
                                stroke-dashoffset="{{ 2 * 3.14159 * 35 * (1 - (total_jobs_completed / total_jobs if total_jobs > 0 else 0)) }}"
                                style="transition: stroke-dashoffset 0.5s ease;"></circle>
                        </svg>
                        <div style="position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%); font-weight: bold; font-size: 12px;">
                            {{ "%.0f"|format((total_jobs_completed / total_jobs * 100) if total_jobs > 0 else 0) }}%
                        </div>
                    </div>
                    <p style="margin: 10px 0 0 0; font-size: 14px; color: #666;">Overall Progress</p>
                </div>
                <table class="stats-table">
                    <tr style="position:sticky; top:-17px; z-index:2;">
                        <th>Name</th>
                        <th>Instances</th>
                        <th>Jobs Done</th>
                        <th>Avg Completion Time</th>
                        <th>Percentage of Share</th>
                    </tr>
                    {% for machine, data in machine_stats.items() %}
                    <tr>
                        <td>{{ machine }}</td>
                        <td>{{ data.instance_count }}</td>
                        <td>{{ data.count }}</td>
                        <td>{{ data.average_time }}</td>
                        <td>{{ data.percentage }}%</td>
                    </tr>
                    {% endfor %}
                </table>
            </div>
        </div>
                <div class="dashboard-grid">
                    <div class="sidebar">
                        <button class="btn" onclick="openModal()">
                            <i class="fas fa-chart-bar"></i> Show Machine Statistics
                        </button>
                        
                        <div class="stats-card">
                            <h3><i class="fas fa-info-circle"></i> Experiment Overview</h3>
                            <div class="experiment-info">
                                <p><strong>ID:</strong> {{ expId }}</p>
                                <p><strong>Total Jobs:</strong> {{ total_jobs }}</p>
                                <p><strong>Avg Time:</strong> {{ avg_completion_time }}</p>
                            </div>
                            
                            <div class="stats-grid">
                                <div class="stat-item">
                                    <div class="stat-icon" style="color: #27ae60;"><i class="fas fa-check-circle"></i></div>
                                    <div class="stat-label">Completed</div>
                                    <div class="stat-value">{{ total_jobs_completed }}</div>
                                </div>
                                <div class="stat-item">
                                    <div class="stat-icon" style="color: #f39c12;"><i class="fas fa-play-circle"></i></div>
                                    <div class="stat-label">Running</div>
                                    <div class="stat-value">{{ total_jobs_served }}</div>
                                </div>
                                <div class="stat-item">
                                    <div class="stat-icon" style="color: #e74c3c;"><i class="fas fa-times-circle"></i></div>
                                    <div class="stat-label">Aborted</div>
                                    <div class="stat-value">{{ total_jobs_aborted }}</div>
                                </div>
                                <div class="stat-item">
                                    <div class="stat-icon" style="color: #95a5a6;"><i class="fas fa-pause-circle"></i></div>
                                    <div class="stat-label">Pending</div>
                                    <div class="stat-value">{{ total_jobs - total_jobs_completed - total_jobs_served - total_jobs_aborted }}</div>
                                </div>
                            </div>
                            
                            <div class="progress-container">
                                <h4>Job Completion Progress</h4>
                                <div class="progress-bar">
                                    <div class="progress-fill" style="width: {{ (total_jobs_completed / total_jobs * 100) if total_jobs > 0 else 0 }}%;"></div>
                                </div>
                                <div class="progress-text">
                                    <span>{{ "%.1f"|format((total_jobs_completed / total_jobs * 100) if total_jobs > 0 else 0) }}% Complete</span>
                                    <span>{{ total_jobs - total_jobs_completed }} Remaining</span>
                                </div>
                            </div>
                            
                            <div style="border-top: 1px solid #e0e0e0; padding-top: 16px; margin-top: 16px; background: #f9f9f9; padding: 12px; border-radius: 6px;">
                                <strong style="color: #333;">Interval Total:</strong> <span id="totalJobs" style="color: #2196F3; font-weight: bold;">0</span>
                            </div>
                            
                            <div class="form-group">
                                <label class="form-label" for="machineFilter">Select Machine:</label>
                                <select class="form-select" id="machineFilter" onchange="updateChart()">
                                    <option value="all">All Machines</option>
                                    {% for machine in machine_names %}
                                        <option value="{{ machine }}">{{ machine }}</option>
                                    {% endfor %}
                                </select>
                            </div>
                            
                            <div class="form-group">
                                <label class="form-label" for="timeInterval">Select Interval:</label>
                                <select class="form-select" id="timeInterval" onchange="updateChart()">
                                    <option value="hourly">Hourly</option>
                                    <option value="minutely">Minutely</option>
                                    <option value="daily">Daily</option>
                                </select>
                            </div>
                        </div>
                        
                        <div class="stats-card">
                            <h3><i class="fas fa-server"></i> API Request Statistics</h3>
                            <div class="api-stats">
                                {% for stat in api_stats %}
                                <div class="api-stat-item">
                                    <div>
                                        <div class="api-endpoint">{{ stat.endpoint }}</div>
                                        <div class="api-method">{{ stat.method }}</div>
                                    </div>
                                    <div class="api-count">{{ stat.request_count }}</div>
                                </div>
                                {% endfor %}
                                {% if not api_stats %}
                                <div style="text-align: center; color: #64748b; font-size: 0.875rem; padding: 20px;">
                                    No API requests tracked yet
                                </div>
                                {% endif %}
                                {% if api_stats %}
                                <div class="api-stat-item" style="border-top: 2px solid #e2e8f0; margin-top: 10px; padding-top: 10px;">
                                    <div>
                                        <div class="api-endpoint" style="font-weight: bold; color: #1e293b;">Total Requests</div>
                                        <div class="api-method" style="color: #64748b;">All Endpoints</div>
                                    </div>
                                    <div class="api-count" style="background: #3b82f6; color: white; font-weight: bold;">{{ total_api_requests }}</div>
                                </div>
                                {% endif %}
                            </div>
                        </div>
                    </div>
                    
                    <div class="chart-container">
                        <div class="chart-wrapper">
                            <canvas id="jobChart"></canvas>
                        </div>
                        
                        <!-- Tab Buttons -->
                        <div class="tabs">
                            <button class="tab-button active" onclick="openTab('SERVED')">
                                <i class="fas fa-play-circle"></i>
                                SERVED
                                <span class="tab-count">{{ jobs|selectattr('status', 'equalto', 'SERVED')|list|length }}</span>
                            </button>
                            <button class="tab-button" onclick="openTab('DONE')">
                                <i class="fas fa-check-circle"></i>
                                DONE
                                <span class="tab-count">{{ jobs|selectattr('status', 'equalto', 'DONE')|list|length }}</span>
                            </button>
                            <button class="tab-button" onclick="openTab('ABORTED')">
                                <i class="fas fa-times-circle"></i>
                                ABORTED
                                <span class="tab-count">{{ jobs|selectattr('status', 'equalto', 'ABORTED')|list|length }}</span>
                            </button>
                            <button class="tab-button" onclick="openTab('PENDING')">
                                <i class="fas fa-pause-circle"></i>
                                PENDING
                                <span class="tab-count">{{ jobs|selectattr('status', 'equalto', 'PENDING')|list|length }}</span>
                            </button>
                        </div>
                        
                        <!-- Tab Contents -->
                        {% for status in ['SERVED', 'DONE', 'ABORTED', 'PENDING'] %}
                            <div id="{{ status }}" class="tabcontent {% if status == 'SERVED' %}active{% endif %}">
                                <div class="table-wrapper">
                                    <table class="myTable">
                                        <thead>
                                            <tr>
                                                <th>ID <span class="sort-icon" onclick="sortTable(this, 0, 'number')">↕</span></th>
                                                <th>Machine <span class="sort-icon" onclick="sortTable(this, 1, 'string')">↕</span></th>
                                                <th>Requested At <span class="sort-icon" onclick="sortTable(this, 2, 'string')">↕</span></th>
                                                <th>Started At <span class="sort-icon" onclick="sortTable(this, 3, 'string')">↕</span></th>
                                                <th>Completed At <span class="sort-icon" onclick="sortTable(this, 4, 'string')">↕</span></th>
                                                <th>Duration <span class="sort-icon" onclick="sortTable(this, 5, 'string')">↕</span></th>
                                                <th>Job History <span class="sort-icon" onclick="sortTable(this, 6, 'string')">↕</span></th>
                                            </tr>
                                        </thead>
                                        <tbody>
                                        {% for job in jobs %}
                                            {% if job.status == status %}
                                            <tr>
                                                <td style="font-weight: bold;">{{ job.id }}</td>
                                                <td>{{ job.machine or '' }}</td>
                                                <td data-timestamp="{{ job.request_timestamp if job.request_timestamp else '' }}">{{ format_timestamp(job.request_timestamp) if job.request_timestamp else '' }}</td>
                                                <td data-timestamp="{{ job.request_timestamp if job.request_timestamp else '' }}">{{ format_timestamp(job.request_timestamp) if job.request_timestamp else '' }}</td>
                                                <td data-timestamp="{{ job.completion_timestamp if job.completion_timestamp else '' }}">{{ format_timestamp(job.completion_timestamp) if job.completion_timestamp else '' }}</td>
                                                <td>{{ format_time(job.required_time) if job.required_time else '' }}</td>
                                                <td>
                                                    <button class="view-details-btn" onclick="showMessageModal({{ job.id }}, {{ job.message }}, {{ job.parameters }}, '{{ job.status }}')">
                                                        <i class="fas fa-eye"></i> View Details
                                                    </button>
                                                </td>
                                            </tr>
                                            {% endif %}
                                        {% endfor %}
                                        </tbody>
                                    </table>
                                </div>
                            </div>
                        {% endfor %}
                    </div>
                </div>
        
        <script>
            let chart;
            function updateChart() {
                let interval = document.getElementById("timeInterval").value;
                let machine = document.getElementById("machineFilter").value;
                fetch(`/job_stats?interval=` + interval + `&machine=` + machine)
                    .then(response => response.json())
                    .then(data => {
                        if (chart) { chart.destroy(); }
                        
                        // Convert timestamps to local time for chart labels
                        let formattedLabels = data.labels;
                        if (data.timestamps) {
                            formattedLabels = data.labels.map(timestamp => {
                                if (typeof timestamp === 'number') {
                                    const date = new Date(timestamp * 1000);
                                    if (interval === 'minutely') {
                                        return date.toLocaleTimeString([], {hour: '2-digit', minute: '2-digit'});
                                    } else if (interval === 'hourly') {
                                        return date.toLocaleTimeString([], {hour: '2-digit', minute: '2-digit'});
                                    } else {
                                        return date.toLocaleDateString([], {month: 'short', day: 'numeric'});
                                    }
                                }
                                return timestamp;
                            });
                        }
                        
                        let ctx = document.getElementById("jobChart").getContext("2d");
                        chart = new Chart(ctx, {
                            type: "bar",
                            data: {
                                labels: formattedLabels,
                                datasets: [{
                                    label: "Jobs Completed",
                                    data: data.values,
                                    backgroundColor: "#3498db",
                                    borderColor: "#2980b9",
                                    borderWidth: 1
                                }]
                            },
                            options: {
                                responsive: true,
                                maintainAspectRatio: false,
                                scales: { 
                                    y: { beginAtZero: true } 
                                },
                                plugins: {
                                    legend: {
                                        display: true,
                                        position: 'top'
                                    }
                                }
                            }
                        });
                        // Update the total jobs count in the HTML element with id "totalJobs"
                        document.getElementById("totalJobs").innerText = data.total_jobs;
                    });
            }
            updateChart();
        </script>
        
        <!-- Modal -->
        <div id="messageModal" class="modal">
            <div class="modal-content">
                <span class="close" onclick="closeMessageModal()">&times;</span>
                <h2>Job History</h2>

                <div style="display: flex; align-items: center; justify-content: space-between;">
                    <p><strong>Job ID:</strong> <span id="jobId"></span></p>
                    <button id="toggleParamsBtn" onclick="toggleParams()" style="cursor: pointer; border: none; background: none; font-weight: bold;">&#9654; View Parameters</button>
                </div>

                <!-- Status Change Section -->
                <div id="statusChangeSection" style="margin: 15px 0; padding: 15px; background: #f8f9fa; border-radius: 8px; border: 1px solid #dee2e6;">
                    <h4 id="statusChangeTitle" style="margin: 0 0 10px 0; color: #495057;">Change Job Status</h4>
                    <div style="display: flex; gap: 10px; align-items: center;">
                        <input type="text" id="statusChangeReason" placeholder="Reason (optional)" style="flex: 1; padding: 8px; border: 1px solid #ced4da; border-radius: 4px;">
                        <input type="password" id="statusChangePin" placeholder="PIN" style="padding: 8px; border: 1px solid #ced4da; border-radius: 4px; width: 80px;" maxlength="4" pattern="[0-9]{4}">
                        <button id="changeStatusBtn" onclick="changeJobStatus()" style="padding: 8px 16px; background: #007bff; color: white; border: none; border-radius: 4px; cursor: pointer; white-space: nowrap;">Change Status</button>
                    </div>
                </div>

                <div id="parametersTable" class="hidden" style="margin-bottom: 15px;"></div>

                <div class="timeline" id="messageTimeline"></div>
            </div>
        </div>



            </div> <!-- End main-content -->
        </div> <!-- End container -->
        
        <script>
            // Function to convert Unix timestamp to local time
            function formatTimestamp(timestamp) {
                if (!timestamp || timestamp === 'N/A') return 'N/A';
                const date = new Date(timestamp * 1000); // Convert Unix timestamp to milliseconds
                return date.toLocaleString(); // Use browser's local timezone
            }
            
            // Function to convert all timestamps in the table to local time
            function convertTimestampsToLocal() {
                const timestampCells = document.querySelectorAll('[data-timestamp]');
                timestampCells.forEach(cell => {
                    const timestamp = cell.getAttribute('data-timestamp');
                    if (timestamp && timestamp !== 'N/A') {
                        cell.textContent = formatTimestamp(parseFloat(timestamp));
                    }
                });
            }
            
            // Function to handle watermark visibility
            function handleTableWatermarks() {
                const tables = document.querySelectorAll('.myTable');
                tables.forEach(table => {
                    const tableWrapper = table.closest('.table-wrapper');
                    const tbody = table.querySelector('tbody');
                    
                    if (tbody) {
                        const visibleRows = tbody.querySelectorAll('tr:not(.dtr-hidden)');
                        
                        // Check if watermark exists, if not create it
                        let watermark = tableWrapper.querySelector('.table-watermark');
                        if (!watermark) {
                            watermark = document.createElement('div');
                            watermark.className = 'table-watermark';
                            watermark.innerHTML = '<i class="fas fa-database"></i><div class="watermark-text">No Data Available</div>';
                            tableWrapper.appendChild(watermark);
                        }
                        
                        if (visibleRows.length === 0) {
                            watermark.style.display = 'block';
                        } else {
                            watermark.style.display = 'none';
                        }
                    }
                });
            }
            
           $(document).ready(function () {
                let tables = new DataTable('.myTable', {
                    "language": {
                        "emptyTable": "" // Remove default "No data available in table" text
                    }
                }); // Initializes ALL tables with that class
                
                // Convert timestamps to local time after table is initialized
                convertTimestampsToLocal();
                
                // Handle watermark visibility
                handleTableWatermarks();
                
                // Handle watermark visibility on search/filter
                tables.on('search.dt', function() {
                    setTimeout(handleTableWatermarks, 100);
                });
            });
        </script>
    </body>
    </html>
    """

    return render_template_string(
        html_template,
        expId = expId,
        total_jobs=total_jobs,
        total_jobs_served=total_jobs_served,
        total_jobs_completed=total_jobs_completed,
        total_jobs_aborted=total_jobs_aborted,
        avg_completion_time=avg_completion_time,
        jobs=jobs,
        format_timestamp=format_timestamp,
        format_time=format_time,
        machine_stats=machine_stats,
        machine_names=machine_names,
        api_stats=api_stats,
        total_api_requests=total_api_requests
    )

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Start the Flask Dashboard server")
    parser.add_argument("--host", default="0.0.0.0", help="IP address to bind to")
    parser.add_argument("--jobDB", default="jobs.db", help="SQLite database file (<filename>.db) placed in the same directory as server.py")
    parser.add_argument("--enableNgrok", default=False, help="Enable ngrok for external access")
    parser.add_argument("--port", type=int, default=5050, help="Port number to listen on")
    parser.add_argument("--expId", type=str, default="sim1", help="Give an unique name")
    args = parser.parse_args()
    createExpBaseDirectory(args)
    setup_log(args)
    logging.info(f"Starting Flask Dashboard server on {args.host}:{args.port}...")
    DB_FILE = os.path.join(BASE_DIR, args.expId, args.jobDB)
    EXP_ID = args.expId
    
    # Initialize database connection
    db = JobDatabase(DB_FILE)
    
    if args.enableNgrok == True:
        logging.info("Starting ngrok tunnel...")
        public_url = ngrok.connect(args.port)
        print(f" >> dashboard : {public_url}")
        logging.info(f"ngrok tunnel established at {public_url}")
    
    # Start the Flask app
    app.run(host=args.host, port=args.port)  

# python dashboard.py --expId=sim1 --jobDB=jobs.db --host=0.0.0.0 --port=5050
