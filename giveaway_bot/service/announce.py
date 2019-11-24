from functools import partial
import time
import json
import sys

import trio
from trio_websocket import serve_websocket, ConnectionClosed


end_time = time.time() + 1000


async def countdown(ws):
    while True:
        #print("announce", ws, "countdown tick", file=sys.stderr)
        await ws.send_message(json.dumps({
            "event": "tick",
            "delta": end_time - time.time(),
        }))
        await trio.sleep(1)


async def winner(ws, receive_channel):
    async with receive_channel:
        async for message in receive_channel:
            print("announce", ws, "winner", file=sys.stdout)
            await ws.send_message(json.dumps({
                "event": "winner",
                **message
            }))


async def server(request, *, receive_channel):
    ws = await request.accept()
    try:
        async with trio.open_nursery() as announcers:
            announcers.start_soon(countdown, ws)
            announcers.start_soon(winner, ws, receive_channel.clone())
    except ConnectionClosed:
        pass


async def start_service(receive_channel):
    _server = partial(server, receive_channel=receive_channel)
    await serve_websocket(_server, '127.0.0.1', 8000, ssl_context=None)
