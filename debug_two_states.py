import asyncio
import json
import time
import math
import websockets

SERVER_URL = "ws://localhost:8765"

async def main():
    # Join two players
    ws1 = await websockets.connect(SERVER_URL)
    join_msg = {"type": "join", "name": "TestPlayer1"}
    await ws1.send(json.dumps(join_msg))
    
    # Receive welcome
    print("Waiting for welcome from player1...")
    pid1 = None
    for i in range(10):
        msg = json.loads(await asyncio.wait_for(ws1.recv(), timeout=2.0))
        print(f"  Received: type={msg.get('type')}")
        if msg.get('type') == 'welcome':
            pid1 = msg["id"]
            print(f"Player1 joined with id={pid1}")
            break
    
    # Join second player
    ws2 = await websockets.connect(SERVER_URL)
    join_msg = {"type": "join", "name": "TestPlayer2"}
    await ws2.send(json.dumps(join_msg))
    
    # Receive welcome
    print("Waiting for welcome from player2...")
    pid2 = None
    for i in range(10):
        msg = json.loads(await asyncio.wait_for(ws2.recv(), timeout=2.0))
        print(f"  Received: type={msg.get('type')}")
        if msg.get('type') == 'welcome':
            pid2 = msg["id"]
            print(f"Player2 joined with id={pid2}")
            break
    
    # Now send input from player 1
    print("\nSending input from player1...")
    t0 = time.time()
    move_right = {
        "type": "input",
        "playerId": pid1,
        "seq": 1,
        "input": {"right": True},
    }
    await ws1.send(json.dumps(move_right))
    
    # Collect states on ws1
    print("Collecting states after input on ws1...")
    p1_initial_pos = None
    state_count = 0
    for i in range(30):
        try:
            msg = json.loads(await asyncio.wait_for(ws1.recv(), timeout=0.2))
            if msg.get('type') == 'state':
                state_count += 1
                elapsed = time.time() - t0
                p1 = msg['players'][pid1]
                if p1_initial_pos is None:
                    p1_initial_pos = (p1['x'], p1['y'])
                x0, y0 = p1_initial_pos
                dist = math.sqrt((p1['x']-x0)**2 + (p1['y']-y0)**2)
                print(f"  State {state_count} (t={elapsed:.3f}s): x={p1['x']:.2f}, y={p1['y']:.2f}, dist={dist:.4f}, vx={p1['vx']:.1f}, lastSeq={p1['lastProcessedInputSeq']}", flush=True)
        except asyncio.TimeoutError:
            print(f"  Timeout - no more states")
            break
    
    print(f"\nReceived {state_count} states total")
    await ws1.close()
    await ws2.close()

asyncio.run(main())
