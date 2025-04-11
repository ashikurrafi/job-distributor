import subprocess
import json
import os
import logging
import shlex
import signal
import sys
import atexit

CONFIG_FILE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")
LOG_FILENAME = "__start__.log"
processes = {}  # moved to global so cleanup can access it


def run_command(cmd):
    """Run a command and stream its output."""
    process = subprocess.Popen(cmd, shell=True)
    process.wait()


def cleanup(*args):
    logging.info("Cleaning up child processes...")
    for name, proc in processes.items():
        try:
            os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
            logging.info(f"Killed {name} (PID {proc.pid})")
        except Exception as e:
            logging.warning(f"Could not kill {name}: {e}")


def main():
    global processes  # so cleanup can access it

    with open(CONFIG_FILE_PATH) as f:
        config = json.load(f)

    # Set up logging
    LOG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), LOG_FILENAME)
    logging.basicConfig(
        filename=LOG_FILE,
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
    )

    # Register cleanup on normal exit and termination signals
    atexit.register(cleanup)
    signal.signal(signal.SIGINT, lambda sig, frame: sys.exit(0))
    signal.signal(signal.SIGTERM, lambda sig, frame: sys.exit(0))

    # Build commands from config
    create_cmd = (
        f"python src/create_job_db.py "
        f"--expId={config['expId']} "
        f"--jobDB={config['jobDB']} "
        f"--parameters='{json.dumps(config['parameters'])}'"
    )

    server_cmd = (
        f"python src/server.py "
        f"--expId={config['expId']} "
        f"--jobDB={config['jobDB']} "
        f"--host={config['host']} "
        f"--port={config['server_port']}"
    )

    dashboard_cmd = (
        f"python src/dashboard.py "
        f"--expId={config['expId']} "
        f"--jobDB={config['jobDB']} "
        f"--host={config['host']} "
        f"--port={config['dashboard_port']}"
    )

    cleaner_cmd = (
        f"python src/job_cleaner.py "
        f"--expId={config['expId']} "
        f"--jobDB={config['jobDB']} "
        f"--cleanupInterval={config['cleanupInterval']} "
        f"--timeoutLimit={config['timeoutLimit']}"
    )

    if config['fresh_start']:
        logging.info("Starting job database creation...")
        subprocess.run(create_cmd, shell=True, check=True)
        logging.info("Job DB created. Launching services in parallel...")

    commands = {
        "server": server_cmd,
        "dashboard": dashboard_cmd,
        "job_cleaner": cleaner_cmd
    }

    for name, cmd in commands.items():
        logging.info(f"Launching {name}...")
        processes[name] = subprocess.Popen(
            shlex.split(cmd),
            preexec_fn=os.setsid  # <-- This is what enables group kill
        )

    # Save PIDs
    pid_file = os.path.join(os.path.dirname(__file__), config["expId"], "pids.json")
    with open(pid_file, "w") as f:
        json.dump({name: proc.pid for name, proc in processes.items()}, f)

    for name, proc in processes.items():
        proc.wait()
        logging.info(f"{name} process exited with code {proc.returncode}.")


if __name__ == "__main__":
    main()
