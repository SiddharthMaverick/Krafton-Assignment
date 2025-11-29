import asyncio
import json
import time
import math
import websockets

SERVER_URL = "ws://localhost:8765"

PLAYER_SPEED = 5.0
TICK_RATE = 20
DT = 1.0 / TICK_RATE

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


async def join_player(name: str):
    """Connect a websocket and join as a given player name. Return (ws, player_id)."""
    ws = await websockets.connect(SERVER_URL)
    join_msg = {"type": "join", "name": name}
    await ws.send(json.dumps(join_msg))

    # Wait for welcome
    welcome = await recv_until_type(ws, "welcome", timeout=3.0)
    if not welcome:
        raise RuntimeError(f"[TEST] Did not receive welcome for {name}")
    pid = welcome.get("id")
    print(f"[TEST] {name} joined with id={pid}")
    return ws, pid


def get_player_from_state(state: dict, player_id: str):
    players = state.get("players", {}) or {}
    return players.get(player_id)


async def test_two_players():
    print("\n[TEST] Joining two players...")
    ws1, pid1 = await join_player("TestPlayer1")
    ws2, pid2 = await join_player("TestPlayer2")
    
    # Wait for both to appear
    print("[TEST] Waiting for both players in state...")
    await asyncio.sleep(1.0)
    
    state = await wait_for_state(ws1, timeout=3.0)
    print(f"[TEST] Got state with {len(state.get('players', {}))} players")
    
    print(f"\n[TEST] Testing movement on player 1...")
    # Get initial state
    state1 = await wait_for_state(ws1, timeout=3.0)
    assert state1 is not None
    p1 = get_player_from_state(state1, pid1)
    assert p1 is not None
    x0, y0 = p1["x"], p1["y"]
    print(f"[TEST] Initial position: ({x0:.2f},{y0:.2f}), lastSeq={p1['lastProcessedInputSeq']}")
    
    # Send move right input
    seq = 1
    move_right = {
        "type": "input",
        "playerId": pid1,
        "seq": seq,
        "input": {"up": False, "down": False, "left": False, "right": True},
    }
    print(f"[TEST] About to send: {json.dumps(move_right)}")
    await ws1.send(json.dumps(move_right))
    print(f"[TEST] Sent move_right input")
    
    # Wait 1 second
    await asyncio.sleep(1.0)
    print(f"[TEST] Waited 1 second, now getting state...")
    
    # Get new state
    state2 = await wait_for_state(ws1, timeout=3.0)
    assert state2 is not None
    p2 = get_player_from_state(state2, pid1)
    assert p2 is not None
    x1, y1 = p2["x"], p2["y"]
    print(f"[TEST] Final position: ({x1:.2f},{y1:.2f}), lastSeq={p2['lastProcessedInputSeq']}")
    
    # DEBUG: Keep reading more states to see what's coming
    print(f"[TEST] DEBUG: Reading more states...")
    for i in range(10):
        try:
            s = await wait_for_state(ws1, timeout=0.5)
            if s:
                p = get_player_from_state(s, pid1)
                print(f"  State {i+1}: x={p['x']:.2f}, lastSeq={p['lastProcessedInputSeq']}")
        except:
            break
    
    dx = x1 - x0
    dy = y1 - y0
    dist = math.sqrt(dx * dx + dy * dy)
    print(f"[TEST] Movement: dx={dx:.4f}, dy={dy:.4f}, dist={dist:.4f}")
    
    if dist > 0.5:
        print("[PASS] Movement test passed!")
    else:
        print("[FAIL] Movement test failed - distance too small!")
        
    await ws1.close()
    await ws2.close()

async def main():
    await test_two_players()

asyncio.run(main())
