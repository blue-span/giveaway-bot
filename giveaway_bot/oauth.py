from contextlib import asynccontextmanager
from urllib import parse
import h11
import json
import time
import sys
import os

from giveaway_bot.http import client


_client_id = os.environ["BS_CLIENT_ID"]
_client_secret = os.environ["BS_CLIENT_SECRET"]


def auth_rf():
    request = h11.Request(
        method="GET",
        target="/o/oauth2/v2/auth?" + parse.urlencode({
            "client_id": _client_id,
            "redirect_uri": "urn:ietf:wg:oauth:2.0:oob",
            "response_type": "code",
            "scope": " ".join([
                "https://www.googleapis.com/auth/youtube",
                "https://www.googleapis.com/auth/youtubepartner",
            ]),
        }),
        headers=[
            ("host", "accounts.google.com"),
            ("content-length", "0")
        ])
    return request


def token_rf(**kwargs):
    data = h11.Data(data=parse.urlencode({
        "client_id": _client_id,
        "client_secret": _client_secret,
        **kwargs,
    }).encode("utf-8"))

    request = h11.Request(
        method="POST",
        target="/token",
        headers=[
            ("host", "oauth2.googleapis.com"),
            ("content-type", "application/x-www-form-urlencoded"),
            ("content-length", str(len(data.data)))
        ]
    )

    return request, data


def code_token_rf(code):
    return token_rf(**{
        "code": code,
        "grant_type": "authorization_code",
        "redirect_uri": "urn:ietf:wg:oauth:2.0:oob"
    })


def refresh_token_rf(refresh_token):
    return token_rf(**{
        "refresh_token": refresh_token,
        "grant_type": "refresh_token"
    })


async def get_refresh_token():
    async with client.factory("accounts.google.com", 443) as make_request:
        async for event in make_request(auth_rf()):
            if isinstance(event, h11.Response):
                response = event
                assert response.status_code == 302, response
            else:
                assert False, type(event)

    location = dict(response.headers)[b"location"].decode("utf-8")
    print(location, file=sys.stderr)
    code = input("code: ")

    async with client.factory("oauth2.googleapis.com", 443) as make_request:
        async for event in make_request(*code_token_rf(code)):
            if isinstance(event, h11.Response):
                response = event
                assert response.status_code == 200, response
            elif isinstance(event, h11.Data):
                data = event
                body = json.loads(data.data)
            else:
                assert False, type(event)

    refresh_token = body["refresh_token"]
    return refresh_token


async def get_access_token(make_request, _token):
    async for event in make_request(*refresh_token_rf(_token)):
        if isinstance(event, h11.Response):
            response = event
            assert response.status_code == 200, response
        elif isinstance(event, h11.Data):
            data = event
            body = json.loads(data.data)
        else:
            assert False, type(event)

    access_token = body["access_token"]
    expires_in = body["expires_in"]
    print(access_token, expires_in, file=sys.stderr)
    return access_token, expires_in


@asynccontextmanager
async def authorizer(_token):
    epoch, access_token, expires_in = None, None, None

    async with client.factory("oauth2.googleapis.com", 443) as make_request:

        async def refresh_access_token():
            nonlocal epoch, access_token, expires_in
            if epoch is not None and time.monotonic() - epoch < expires_in:
                return access_token
            else:
                print("refreshing access_token", file=sys.stderr)
                epoch = time.monotonic()
                access_token, expires_in = await get_access_token(make_request, _token)
                return access_token

        async def authorize(request_builder):
            return request_builder(
                ("authorization", " ".join((
                    "Bearer", await refresh_access_token()
                )))
            )
            return request

        yield authorize


if __name__ == "__main__":
    import trio
    print(trio.run(get_refresh_token))
