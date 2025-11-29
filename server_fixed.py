# server.py
import asyncio
import json
import random
import time
import uuid
import websockets

TICK_RATE = 20  # 20 Hz
DT = 1.0 / TICK_RATE
MAP_WIDTH = 20
MAP_HEIGHT = 10
PLAYER_SPEED = 5.0
COIN_COUNT = 5
PICKUP_RADIUS = 1.0
ARTIFICIAL_LATENCY = 0.2  # seconds in both directions


class Player:
    def __init__(self, pid, name):
        self.id = pid
        self.name = name
        self.x = random.uniform(0, MAP_WIDTH)
        self.y = random.uniform(0, MAP_HEIGHT)
        self.vx = 0.0
        self.vy = 0.0
        self.score = 0
        self.last_input = {"up": False, "down": False, "left": False, "right": False}
        self.last_seq = 0


class Coin:
    def __init__(self, cid):
        self.id = cid
        self.x = random.uniform(0, MAP_WIDTH)
        self.y = random.uniform(0, MAP_HEIGHT)


class GameServer:
    def __init__(self):
        # websocket -> player_id
        self.clients: dict[websockets.WebSocketServerProtocol, str] = {}
        # player_id -> websocket
        self.client_by_id: dict[str, websockets.WebSocketServerProtocol] = {}
        self.players: dict[str, Player] = {}  # id -> Player
        self.coins: dict[str, Coin] = {}      # id -> Coin
        self.running = False

    async def send_with_latency(self, ws, msg: dict):
        """Simulate outbound latency."""
        await asyncio.sleep(ARTIFICIAL_LATENCY)
        await ws.send(json.dumps(msg))

    async def broadcast_state(self):
        """Send full state to all clients."""
        if not self.clients:
            return

        state = {
            "type": "state",
            "serverTime": time.time(),
            "players": {
                pid: {
                    "id": p.id,
                    "name": p.name,
                    "x": p.x,
                    "y": p.y,
                    "vx": p.vx,
                    "vy": p.vy,
                    "score": p.score,
                    "lastProcessedInputSeq": p.last_seq,
                }
                for pid, p in self.players.items()
            },
            "coins": [
                {"id": c.id, "x": c.x, "y": c.y}
                for c in self.coins.values()
            ],
        }

        # Send concurrently to all connected clients
        await asyncio.gather(
            *[self.send_with_latency(ws, state) for ws in list(self.clients.keys())],
            return_exceptions=True,
        )

    def ensure_coins(self):
        """Make sure there are always COIN_COUNT coins on the map."""
        while len(self.coins) < COIN_COUNT:
            cid = str(uuid.uuid4())
            self.coins[cid] = Coin(cid)

    def apply_inputs(self):
        """Convert last input per player into velocities."""
        for p in self.players.values():
            inp = p.last_input
            dx = float(inp.get("right", False)) - float(inp.get("left", False))
            dy = float(inp.get("down", False)) - float(inp.get("up", False))
            p.vx = dx * PLAYER_SPEED
            p.vy = dy * PLAYER_SPEED

    def integrate(self):
        """Integrate positions using velocities."""
        for p in self.players.values():
            p.x += p.vx * DT
            p.y += p.vy * DT
            # clamp to map
            p.x = max(0.0, min(MAP_WIDTH, p.x))
            p.y = max(0.0, min(MAP_HEIGHT, p.y))

    def handle_collisions(self):
        """Check player–coin collisions and update scores."""
        to_remove = []
        for cid, c in self.coins.items():
            for p in self.players.values():
                dx = p.x - c.x
                dy = p.y - c.y
                dist_sq = dx * dx + dy * dy
                if dist_sq <= PICKUP_RADIUS * PICKUP_RADIUS:
                    p.score += 1
                    to_remove.append(cid)
                    break
        for cid in to_remove:
            self.coins.pop(cid, None)

    async def game_loop(self):
        """Main game loop: fixed tick, broadcast snapshots."""
        self.running = True
        last_time = time.time()
        print("[SERVER] Game loop started", flush=True)
        while True:
            now = time.time()
            elapsed = now - last_time
            if elapsed < DT:
                await asyncio.sleep(DT - elapsed)
                continue
            last_time = now

            self.apply_inputs()
            self.integrate()
            self.handle_collisions()
            self.ensure_coins()
            await self.broadcast_state()

    async def handle_client(self, websocket):
        """Handle one client connection."""
        async for raw in websocket:
            try:
                msg = json.loads(raw)
            except json.JSONDecodeError:
                continue

            mtype = msg.get("type")
            if mtype == "join":
                name = msg.get("name", "Player")
                pid = str(uuid.uuid4())
                player = Player(pid, name)
                self.players[pid] = player
                self.clients[websocket] = pid
                self.client_by_id[pid] = websocket

                welcome = {"type": "welcome", "id": pid, "name": name}
                await self.send_with_latency(websocket, welcome)

                print(f"[SERVER] Player joined: {name} ({pid})", flush=True)

                # Start the game loop after the first player joins
                if not self.running:
                    asyncio.create_task(self.game_loop())

            elif mtype == "input":
                pid = msg.get("playerId")
                seq = msg.get("seq", 0)
                inp = msg.get("input", {})
                player = self.players.get(pid)
                if player is None:
                    continue
                # Ignore older inputs
                if seq <= player.last_seq:
                    continue
                player.last_seq = seq
                # Normalize keys
                player.last_input = {
                    "up": bool(inp.get("up", False)),
                    "down": bool(inp.get("down", False)),
                    "left": bool(inp.get("left", False)),
                    "right": bool(inp.get("right", False)),
                }

    async def on_disconnect(self, websocket):
        """Cleanup when a client disconnects."""
        pid = self.clients.get(websocket)
        if pid:
            print(f"[SERVER] Player disconnected: {pid}", flush=True)
            self.clients.pop(websocket, None)
            self.client_by_id.pop(pid, None)
            self.players.pop(pid, None)


async def main():
    server = GameServer()

    async def handler(ws):
        try:
            await server.handle_client(ws)
        except websockets.exceptions.ConnectionClosed:
            pass
        finally:
            await server.on_disconnect(ws)

    print("Starting server on ws://localhost:8765", flush=True)
    async with websockets.serve(handler, "localhost", 8765):
        await asyncio.Future()  # run forever


if __name__ == "__main__":
    asyncio.run(main())
