import asyncio
import json
import time
import websockets

SERVER_URL = "ws://localhost:8765"

async def two_player_test():
    # Join player 1
    ws1 = await websockets.connect(SERVER_URL)
    join_msg = {"type": "join", "name": "Player1"}
    await ws1.send(json.dumps(join_msg))
    welcome1 = json.loads(await ws1.recv())
    pid1 = welcome1["id"]
    print(f"[TEST] Player 1 joined: {pid1[:8]}")
    
    # Join player 2
    ws2 = await websockets.connect(SERVER_URL)
    join_msg = {"type": "join", "name": "Player2"}
    await ws2.send(json.dumps(join_msg))
    welcome2 = json.loads(await ws2.recv())
    pid2 = welcome2["id"]
    print(f"[TEST] Player 2 joined: {pid2[:8]}")
    
    # Get initial states
    state1 = json.loads(await ws1.recv())
    p1_initial = state1.get("players", {}).get(pid1, {})
    print(f"[TEST] Player 1 initial pos: ({p1_initial.get('x'):.2f},{p1_initial.get('y'):.2f})")
    
    # Send input from player 1
    inp = {
        "type": "input",
        "playerId": pid1,
        "seq": 1,
        "input": {"up": False, "down": False, "left": False, "right": True},
    }
    await ws1.send(json.dumps(inp))
    print("[TEST] Player 1 sent input: move right")
    
    # Wait
    await asyncio.sleep(1.0)
    print("[TEST] Waited 1 second")
    
    # Get next state from player 1
    state2 = json.loads(await asyncio.wait_for(ws1.recv(), timeout=3.0))
    p1_after = state2.get("players", {}).get(pid1, {})
    print(f"[TEST] Player 1 after input: ({p1_after.get('x'):.2f},{p1_after.get('y'):.2f})")
    
    await ws1.close()
    await ws2.close()

if __name__ == "__main__":
    asyncio.run(two_player_test())
