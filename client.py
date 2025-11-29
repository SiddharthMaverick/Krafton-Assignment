# client.py
import asyncio
import json
import sys
import time
import websockets

SERVER_URL = "ws://localhost:8765"

# Important:
# We already simulate 200 ms latency on the SERVER (both directions),
# so keep client latency = 0.0 to avoid over-delaying everything.
ARTIFICIAL_LATENCY = 0.0


class ClientGame:
    def __init__(self, name: str = "Player"):
        self.name = name
        self.player_id: str | None = None
        self.seq: int = 0
        self.current_input = {
            "up": False,
            "down": False,
            "left": False,
            "right": False,
        }
        # Raw state replicated from server snapshots
        self.players: dict[str, dict] = {}
        self.coins: list[dict] = []

    async def send_with_latency(self, ws, msg: dict):
        """Optionally simulate outbound latency from client to server."""
        if ARTIFICIAL_LATENCY > 0.0:
            await asyncio.sleep(ARTIFICIAL_LATENCY)
        await ws.send(json.dumps(msg))

    async def input_loop(self, ws):
        """
        Simple text input:
          w/a/s/d -> move
          stop    -> stop movement
          q       -> quit
        """
        print("Controls: w/a/s/d + Enter, 'stop' to stop, 'q' to quit\n")
        loop = asyncio.get_event_loop()

        while True:
            # Run blocking stdin read in a thread so we don't block the event loop
            line = await loop.run_in_executor(None, sys.stdin.readline)
            if not line:
                continue

            line = line.strip().lower()

            if line == "q":
                print("Quitting client...")
                await ws.close()
                break

            if line == "stop":
                # Stop movement in all directions
                self.current_input = {
                    "up": False,
                    "down": False,
                    "left": False,
                    "right": False,
                }
            else:
                # Last key pressed sets current direction (4-way movement)
                up = (line == "w")
                down = (line == "s")
                left = (line == "a")
                right = (line == "d")

                if not any([up, down, left, right]):
                    print("Unknown input. Use w/a/s/d, 'stop', or 'q'.")
                    continue

                self.current_input = {
                    "up": up,
                    "down": down,
                    "left": left,
                    "right": right,
                }

            # Increment input sequence and send to server
            self.seq += 1
            if self.player_id is not None:
                msg = {
                    "type": "input",
                    "playerId": self.player_id,
                    "seq": self.seq,
                    "input": self.current_input,
                }
                await self.send_with_latency(ws, msg)
            else:
                # We haven't received our welcome/id yet
                print("Waiting for welcome from server, input not sent yet.")

    def print_state(self):
        """Pretty-print latest state snapshot from the authoritative server."""
        print("\n=== GAME STATE @", time.strftime("%H:%M:%S"), "=== ")
        if not self.players:
            print("No players yet.")
        for pid, p in self.players.items():
            me = "(YOU)" if pid == self.player_id else ""
            name = p.get("name", "Player")
            x = p.get("x", 0.0)
            y = p.get("y", 0.0)
            score = p.get("score", 0)
            print(f"{name} {me} | pos=({x:.2f},{y:.2f}) | score={score}")

        print(f"Coins: {len(self.coins)}")
        # Show at most first 5 coins to avoid spam
        for c in self.coins[:5]:
            cid_short = c.get("id", "")[:6]
            cx = c.get("x", 0.0)
            cy = c.get("y", 0.0)
            print(f"  coin {cid_short} @ ({cx:.1f},{cy:.1f})")
        print("====================================\n")

    async def run(self):
        async with websockets.connect(SERVER_URL) as ws:
            # Send join request
            join_msg = {"type": "join", "name": self.name}
            await self.send_with_latency(ws, join_msg)

            # Start reading keyboard input in parallel
            asyncio.create_task(self.input_loop(ws))

            # Listen for server messages
            async for raw in ws:
                if ARTIFICIAL_LATENCY > 0.0:
                    await asyncio.sleep(ARTIFICIAL_LATENCY)  # optional inbound latency

                try:
                    msg = json.loads(raw)
                except json.JSONDecodeError:
                    continue

                mtype = msg.get("type")
                if mtype == "welcome":
                    self.player_id = msg.get("id")
                    print(f"[CLIENT] Joined as {self.name}, id={self.player_id}")

                elif mtype == "state":
                    # Fully overwrite local replicated state
                    self.players = msg.get("players", {}) or {}
                    self.coins = msg.get("coins", []) or []
                    self.print_state()


if __name__ == "__main__":
    name = "Player"
    if len(sys.argv) > 1:
        name = sys.argv[1]

    game = ClientGame(name=name)
    asyncio.run(game.run())
