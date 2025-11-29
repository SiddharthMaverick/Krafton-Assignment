import asyncio
import json
import time
import math
import websockets

SERVER_URL = "ws://localhost:8765"

async def recv_until_type(ws, wanted_type, timeout=3.0):
    """Receive messages until we find a given type or timeout."""
    end = time.time() + timeout
    last_state = None
    while time.time() < end:
        remaining = end - time.time()
        try:
            raw = await asyncio.wait_for(ws.recv(), timeout=remaining)
        except asyncio.TimeoutError:
            break
        try:
            msg = json.loads(raw)
        except json.JSONDecodeError:
            continue

        mtype = msg.get("type")
        if mtype == wanted_type:
            return msg
        if mtype == "state":
            last_state = msg
    # If wanted_type was "state", return whatever we last saw
    if wanted_type == "state":
        return last_state
    return None


async def wait_for_state(ws, timeout=2.0):
    """Convenience wrapper to get the latest state within a small time window."""
    return await recv_until_type(ws, "state", timeout=timeout)


async def main():
    # Join ONE player
    ws = await websockets.connect(SERVER_URL)
    join_msg = {"type": "join", "name": "TestPlayer1"}
    await ws.send(json.dumps(join_msg))
    welcome = await recv_until_type(ws, "welcome", timeout=3.0)
    pid = welcome["id"]
    print(f"Joined with id={pid}")
    
    # Get initial state
    state1 = await wait_for_state(ws, timeout=3.0)
    p1 = state1["players"][pid]
    x0, y0 = p1["x"], p1["y"]
    print(f"Initial position: ({x0:.2f},{y0:.2f})")
    
    # Send move right input
    move_right = {
        "type": "input",
        "playerId": pid,
        "seq": 1,
        "input": {"up": False, "down": False, "left": False, "right": True},
    }
    await ws.send(json.dumps(move_right))
    print(f"Sent move_right input")
    
    # Wait 1 second
    await asyncio.sleep(1.0)
    print(f"Waited 1 second, now getting state...")
    
    # Get new state
    state2 = await wait_for_state(ws, timeout=3.0)
    p2 = state2["players"][pid]
    x1, y1 = p2["x"], p2["y"]
    print(f"Final position: ({x1:.2f},{y1:.2f})")
    
    dx = x1 - x0
    dy = y1 - y0
    dist = math.sqrt(dx * dx + dy * dy)
    print(f"Movement: dx={dx:.4f}, dy={dy:.4f}, dist={dist:.4f}")
    
    if dist > 0.5:
        print("[PASS]")
    else:
        print("[FAIL]")
        
    await ws.close()

asyncio.run(main())
