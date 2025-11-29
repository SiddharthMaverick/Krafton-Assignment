#!/usr/bin/env python3
import asyncio
import json
import websockets
import time
import sys

async def test():
    uri = "ws://localhost:8765"
    
    # Connect player 1
    async with websockets.connect(uri) as ws1:
        print("[P1] Connected")
        await ws1.send(json.dumps({"type": "join", "name": "P1"}))
        msg = await ws1.recv()
        p1_data = json.loads(msg)
        p1_id = p1_data["id"]
        print(f"[P1] Joined with id={p1_id}")
        
        # Connect player 2
        async with websockets.connect(uri) as ws2:
            print("[P2] Connected")
            await ws2.send(json.dumps({"type": "join", "name": "P2"}))
            msg = await ws2.recv()
            p2_data = json.loads(msg)
            p2_id = p2_data["id"]
            print(f"[P2] Joined with id={p2_id}")
            
            # Get initial state
            print("\n[P1] Waiting for state...")
            state = await ws1.recv()
            state_data = json.loads(state)
            print(f"[P1] Got state with {len(state_data['players'])} players")
            p1_initial = state_data['players'][p1_id]
            print(f"[P1] Initial: x={p1_initial['x']:.2f}, y={p1_initial['y']:.2f}, lastSeq={p1_initial['lastProcessedInputSeq']}")
            
            # Send move right input
            print(f"\n[P1] Sending move_right input (seq=1)")
            await ws1.send(json.dumps({
                "type": "input",
                "playerId": p1_id,
                "seq": 1,
                "input": {"up": False, "down": False, "left": False, "right": True}
            }))
            
            # Now read 20 states and dump detailed info
            print("\n[P1] Reading 20 states:")
            for i in range(20):
                state = await ws1.recv()
                state_data = json.loads(state)
                p1_state = state_data['players'][p1_id]
                print(f"  State {i+1}: x={p1_state['x']:.4f}, vx={p1_state['vx']:.2f}, lastSeq={p1_state['lastProcessedInputSeq']}, time={state_data['serverTime']:.3f}")
                
                if i == 0:
                    first_time = state_data['serverTime']
                    first_pos = p1_state['x']
                
            print(f"\n[P1] After 20 states:")
            print(f"  First pos:  {first_pos:.4f}")
            print(f"  Final pos:  {p1_state['x']:.4f}")
            print(f"  Distance:   {p1_state['x'] - first_pos:.4f}")
            print(f"  Expected:   ~5.0 units/sec (0.25 per tick)")

if __name__ == "__main__":
    asyncio.run(test())
