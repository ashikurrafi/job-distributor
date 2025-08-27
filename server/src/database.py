import sqlite3
import json
import logging
import threading
import time
from contextlib import contextmanager
from typing import List, Dict, Any, Optional

# Constants for job statuses
STATUS_PENDING = "PENDING"
STATUS_SERVED = "SERVED"
STATUS_DONE = "DONE"
STATUS_ABORTED = "ABORTED"

class JobDatabase:
    """SQLite database handler for job distribution system."""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.lock = threading.Lock()
        self._init_database()
    
    def _init_database(self):
        """Initialize the database with the jobs and api_stats tables."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS jobs (
                    id INTEGER PRIMARY KEY,
                    requested_by TEXT DEFAULT '',
                    request_timestamp REAL DEFAULT 0,
                    completion_timestamp REAL DEFAULT 0,
                    required_time REAL DEFAULT 0,
                    last_ping_timestamp REAL DEFAULT 0,
                    status TEXT DEFAULT 'PENDING',
                    message TEXT DEFAULT '[]',
                    parameters TEXT NOT NULL
                )
            ''')
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS api_stats (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    endpoint TEXT NOT NULL,
                    method TEXT NOT NULL,
                    request_count INTEGER DEFAULT 0,
                    last_updated REAL DEFAULT 0,
                    UNIQUE(endpoint, method)
                )
            ''')
            
            # Create indexes for optimal query performance
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_jobs_status ON jobs(status)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_jobs_status_id ON jobs(status, id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_jobs_last_ping ON jobs(last_ping_timestamp)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_jobs_status_ping ON jobs(status, last_ping_timestamp)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_jobs_requested_by ON jobs(requested_by)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_jobs_request_timestamp ON jobs(request_timestamp)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_jobs_completion_timestamp ON jobs(completion_timestamp)')
            
            conn.commit()
            logging.info(f"Database initialized with indexes at {self.db_path}")
    
    @contextmanager
    def get_connection(self):
        """Get a database connection with proper error handling."""
        conn = None
        try:
            conn = sqlite3.connect(self.db_path, timeout=30.0)
            conn.row_factory = sqlite3.Row  # Enable dict-like access to rows
            yield conn
        except Exception as e:
            if conn:
                conn.rollback()
            logging.error(f"Database error: {e}")
            raise
        finally:
            if conn:
                conn.close()
    
    def create_jobs(self, parameters_list: List[str], clear_api_stats: bool = True) -> int:
        """Create multiple jobs from a list of parameter strings."""
        with self.lock:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Clear existing jobs
                cursor.execute("DELETE FROM jobs")
                
                # Clear API stats if requested (for fresh starts)
                if clear_api_stats:
                    cursor.execute("DELETE FROM api_stats")
                    logging.info("API stats cleared for fresh start")
                
                # Insert new jobs
                jobs_data = []
                for i, params in enumerate(parameters_list):
                    jobs_data.append((
                        i,  # id
                        '',  # requested_by
                        0,   # request_timestamp
                        0,   # completion_timestamp
                        0,   # required_time
                        0,   # last_ping_timestamp
                        STATUS_PENDING,  # status
                        '[]',  # message
                        params  # parameters
                    ))
                
                cursor.executemany('''
                    INSERT INTO jobs 
                    (id, requested_by, request_timestamp, completion_timestamp, 
                     required_time, last_ping_timestamp, status, message, parameters)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', jobs_data)
                
                conn.commit()
                total_jobs = len(parameters_list)
                logging.info(f"Created {total_jobs} jobs in database")
                return total_jobs
    
    def get_all_jobs(self) -> List[Dict[str, Any]]:
        """Get all jobs from the database."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM jobs ORDER BY id")
            rows = cursor.fetchall()
            
            jobs = []
            for row in rows:
                job = dict(row)
                # Parse JSON fields
                try:
                    job['message'] = json.loads(job['message'])
                except json.JSONDecodeError:
                    job['message'] = []
                try:
                    job['parameters'] = json.loads(job['parameters'])
                except json.JSONDecodeError:
                    job['parameters'] = {}
                jobs.append(job)
            
            return jobs
    
    def track_api_request(self, endpoint: str, method: str):
        """Track an API request by incrementing the counter."""
        with self.lock:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                now = time.time()
                
                # Insert or update the API stats
                cursor.execute('''
                    INSERT INTO api_stats (endpoint, method, request_count, last_updated)
                    VALUES (?, ?, 1, ?)
                    ON CONFLICT(endpoint, method) 
                    DO UPDATE SET 
                        request_count = request_count + 1,
                        last_updated = ?
                ''', (endpoint, method, now, now))
                
                conn.commit()
    
    def get_api_stats(self) -> List[Dict[str, Any]]:
        """Get API request statistics."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT endpoint, method, request_count, last_updated 
                FROM api_stats 
                ORDER BY request_count DESC
            ''')
            rows = cursor.fetchall()
            
            stats = []
            for row in rows:
                stats.append({
                    'endpoint': row['endpoint'],
                    'method': row['method'],
                    'request_count': row['request_count'],
                    'last_updated': row['last_updated']
                })
            
            return stats
    
    def clear_api_stats(self) -> bool:
        """Clear all API request statistics."""
        with self.lock:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM api_stats")
                conn.commit()
                logging.info("API stats cleared")
                return True
    
    def get_database_info(self) -> Dict[str, Any]:
        """Get database information including indexes and table sizes."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Get table sizes
            cursor.execute("SELECT COUNT(*) as count FROM jobs")
            jobs_count = cursor.fetchone()['count']
            
            cursor.execute("SELECT COUNT(*) as count FROM api_stats")
            api_stats_count = cursor.fetchone()['count']
            
            # Get indexes
            cursor.execute("""
                SELECT name, sql FROM sqlite_master 
                WHERE type='index' AND tbl_name='jobs'
                ORDER BY name
            """)
            indexes = [{'name': row['name'], 'sql': row['sql']} for row in cursor.fetchall()]
            
            # Get table schema
            cursor.execute("PRAGMA table_info(jobs)")
            schema = [{'name': row['name'], 'type': row['type']} for row in cursor.fetchall()]
            
            return {
                'jobs_count': jobs_count,
                'api_stats_count': api_stats_count,
                'indexes': indexes,
                'schema': schema
            }
    
    def get_job_by_id(self, job_id: int) -> Optional[Dict[str, Any]]:
        """Get a specific job by ID."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM jobs WHERE id = ?", (job_id,))
            row = cursor.fetchone()
            
            if row:
                job = dict(row)
                # Parse JSON fields
                try:
                    job['message'] = json.loads(job['message'])
                except json.JSONDecodeError:
                    job['message'] = []
                try:
                    job['parameters'] = json.loads(job['parameters'])
                except json.JSONDecodeError:
                    job['parameters'] = {}
                return job
            return None

    def get_jobs_paginated(self, page: int = 1, per_page: int = 50, status: str = None, search_job_id: str = None) -> Dict[str, Any]:
        """
        Get jobs with pagination support.
        
        Args:
            page: Page number (1-based)
            per_page: Number of jobs per page
            status: Filter by status (optional)
            search_job_id: Search by job ID (optional)
        
        Returns:
            Dict with jobs, total_count, total_pages, current_page
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Build WHERE clause
            where_conditions = []
            params = []
            
            if status:
                where_conditions.append("status = ?")
                params.append(status)
            
            if search_job_id:
                where_conditions.append("id = ?")
                params.append(int(search_job_id))
            
            where_clause = " WHERE " + " AND ".join(where_conditions) if where_conditions else ""
            
            # Get total count
            count_query = f"SELECT COUNT(*) as count FROM jobs{where_clause}"
            cursor.execute(count_query, params)
            total_count = cursor.fetchone()['count']
            
            # Calculate pagination
            total_pages = (total_count + per_page - 1) // per_page
            offset = (page - 1) * per_page
            
            # Get jobs for current page
            jobs_query = f"""
                SELECT * FROM jobs{where_clause}
                ORDER BY id
                LIMIT ? OFFSET ?
            """
            cursor.execute(jobs_query, params + [per_page, offset])
            rows = cursor.fetchall()
            
            jobs = []
            for row in rows:
                job = dict(row)
                # Parse JSON fields
                try:
                    job['message'] = json.loads(job['message'])
                except json.JSONDecodeError:
                    job['message'] = []
                try:
                    job['parameters'] = json.loads(job['parameters'])
                except json.JSONDecodeError:
                    job['parameters'] = {}
                jobs.append(job)
            
            return {
                'jobs': jobs,
                'total_count': total_count,
                'total_pages': total_pages,
                'current_page': page,
                'per_page': per_page
            }
    
    def request_job(self, requested_by: str) -> Optional[Dict[str, Any]]:
        """Assign a PENDING job to a requester and mark it as SERVED."""
        with self.lock:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Find first PENDING job
                cursor.execute(
                    "SELECT * FROM jobs WHERE status = ? ORDER BY id LIMIT 1",
                    (STATUS_PENDING,)
                )
                row = cursor.fetchone()
                
                if not row:
                    return None
                
                job = dict(row)
                timestamp = time.time()
                
                # Parse existing messages
                try:
                    messages = json.loads(job['message'])
                except json.JSONDecodeError:
                    messages = []
                
                # Add new message
                messages.append({
                    "reason": f"{requested_by} requests this job for execution",
                    "timestamp": timestamp
                })
                
                # Update job
                cursor.execute('''
                    UPDATE jobs 
                    SET requested_by = ?, status = ?, request_timestamp = ?, message = ?
                    WHERE id = ?
                ''', (requested_by, STATUS_SERVED, timestamp, json.dumps(messages), job['id']))
                
                conn.commit()
                
                # Return updated job
                job['requested_by'] = requested_by
                job['status'] = STATUS_SERVED
                job['request_timestamp'] = timestamp
                job['message'] = messages
                try:
                    job['parameters'] = json.loads(job['parameters'])
                except json.JSONDecodeError:
                    job['parameters'] = {}
                
                return job
    
    def update_job_status(self, job_id: int, status: str, message: str = "") -> bool:
        """Update job status to DONE or ABORTED."""
        if status not in [STATUS_DONE, STATUS_ABORTED]:
            return False
        
        with self.lock:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Get current job
                cursor.execute(
                    "SELECT * FROM jobs WHERE id = ? AND status = ?",
                    (job_id, STATUS_SERVED)
                )
                row = cursor.fetchone()
                
                if not row:
                    return False
                
                job = dict(row)
                now = time.time()
                required_time = now - job['request_timestamp']
                
                # Parse existing messages
                try:
                    messages = json.loads(job['message'])
                except json.JSONDecodeError:
                    messages = []
                
                # Add new message
                messages.append({
                    "reason": message if message else "No reason provided",
                    "timestamp": now
                })
                
                # Update job
                cursor.execute('''
                    UPDATE jobs 
                    SET status = ?, completion_timestamp = ?, required_time = ?, message = ?
                    WHERE id = ?
                ''', (status, now, required_time, json.dumps(messages), job_id))
                
                conn.commit()
                return True
    
    def change_job_status(self, job_id: int, new_status: str, reason: str = "") -> bool:
        """Change job status for DONE, ABORTED, or PENDING jobs."""
        if new_status not in [STATUS_DONE, STATUS_ABORTED, STATUS_PENDING]:
            return False
        
        with self.lock:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Get current job
                cursor.execute(
                    "SELECT * FROM jobs WHERE id = ? AND status IN (?, ?, ?)",
                    (job_id, STATUS_DONE, STATUS_ABORTED, STATUS_PENDING)
                )
                row = cursor.fetchone()
                
                if not row:
                    return False
                
                job = dict(row)
                now = time.time()
                old_status = job['status']
                
                # Parse existing messages
                try:
                    messages = json.loads(job['message'])
                except json.JSONDecodeError:
                    messages = []
                
                # Add status change message
                status_change_message = f"Manual Status Change: {old_status} → {new_status}"
                if reason:
                    status_change_message += f" | Reason: {reason}"
                else:
                    status_change_message += " | No reason provided"
                
                messages.append({
                    "reason": status_change_message,
                    "timestamp": now
                })
                
                        # Update job status and reset timestamps if going to PENDING
                if new_status == STATUS_PENDING:
                    cursor.execute('''
                        UPDATE jobs 
                        SET status = ?, message = ?, request_timestamp = 0, 
                            completion_timestamp = 0, required_time = 0, 
                            last_ping_timestamp = 0, requested_by = ''
                        WHERE id = ?
                    ''', (new_status, json.dumps(messages), job_id))
                else:
                    cursor.execute('''
                        UPDATE jobs 
                        SET status = ?, message = ?
                        WHERE id = ?
                    ''', (new_status, json.dumps(messages), job_id))
                
                conn.commit()
                return True
    
    def ping_job(self, job_id: int) -> bool:
        """Update last_ping_timestamp for a SERVED job."""
        with self.lock:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Check if job exists and is SERVED
                cursor.execute(
                    "SELECT id FROM jobs WHERE id = ? AND status = ?",
                    (job_id, STATUS_SERVED)
                )
                row = cursor.fetchone()
                
                if not row:
                    return False
                
                now = round(time.time())
                cursor.execute(
                    "UPDATE jobs SET last_ping_timestamp = ? WHERE id = ?",
                    (now, job_id)
                )
                
                conn.commit()
                return True
    
    def reset_aborted_jobs(self) -> int:
        """Reset all ABORTED jobs to PENDING."""
        with self.lock:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                current_time = time.time()
                
                # Get all aborted jobs
                cursor.execute("SELECT * FROM jobs WHERE status = ?", (STATUS_ABORTED,))
                aborted_jobs = cursor.fetchall()
                
                count = 0
                for row in aborted_jobs:
                    job = dict(row)
                    prev_requester = job['requested_by']
                    
                    # Parse existing messages
                    try:
                        messages = json.loads(job['message'])
                    except json.JSONDecodeError:
                        messages = []
                    
                    # Add reset message
                    messages.append({
                        "reason": f"Job Cleaner: Reset job to PENDING status. Previous execution failed on machine '{prev_requester}'. Job is now available for reassignment.",
                        "timestamp": current_time
                    })
                    
                    # Reset job
                    cursor.execute('''
                        UPDATE jobs 
                        SET status = ?, requested_by = '', request_timestamp = 0, 
                            completion_timestamp = 0, required_time = 0, 
                            last_ping_timestamp = 0, message = ?
                        WHERE id = ?
                    ''', (STATUS_PENDING, json.dumps(messages), job['id']))
                    
                    count += 1
                
                conn.commit()
                return count
    
    def reset_stale_served_jobs(self, idle_timeout: int) -> int:
        """Reset SERVED jobs that haven't pinged within the timeout."""
        with self.lock:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                current_time = time.time()
                cutoff_time = current_time - idle_timeout
                
                # Get stale served jobs
                cursor.execute(
                    "SELECT * FROM jobs WHERE status = ? AND last_ping_timestamp < ?",
                    (STATUS_SERVED, cutoff_time)
                )
                stale_jobs = cursor.fetchall()
                
                count = 0
                for row in stale_jobs:
                    job = dict(row)
                    prev_requester = job['requested_by']
                    last_ping = job['last_ping_timestamp']
                    minutes_silent = round((current_time - last_ping) / 60)
                    
                    # Parse existing messages
                    try:
                        messages = json.loads(job['message'])
                    except json.JSONDecodeError:
                        messages = []
                    
                    # Add reset message
                    messages.append({
                        "reason": f"Job Cleaner: Reset job to PENDING status. Machine '{prev_requester}' stopped responding ({minutes_silent} minutes of inactivity). Job is now available for reassignment.",
                        "timestamp": current_time
                    })
                    
                    # Reset job
                    cursor.execute('''
                        UPDATE jobs 
                        SET status = ?, requested_by = '', request_timestamp = 0, 
                            completion_timestamp = 0, required_time = 0, 
                            last_ping_timestamp = 0, message = ?
                        WHERE id = ?
                    ''', (STATUS_PENDING, json.dumps(messages), job['id']))
                    
                    count += 1
                
                conn.commit()
                return count
    
    def get_job_counts_by_status(self) -> Dict[str, int]:
        """Get job counts by status efficiently."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT status, COUNT(*) as count 
                FROM jobs 
                GROUP BY status
            """)
            rows = cursor.fetchall()
            
            counts = {STATUS_PENDING: 0, STATUS_SERVED: 0, STATUS_DONE: 0, STATUS_ABORTED: 0}
            for row in rows:
                counts[row['status']] = row['count']
            
            return counts
    
    def get_jobs_by_status(self, status: str) -> List[Dict[str, Any]]:
        """Get all jobs with a specific status."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM jobs WHERE status = ? ORDER BY id", (status,))
            rows = cursor.fetchall()
            
            jobs = []
            for row in rows:
                job = dict(row)
                # Parse JSON fields
                try:
                    job['message'] = json.loads(job['message'])
                except json.JSONDecodeError:
                    job['message'] = []
                try:
                    job['parameters'] = json.loads(job['parameters'])
                except json.JSONDecodeError:
                    job['parameters'] = {}
                jobs.append(job)
            
            return jobs
    
    def track_api_request(self, endpoint: str, method: str):
        """Track an API request by incrementing the counter."""
        with self.lock:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                now = time.time()
                
                # Insert or update the API stats
                cursor.execute('''
                    INSERT INTO api_stats (endpoint, method, request_count, last_updated)
                    VALUES (?, ?, 1, ?)
                    ON CONFLICT(endpoint, method) 
                    DO UPDATE SET 
                        request_count = request_count + 1,
                        last_updated = ?
                ''', (endpoint, method, now, now))
                
                conn.commit()
    
    def get_api_stats(self) -> List[Dict[str, Any]]:
        """Get API request statistics."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT endpoint, method, request_count, last_updated 
                FROM api_stats 
                ORDER BY request_count DESC
            ''')
            rows = cursor.fetchall()
            
            stats = []
            for row in rows:
                stats.append({
                    'endpoint': row['endpoint'],
                    'method': row['method'],
                    'request_count': row['request_count'],
                    'last_updated': row['last_updated']
                })
            
            return stats
