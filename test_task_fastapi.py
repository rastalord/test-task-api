import asyncio
import logging
import signal
import time
from typing import Set

from fastapi import FastAPI, WebSocket, WebSocketDisconnect

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)

app = FastAPI()

# Global State
active_connections: Set[WebSocket] = set()
shutdown_event = asyncio.Event()
shutdown_initiated = False
shutdown_start_time: float | None = None
MAX_SHUTDOWN_WAIT = 30 * 60  # 30 minutes


# connection establishing and connection actions
async def connect(websocket: WebSocket):
    await websocket.accept()
    active_connections.add(websocket)
    logging.info(f"client connected. Active connections: {len(active_connections)}")


async def disconnect(websocket: WebSocket):
    active_connections.discard(websocket)
    logging.info(f"client disconnected. Active connections: {len(active_connections)}")


async def broadcast(message: str):
    disconnected = []
    for connection in active_connections:
        try:
            await connection.send_text(message)
        except Exception:
            disconnected.append(connection)

    for conn in disconnected:
        await disconnect(conn)


# websocket endpoint
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except Web_socket_disconnect:
        await disconnect(websocket)
    except Exception:
        await disconnect(websocket)


# background notification
async def notification_loop():
    while not shutdown_event.is_set():
        await asyncio.sleep(10)
        if active_connections:
            logging.info("Sending test notification to clients...")
            await broadcast("Test notification from server")


# graceful shutdown
async def wait_for_shutdown():
    global shutdown_start_time

    shutdown_start_time = time.time()
    logging.info("Shutdown signal received. Waiting for connections to close...")

    while True:
        elapsed = time.time() - shutdown_start_time
        remaining = MAX_SHUTDOWN_WAIT - elapsed

        logging.info(
            f"Shutdown progress: {len(active_connections)} active connections, "
            f"{int(remaining)} seconds remaining"
        )

        if not active_connections:
            logging.info("All clients disconnected. Shutting down immediately.")
            break

        if elapsed >= MAX_SHUTDOWN_WAIT:
            logging.warning("Shutdown timeout reached. Forcing shutdown.")
            break

        await asyncio.sleep(5)

    shutdown_event.set()


def handle_signal():
    global shutdown_initiated
    if not shutdown_initiated:
        shutdown_initiated = True
        asyncio.create_task(wait_for_shutdown())


# FastAPI events
@app.on_event("startup")
async def startup_event():
    logging.info("Server started")

    loop = asyncio.get_running_loop()

    # Register signal handlers (only in main thread)
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, handle_signal)
        except NotImplementedError:
            # Windows fallback
            signal.signal(sig, lambda s, f: handle_signal())

    asyncio.create_task(notification_loop())


@app.on_event("shutdown")
async def shutdown_event_handler():
    logging.info("Shutdown complete.")

# runnable with uvicorn main:app --workers 1
