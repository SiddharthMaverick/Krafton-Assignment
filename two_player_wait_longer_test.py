import asyncio
import json
import time
import websockets

SERVER_URL = "ws://localhost:8765"

async def two_player_wait_longer_test():
    # Join player 1
    ws1 = await websockets.connect(SERVER_URL)
    join_msg = {"type": "join", "name": "Player1"}
    await ws1.send(json.dumps(join_msg))
    welcome1 = json.loads(await ws1.recv())
    pid1 = welcome1["id"]
    print(f"[P1] Joined: {pid1[:8]}")
    
    # Join player 2
    ws2 = await websockets.connect(SERVER_URL)
    join_msg = {"type": "join", "name": "Player2"}
    await ws2.send(json.dumps(join_msg))
    welcome2 = json.loads(await ws2.recv())
    pid2 = welcome2["id"]
    print(f"[P2] Joined: {pid2[:8]}")
    
    # Get initial state from player 1
    state1 = json.loads(await ws1.recv())
    p1_state = state1.get("players", {}).get(pid1, {})
    print(f"[P1] Initial: pos=({p1_state.get('x'):.2f},{p1_state.get('y'):.2f})")
    
    # Send input
    inp = {"type": "input", "playerId": pid1, "seq": 1, "input": {"right": True}}
    print("[P1] Sent input")
    await ws1.send(json.dumps(inp))
    
    # Wait and collect multiple states
    print("[P1] Collecting states for 3 seconds...")
    for i in range(10):
        try:
            state = json.loads(await asyncio.wait_for(ws1.recv(), timeout=0.5))
            p1 = state.get("players", {}).get(pid1, {})
            print(f"[STATE] pos=({p1.get('x'):.2f},{p1.get('y'):.2f}), vx={p1.get('vx'):.1f}, seq={p1.get('lastProcessedInputSeq')}")
        except asyncio.TimeoutError:
            print("[TIMEOUT]")
            break
    
    await ws1.close()
    await ws2.close()

if __name__ == "__main__":
    asyncio.run(two_player_wait_longer_test())
