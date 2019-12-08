from functools import partial
import datetime
import time
import json
import sys
import ssl
import os

import pytz
import trio
from trio_websocket import serve_websocket, ConnectionClosed


PT = pytz.timezone("America/Los_Angeles")
timestamp = lambda *a, **kw: int(PT.localize(datetime.datetime(*a, **kw)).timestamp())
end_time = timestamp(2019, 12, 8, 12, 00)


tls_cert = os.environ.get("BS_WSS_TLS_CERT", "../cert.pem")
tls_key = os.environ.get("BS_WSS_TLS_KEY", "../key.pem")


announcer_sockets = [
]

last_message = None


async def countdown(ws):
    while True:
        delta = end_time - time.time()
        #print("announce", ws, "countdown tick", delta, file=sys.stderr)
        await ws.send_message(json.dumps({
            "event": "tick",
            "delta": delta if delta > 0 else 0
        }))
        await trio.sleep(1)


async def server(request):
    ws = await request.accept()
    if last_message is not None:
        await ws.send_message(json.dumps({
            "event": "winner",
            **last_message
        }))
    announcer_sockets.append(ws)
    try:
        async with trio.open_nursery() as announcers:
            announcers.start_soon(countdown, ws)
    except ConnectionClosed:
        pass


def tls_context():
    tls_context = ssl.create_default_context()
    tls_context.verify_mode = ssl.CERT_OPTIONAL
    tls_context.check_hostname = False
    tls_context.load_cert_chain(tls_cert, tls_key)
    return tls_context


async def tee(receive_channel):
    async with receive_channel:
        async for message in receive_channel:
            global last_message
            last_message = message
            if (end_time - time.time()) > 0:
                for ws in announcer_sockets:
                    print("announce", ws, "winner", file=sys.stdout)
                    try:
                        await ws.send_message(json.dumps({
                            "event": "winner",
                            **message
                        }))
                    except Exception:
                        pass


async def start_service(receive_channel):

    async with trio.open_nursery() as n:
        n.start_soon(partial(tee, receive_channel=receive_channel))
        n.start_soon(partial(serve_websocket, server, '0.0.0.0', 8443, ssl_context=tls_context()))
