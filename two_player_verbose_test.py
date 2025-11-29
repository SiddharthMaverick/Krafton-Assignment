import asyncio
import json
import time
import websockets

SERVER_URL = "ws://localhost:8765"

async def two_player_verbose_test():
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
    print("[P1] Waiting for initial state...")
    state1 = json.loads(await ws1.recv())
    p1_state = state1.get("players", {}).get(pid1, {})
    print(f"[P1] State received: pos=({p1_state.get('x'):.2f},{p1_state.get('y'):.2f}), seq={p1_state.get('lastProcessedInputSeq')}")
    print(f"[P1] All players in state: {list(state1.get('players', {}).keys())}")
    
    # Send input
    inp = {
        "type": "input",
        "playerId": pid1,
        "seq": 1,
        "input": {"right": True},
    }
    print("[P1] Sending input...")
    await ws1.send(json.dumps(inp))
    
    # Wait
    print("[P1] Waiting 1 second...")
    await asyncio.sleep(1.0)
    
    # Get next state
    print("[P1] Receiving next state...")
    try:
        state2 = json.loads(await asyncio.wait_for(ws1.recv(), timeout=3.0))
        p1_new = state2.get("players", {}).get(pid1, {})
        print(f"[P1] New state: pos=({p1_new.get('x'):.2f},{p1_new.get('y'):.2f}), seq={p1_new.get('lastProcessedInputSeq')}")
        print(f"[P1] Velocity: ({p1_new.get('vx'):.1f},{p1_new.get('vy'):.1f})")
    except asyncio.TimeoutError:
        print("[P1] TIMEOUT waiting for state!")
    
    await ws1.close()
    await ws2.close()

if __name__ == "__main__":
    asyncio.run(two_player_verbose_test())
