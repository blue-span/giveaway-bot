from functools import partial
import h11
import trio
import client


def gateway_bot():
    request = h11.Request(
        method="GET",
        target="/api/gateway/bot",
        headers=[
            ("host", "discordapp.com"),
            ("content-length", "0"),
            ("authorization", "Bot ")
        ])
    return request


async def main():
    async with client.factory("discordapp.com", 443) as make_request:
        async for event in make_request(gateway_bot()):
            response = next(event)
            assert response.status_code==200
            data = next(event)
            assert next(event, None) is None

            body = json.loads(data.data)


trio.run(main)


"https://discordapp.com/api"
"""
{
  "url": "wss://gateway.discord.gg/",
  "shards": 9,
  "session_start_limit": {
    "total": 1000,
    "remaining": 999,
    "reset_after": 14400000
  }
}
"""
