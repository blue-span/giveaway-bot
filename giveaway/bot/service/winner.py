from binascii import hexlify
from functools import partial
from itertools import islice
from operator import itemgetter

from uuid import UUID

import h11

from giveaway.http import client
from giveaway.bot import selection
from giveaway.bot import giveaway


def as_hex(digest):
    return hexlify(digest)[:8].decode("utf-8")


async def announce(chat_recieve, send_channel, prize_vectors):
    last_digest = b'\x00' * 16

    async with chat_recieve:
        with selection.factory() as update_winner:
            async for chat_message in chat_recieve:
                current_digest = update_winner(**chat_message)

                print("last", as_hex(last_digest), "next", as_hex(current_digest))

                current_seed = selection.as_seed(current_digest)
                top5_by_prize = list(
                    map(
                        lambda vec_reg: list(islice(
                            selection.sort_winners(
                                vector_list=vec_reg,
                                seed=current_seed,
                                as_vector=itemgetter(0),
                            ),
                            5,
                        )),
                        prize_vectors
                    ),
                )

                await send_channel.send(dict(
                    last_digest=as_hex(last_digest),
                    last_seed=selection.as_seed(last_digest),
                    current_digest=as_hex(current_digest),
                    current_seed=current_seed,
                    top5_by_prize=top5_by_prize,
                    chat_message=chat_message,
                ))

                last_digest = current_digest


def prize_registrations_by_vector(prize_registrations):
    def by_vector(registration):
        vector1 = UUID(registration["registration_id"]).int
        vector2 = UUID(registration["giveaway_prize_id"]).int
        vector = vector1 ^ vector2
        return vector, registration

    return [
        list(map(by_vector, registrations))
        for registrations in prize_registrations.values()
    ]


async def start_service(chat_recieve, send_channel):
    async with client.factory("bluespan.gg", 443) as make_request:
        prize_registrations = await giveaway.json_request_factory(giveaway.get_registrations_builder, make_request)

        prize_vectors = prize_registrations_by_vector(prize_registrations)

        await announce(chat_recieve, send_channel, prize_vectors)
