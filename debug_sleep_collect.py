#!/usr/bin/env python3
import asyncio
import json
import time
import websockets

SERVER_URL = "ws://localhost:8765"

async def recv_with_timeout(ws, timeout):
    end = time.time() + timeout
    msgs = []
    while time.time() < end:
        remaining = end - time.time()
        try:
            raw = await asyncio.wait_for(ws.recv(), timeout=remaining)
        except asyncio.TimeoutError:
            break
        try:
            msgs.append(json.loads(raw))
        except Exception:
            continue
    return msgs

async def main():
    ws1 = await websockets.connect(SERVER_URL)
    await ws1.send(json.dumps({"type":"join","name":"S1"}))
    welcome = await ws1.recv()
    wid1 = json.loads(welcome)["id"]
    print(f"P1 id={wid1}")

    ws2 = await websockets.connect(SERVER_URL)
    await ws2.send(json.dumps({"type":"join","name":"S2"}))
    welcome = await ws2.recv()
    wid2 = json.loads(welcome)["id"]
    print(f"P2 id={wid2}")

    # wait for a state
    while True:
        raw = await ws1.recv()
        msg = json.loads(raw)
        if msg.get("type") == "state":
            initial = msg
            break
    p0 = initial['players'][wid1]
    print(f"Initial: x={p0['x']:.4f}, lastSeq={p0['lastProcessedInputSeq']}")

    # send input
    await ws1.send(json.dumps({"type":"input","playerId":wid1,"seq":1,"input":{"up":False,"down":False,"left":False,"right":True}}))
    print("Sent input seq=1; now sleeping 1s without reading")

    # Sleep for 1 second without reading websocket
    await asyncio.sleep(1.0)

    # Now drain any messages
    msgs = []
    try:
        while True:
            raw = await asyncio.wait_for(ws1.recv(), timeout=0.1)
            msgs.append(json.loads(raw))
    except asyncio.TimeoutError:
        pass

    states = [m for m in msgs if m.get('type')=='state']
    print(f"After 1s sleep, received {len(states)} state messages")
    if states:
        last = states[-1]['players'][wid1]
        print(f"Last state: x={last['x']:.4f}, lastSeq={last['lastProcessedInputSeq']}, vx={last['vx']:.2f}")
        print(f"First state during drain: x={states[0]['players'][wid1]['x']:.4f}, lastSeq={states[0]['players'][wid1]['lastProcessedInputSeq']}")
    else:
        print("No states received after sleep")

    await ws1.close()
    await ws2.close()

asyncio.run(main())
