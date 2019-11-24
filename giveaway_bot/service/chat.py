from functools import partial
import os
import sys
import json

import h11
import trio

from giveaway_bot.http import client
from giveaway_bot import oauth
from giveaway_bot import youtube


_watch_token = os.environ["BS_CHAT_WATCH_TOKEN"]
_send_token = os.environ["BS_CHAT_SEND_TOKEN"]


async def json_request_factory(request_builder, authorize, make_request):
    request_events = await authorize(request_builder)

    buf = bytearray()
    async for event in make_request(*request_events):
        if isinstance(event, h11.Response):
            response = event
            assert response.status_code == 200, response
        elif isinstance(event, h11.Data):
            data = event
            buf.extend(data.data)
        else:
            assert False, type(event)

    data = json.loads(buf)
    return data


async def chat_handler(*, live_chat_id, authorize, send_channel):
    async with client.factory("www.googleapis.com", 443) as make_request:
        async with oauth.authorizer(_send_token) as authorize_bluespangg:
            builder = partial(youtube.insert_live_chat_message_builder,
                live_chat_id=live_chat_id,
                message_text="Good morning, Mr. @Blue Span.",
            )
            await json_request_factory(builder, authorize_bluespangg, make_request)

        async def next_messages(**k):
            builder = partial(youtube.list_live_chat_messages_builder, live_chat_id=live_chat_id, **k)
            return await json_request_factory(builder, authorize, make_request)

        async def messages_generator():
            data = await next_messages()
            base_backoff = 5
            backoff = base_backoff
            while True:
                for item in iter(data["items"]):
                    backoff = 0
                    yield item

                def get_backoff():
                    nonlocal backoff
                    if backoff == 0:
                        return base_backoff * data["pollingIntervalMillis"] / 1000
                    else:
                        backoff = backoff * 2 if backoff * 2 <= 80 else 80
                        return backoff

                backoff = get_backoff()
                print("chat", "sleep", backoff)
                await trio.sleep(backoff)
                data = await next_messages(page_token=data["nextPageToken"])

        print("waiting for messages...", file=sys.stderr)
        async for message in messages_generator():
            if message["snippet"]["type"] == "textMessageEvent":
                published_at = message["snippet"]["publishedAt"]
                channel_id = message["snippet"]["authorChannelId"]
                message_text = message["snippet"]["textMessageDetails"]["messageText"]
                await send_channel.send(dict(
                    channel_id=channel_id,
                    published_at=published_at,
                    message_text=message_text,
                ))
            else:
                print("unhandled message type", message["snippet"]["type"], file=sys.stderr)


async def start_service(send_channel):
    async with oauth.authorizer(_watch_token) as authorize, \
               client.factory("www.googleapis.com", 443) as make_request, \
               send_channel:

        seen = set()

        while True:
            data = await json_request_factory(
                partial(youtube.list_live_broadcasts_builder), authorize, make_request
            )

            import pprint
            pprint.pprint(data)

            async with trio.open_nursery() as chat_handlers:
                # Make two concurrent calls to child()
                for broadcast in data["items"]:
                    if broadcast["id"] in seen:
                        print("skipping", broadcast["id"], file=sys.stderr)
                        continue
                    print("starting chat handler for broadcast", broadcast["id"], file=sys.stderr)
                    seen.add(broadcast["id"])
                    chat_handlers.start_soon(partial(
                        chat_handler,
                        live_chat_id=broadcast["snippet"]["liveChatId"],
                        authorize=authorize,
                        send_channel=send_channel,
                    ))
            await trio.sleep(60)
