import asyncio
import json
import time
import websockets

SERVER_URL = "ws://localhost:8765"

async def capture_test():
    # Join
    ws = await websockets.connect(SERVER_URL)
    join_msg = {"type": "join", "name": "CapturePlayer"}
    await ws.send(json.dumps(join_msg))
    
    # Wait for welcome
    welcome = json.loads(await ws.recv())
    pid = welcome["id"]
    print(f"[TEST] Joined with ID: {pid}")
    
    # Collect all states for 5 seconds and print positions
    print("[TEST] Collecting states...")
    start = time.time()
    state_count = 0
    prev_pos = None
    
    while time.time() - start < 5.0:
        try:
            msg_raw = await asyncio.wait_for(ws.recv(), timeout=0.1)
            msg = json.loads(msg_raw)
            
            if msg.get("type") == "state":
                state_count += 1
                p = msg.get("players", {}).get(pid, {})
                x, y = p.get("x"), p.get("y")
                vx, vy = p.get("vx"), p.get("vy")
                
                if (x, y) != prev_pos:
                    print(f"[STATE {state_count}] pos=({x:.2f},{y:.2f}) v=({vx:.1f},{vy:.1f})")
                    prev_pos = (x, y)
                
                # After first state, send input
                if state_count == 1:
                    inp = {
                        "type": "input",
                        "playerId": pid,
                        "seq": 1,
                        "input": {"up": False, "down": False, "left": False, "right": True},
                    }
                    await ws.send(json.dumps(inp))
                    print("[TEST] Sent input: move right")
        except asyncio.TimeoutError:
            pass
    
    print(f"[TEST] Received {state_count} state messages in 5 seconds")
    await ws.close()

if __name__ == "__main__":
    asyncio.run(capture_test())
