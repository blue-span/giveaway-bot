import json
import os

import h11


_token = os.environ["BS_TOKEN"]


async def json_request_factory(request_builder, make_request):
    buf = bytearray()
    request_events = request_builder()
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


def get_registrations_builder():
    request = h11.Request(
        method="GET",
        target="/giveaway/winner",
        headers=[
            ("host", "bluespan.gg"),
            ("authorization", _token)
        ]
    )
    return request,
