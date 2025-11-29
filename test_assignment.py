import asyncio
import json
import time
import math

import websockets

SERVER_URL = "ws://localhost:8765"

# These should roughly match server constants
PLAYER_SPEED = 5.0
TICK_RATE = 20
DT = 1.0 / TICK_RATE
PICKUP_RADIUS = 1.0


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


async def test_two_players_present(ws, pid1, pid2, timeout=5.0):
    print("\n[TEST] Checking that two players appear in server state...")

    start = time.time()
    last_players = {}
    while time.time() - start < timeout:
        state = await wait_for_state(ws, timeout=1.0)
        if not state:
            continue

        players = state.get("players", {}) or {}
        last_players = players
        if pid1 in players and pid2 in players:
            print("[PASS] Both players are present in server snapshots.")
            return

    raise AssertionError(
        f"[FAIL] Both players not found in state within {timeout}s.\n"
        f"Last players keys: {list(last_players.keys())}"
    )


async def test_movement(ws, player_id):
    print("\n[TEST] Checking that movement input changes player position...")

    # Get initial state
    state = await wait_for_state(ws, timeout=3.0)
    assert state is not None, "[FAIL] No state for movement test."

    p = get_player_from_state(state, player_id)
    assert p is not None, "[FAIL] Player not found in state for movement test."
    x0, y0 = p["x"], p["y"]

    # Send a single "move right" input
    seq = 1
    move_right = {
        "type": "input",
        "playerId": player_id,
        "seq": seq,
        "input": {"up": False, "down": False, "left": False, "right": True},
    }
    await ws.send(json.dumps(move_right))

    # Wait some time for motion to accumulate
    await asyncio.sleep(1.0)

    # Receive a new state
    state2 = await wait_for_state(ws, timeout=3.0)
    assert state2 is not None, "[FAIL] No second state for movement test."

    p2 = get_player_from_state(state2, player_id)
    assert p2 is not None, "[FAIL] Player not found in second state for movement test."
    x1, y1 = p2["x"], p2["y"]

    dx = x1 - x0
    dy = y1 - y0
    dist = math.sqrt(dx * dx + dy * dy)

    print(f"[TEST] Position changed from ({x0:.2f},{y0:.2f}) to ({x1:.2f},{y1:.2f}), dist={dist:.2f}")
    assert dist > 0.5, "[FAIL] Player did not move enough after input."
    print("[PASS] Movement input correctly changes player position (authoritative server updates).")


async def test_coin_collection(ws, player_id):
    print("\n[TEST] Checking that player can collect a coin and score increases...")

    # Get initial state
    state = await wait_for_state(ws, timeout=3.0)
    assert state is not None, "[FAIL] No state for coin test."

    p = get_player_from_state(state, player_id)
    assert p is not None, "[FAIL] Player not found in state for coin test."

    initial_score = p["score"]
    px, py = p["x"], p["y"]

    coins = state.get("coins", []) or []
    assert coins, "[FAIL] No coins present in world."

    # Choose the first coin as target
    target = coins[0]
    cx, cy = target["x"], target["y"]
    print(f"[TEST] Moving from ({px:.2f},{py:.2f}) towards coin at ({cx:.2f},{cy:.2f}) with initial score={initial_score}")

    # Try to walk towards the coin, adjusting direction each few snapshots
    seq = 100  # start seq high to clearly be "new"
    start_time = time.time()
    timeout = 8.0  # seconds

    while time.time() - start_time < timeout:
        # Refresh state
        state = await wait_for_state(ws, timeout=1.0)
        if not state:
            continue

        p = get_player_from_state(state, player_id)
        if not p:
            continue

        score = p["score"]
        if score > initial_score:
            print(f"[PASS] Score increased from {initial_score} to {score} after approaching coin.")
            return

        px, py = p["x"], p["y"]

        # Recompute direction towards original coin coordinate
        dir_x = cx - px
        dir_y = cy - py

        # If we are close enough but score not increased yet, just wait more
        dist_to_coin = math.sqrt(dir_x * dir_x + dir_y * dy if (dy := dir_y) else dir_y * dir_y)
        # Above line to avoid Pylance complaining; logically it's dist^2 = dx^2+dy^2 then sqrt.
        dist_to_coin = math.sqrt(dir_x * dir_x + dir_y * dir_y)
        if dist_to_coin < PICKUP_RADIUS + 0.5:
            print(f"[TEST] Close to coin (dist={dist_to_coin:.2f}), waiting for pickup...")
            await asyncio.sleep(0.5)
            continue

        # Set directional inputs
        right = dir_x > 0.1
        left = dir_x < -0.1
        down = dir_y > 0.1
        up = dir_y < -0.1

        seq += 1
        inp = {
            "type": "input",
            "playerId": player_id,
            "seq": seq,
            "input": {"up": up, "down": down, "left": left, "right": right},
        }
        await ws.send(json.dumps(inp))
        await asyncio.sleep(0.2)  # allow some ticks

    raise AssertionError("[FAIL] Timed out trying to collect a coin and increase score.")


async def test_anti_cheat_basic(ws, player_id):
    """
    Basic authority sanity check:
    - Send an 'old' input with lower sequence number and verify it doesn't break state.
    """
    print("\n[TEST] Checking basic anti-cheat / authority behavior (old input ignored)...")

    # Get baseline state & last seq from server view (if any)
    state = await wait_for_state(ws, timeout=3.0)
    assert state is not None, "[FAIL] No state for anti-cheat test."
    p = get_player_from_state(state, player_id)
    assert p is not None, "[FAIL] Player not found in anti-cheat test."

    last_seq_server = p.get("lastProcessedInputSeq", 0)

    # Send an obviously "old" input
    old_seq = max(0, last_seq_server - 10)
    cheat_input = {
        "type": "input",
        "playerId": player_id,
        "seq": old_seq,
        "input": {"up": True, "down": False, "left": False, "right": False},
    }
    await ws.send(json.dumps(cheat_input))

    # Wait and get another state
    await asyncio.sleep(0.5)
    state2 = await wait_for_state(ws, timeout=3.0)
    assert state2 is not None, "[FAIL] No state after anti-cheat attempt."
    p2 = get_player_from_state(state2, player_id)
    assert p2 is not None, "[FAIL] Player missing after anti-cheat attempt."

    new_last_seq = p2.get("lastProcessedInputSeq", 0)

    # The server should not roll back lastProcessedInputSeq to the old one
    assert new_last_seq >= last_seq_server, (
        f"[FAIL] lastProcessedInputSeq went backwards ({last_seq_server} -> {new_last_seq}), "
        "server accepted old/cheat input."
    )
    print("[PASS] Old input ignored / sequence number not rolled back (basic authority check).")


async def main():
    print("[TEST] Make sure server is running at ws://localhost:8765 before running this.")

    # 1) Join two players
    ws1, pid1 = await join_player("TestPlayer1")
    ws2, pid2 = await join_player("TestPlayer2")

    try:
        # 2) Two players present in state (robust check)
        await test_two_players_present(ws1, pid1, pid2)

        # 3) Movement test (authoritative server updates)
        await test_movement(ws1, pid1)

        # 4) Coin collection & score increase
        await test_coin_collection(ws1, pid1)

        # 5) Basic anti-cheat / authority check
        await test_anti_cheat_basic(ws1, pid1)

        print("\n✅ ALL TESTS PASSED (for the parts this script checks).\n")

    finally:
        await ws1.close()
        await ws2.close()


if __name__ == "__main__":
    asyncio.run(main())
