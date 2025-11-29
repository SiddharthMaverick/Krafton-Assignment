import asyncio
import json
import time
import math
import websockets

async def main():
    ws = await websockets.connect('ws://localhost:8765')
    
    # Join
    join_msg = {'type': 'join', 'name': 'TestPlayer'}
    await ws.send(json.dumps(join_msg))
    
    # Get welcome
    welcome = json.loads(await ws.recv())
    pid = welcome['id']
    print(f'Joined with pid={pid}', flush=True)
    
    # Get first state
    state1 = json.loads(await asyncio.wait_for(ws.recv(), timeout=5))
    print(f'State 1: serverTime={state1["serverTime"]:.3f}, players={list(state1["players"].keys())}', flush=True)
    p1 = state1['players'][pid]
    x0, y0 = p1['x'], p1['y']
    print(f'  Player1 pos=({x0:.2f},{y0:.2f}), vx={p1["vx"]}, vy={p1["vy"]}, lastSeq={p1["lastProcessedInputSeq"]}', flush=True)
    
    # Send move right
    t0 = time.time()
    move_right = {'type': 'input', 'playerId': pid, 'seq': 1, 'input': {'right': True}}
    await ws.send(json.dumps(move_right))
    print(f'Input sent at t=0', flush=True)
    
    # Collect states
    x_prev = x0
    for i in range(30):
        try:
            state = json.loads(await asyncio.wait_for(ws.recv(), timeout=0.5))
            elapsed = time.time() - t0
            p = state['players'][pid]
            x, y = p['x'], p['y']
            dx = x - x_prev
            print(f'State {i+2} (t={elapsed:.3f}s): pos=({x:.2f},{y:.2f}), dx={dx:.4f}, vx={p["vx"]}, vy={p["vy"]}, lastSeq={p["lastProcessedInputSeq"]}', flush=True)
            x_prev = x
        except asyncio.TimeoutError:
            break
    
    await ws.close()

asyncio.run(main())
