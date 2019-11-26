from contextlib import contextmanager

import hashlib
import struct
import random
import time
import os
import json
import xdg


@contextmanager
def factory():
    hash = hashlib.sha256()

    dir_path = xdg.XDG_DATA_HOME
    os.makedirs(dir_path / "giveaway", exist_ok=True)
    log_path = dir_path / "giveaway" / "selection.json.log"

    with open(log_path, "a") as log_file:
        def log(event, **kwargs):
            evt = {
                "event": event,
                "data": kwargs
            }
            json.dump(evt, log_file)

        log("selection epoch", timestamp=time.time())

        def update(published_at, channel_id, message_text, **kwargs):
            log("selection update", **dict(
                published_at=published_at,
                channel_id=channel_id,
                message_text=message_text,
            ))

            hash.update(str(published_at).encode("utf-8"))
            hash.update(str(channel_id).encode("utf-8"))
            hash.update(str(message_text).encode("utf-8"))

            return hash.digest()

        yield update


def as_seed(digest: bytes):
    upper, lower = struct.unpack(
        ">QQ", digest[:16],
    )
    seed = (upper << 64) + lower
    return seed


def sort_winners(vector_list, seed, as_vector):
    return sorted(vector_list, key=lambda vector_ish: abs(seed - as_vector(vector_ish)))
