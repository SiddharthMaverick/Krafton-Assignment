#!/usr/bin/env python3
"""
Standalone test runner that starts server and runs test in parallel.
"""
import asyncio
import subprocess
import sys
import time
import os
import threading

def run_server():
    """Start server as a subprocess."""
    proc = subprocess.Popen(
        [sys.executable, "server.py"],
        cwd="C:\\Users\\Admin\\Documents\\Assignment Krafton",
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1  # Line buffered
    )
    return proc

def print_server_output(proc):
    """Print server output in real time."""
    for line in iter(proc.stdout.readline, ''):
        if line:
            print(f"[SERVER] {line.rstrip()}")

def run_test():
    """Run test."""
    proc = subprocess.run(
        [sys.executable, "test_assignment.py"],
        cwd="C:\\Users\\Admin\\Documents\\Assignment Krafton",
        capture_output=False
    )
    return proc.returncode

if __name__ == "__main__":
    # Start server
    server = run_server()
    print("[RUNNER] Server started with PID:", server.pid)
    
    # Start thread to print server output
    server_thread = threading.Thread(target=print_server_output, args=(server,), daemon=True)
    server_thread.start()
    
    # Wait for server to be ready
    time.sleep(3)
    
    # Run test
    print("[RUNNER] Running tests...")
    exit_code = run_test()
    
    # Kill server
    server.terminate()
    server.wait(timeout=5)
    
    sys.exit(exit_code)
