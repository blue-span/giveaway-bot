from functools import partial
import time
import json
import sys
import ssl
import os

import trio
from trio_websocket import serve_websocket, ConnectionClosed


end_time = time.time() + 1000


tls_cert = os.environ.get("BS_WSS_TLS_CERT", "../cert.pem")
tls_key = os.environ.get("BS_WSS_TLS_KEY", "../key.pem")


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


def tls_context():
    tls_context = ssl.create_default_context()
    tls_context.verify_mode = ssl.CERT_OPTIONAL
    tls_context.check_hostname = False
    tls_context.load_cert_chain(tls_cert, tls_key)
    return tls_context


async def start_service(receive_channel):
    _server = partial(server, receive_channel=receive_channel)
    await serve_websocket(_server, '::', 8443, ssl_context=tls_context())
