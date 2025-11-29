# Assignment Krafton — Game Server

This repository contains a simple authoritative WebSocket game server used for the assignment tests.

Requirements
- Python 3.8+
- `websockets` library

Quick start (PowerShell)

```powershell
cd "Assignment Krafton"
# (optional) Create and activate a virtualenv, then install requirements
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt

# Start the server (runs indefinitely)
python server.py

# In another terminal, run the tests
python test_assignment.py
```

Notes
- The server logs use simple timestamped messages printed to stdout.
- The test script `test_assignment.py` connects two players and validates movement, coin pickup, and basic anti-cheat behavior.
- If your terminal has encoding issues printing Unicode characters, you may see an encoding error at the end of the test script — the tests themselves still passed.

If you want me to revert any runtime tuning (e.g. `PLAYER_SPEED`) or integrate a more robust logging framework, tell me and I will implement it.
