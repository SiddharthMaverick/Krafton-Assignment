import asyncio
import json
import time
import websockets

SERVER_URL = "ws://localhost:8765"

async def debug_test():
    # Join
    ws = await websockets.connect(SERVER_URL)
    join_msg = {"type": "join", "name": "DebugPlayer"}
    await ws.send(json.dumps(join_msg))
    
    # Wait for welcome
    welcome = json.loads(await ws.recv())
    pid = welcome["id"]
    print(f"Joined with ID: {pid}")
    
    # Receive first state
    state1 = json.loads(await ws.recv())
    p1 = state1["players"].get(pid, {})
    print(f"Initial state: pos=({p1.get('x', 0):.2f},{p1.get('y', 0):.2f})")
    
    # Send input
    inp = {
        "type": "input",
        "playerId": pid,
        "seq": 1,
        "input": {"up": False, "down": False, "left": False, "right": True},
    }
    await ws.send(json.dumps(inp))
    print("Sent input: move right")
    
    # Wait
    await asyncio.sleep(1.0)
    
    # Receive state
    print("Receiving next state...")
    state2 = json.loads(await asyncio.wait_for(ws.recv(), timeout=3.0))
    p2 = state2["players"].get(pid, {})
    print(f"After 1s: pos=({p2.get('x', 0):.2f},{p2.get('y', 0):.2f})")
    
    await ws.close()

if __name__ == "__main__":
    asyncio.run(debug_test())
