import sys
import time
import math

import trio

from giveaway.bot.service import chat
from giveaway.bot.service import winner
from giveaway.bot.service import announce


async def start_services():
    chat_send, chat_receive = trio.open_memory_channel(0)
    announce_send, announce_receive = trio.open_memory_channel(math.inf)

    async with trio.open_nursery() as services:
        async with chat_send, chat_receive, announce_send, announce_receive:

            services.start_soon(chat.start_service, chat_send.clone())
            services.start_soon(winner.start_service, chat_receive.clone(), announce_send.clone())
            services.start_soon(announce.start_service, announce_receive.clone())


def main():
    while True:
        try:
            trio.run(start_services)
        except KeyboardInterrupt:
            break
        except Exception as exc:
            raise
            print(exc, file=sys.stderr)
            time.sleep(60)


if __name__ == "__main__":
    main()
