from urllib import parse
import json

import h11

import os


_video_id = os.environ["BS_VIDEO_ID"]


def list_live_broadcasts_builder(authorization_header, *, page_token=None):
    page_token_kv = {"pageToken": page_token} if page_token is not None else {}
    request = h11.Request(
        method="GET",
        target="/youtube/v3/liveBroadcasts?" + parse.urlencode({
            "part": "snippet",
            #"mine": "true",
            "id": _video_id,
            #"broadcastStatus": "active",
            **page_token_kv
        }),
        headers=[
            ("host", "www.googleapis.com"),
            ("content-length", "0"),
            authorization_header,
        ])
    return request,


def list_live_chat_messages_builder(authorization_header, *, live_chat_id, page_token=None):
    page_token_kv = {"pageToken": page_token} if page_token is not None else {}
    request = h11.Request(
        method="GET",
        target="/youtube/v3/liveChat/messages?" + parse.urlencode({
            "part": "snippet,authorDetails",
            "liveChatId": live_chat_id,
            **page_token_kv
        }),
        headers=[
            ("host", "www.googleapis.com"),
            ("content-length", "0"),
            authorization_header,
        ])
    return request,


def insert_live_chat_message_builder(authorization_header, *, live_chat_id, message_text):
    data = h11.Data(data=json.dumps({
        "snippet": {
            "liveChatId": live_chat_id,
            "type": "textMessageEvent",
            "textMessageDetails": {
                "messageText": message_text
            }
        }
    }).encode("utf-8"))
    request = h11.Request(
        method="POST",
        target="/youtube/v3/liveChat/messages?" + parse.urlencode({
            "part": "snippet"
        }),
        headers=[
            ("host", "www.googleapis.com"),
            ("content-type", "application/json"),
            ("content-length", str(len(data.data))),
            authorization_header
        ])
    return request, data
