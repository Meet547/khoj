"""Synthetic scripted demo inputs; never used by the production gateway."""

import html
import json
import re

import httpx

CONVERSATIONS = {
    "hi": [
        (
            "मेरा भाई राहुल 24 साल का है। आखिरी बार दिल्ली स्टेशन पर देखा था। वह हिंदी बोलता है।",
            [
                ("name", "Rahul", "राहुल"),
                ("relation", "brother", "मेरा भाई"),
                ("age", "24", "24 साल"),
                ("last_seen_place", "Delhi station", "दिल्ली स्टेशन"),
                ("language", "Hindi", "हिंदी बोलता है"),
            ],
        ),
        ("उसके माथे पर निशान है।", [("marks", "mark on forehead", "माथे पर निशान")]),
        ("पुरुष है।", [("gender", "male", "पुरुष")]),
        ("उसने नीली कमीज़ पहनी थी।", [("clothing", "blue shirt", "नीली कमीज़")]),
    ],
    "en": [
        (
            "My brother Rahul is 24, speaks Hindi and was last seen at Delhi station.",
            [
                ("name", "Rahul", "Rahul"),
                ("relation", "brother", "My brother"),
                ("age", "24", "24"),
                ("language", "Hindi", "speaks Hindi"),
                ("last_seen_place", "Delhi station", "Delhi station"),
            ],
        ),
        ("He has a scar on his forehead.", [("marks", "scar on forehead", "scar on his forehead")]),
        ("He is male.", [("gender", "male", "male")]),
        ("He wore a blue shirt.", [("clothing", "blue shirt", "blue shirt")]),
    ],
    "hinglish": [
        (
            "Mera bhai Rahul 24 saal ka hai, Hindi bolta hai, last Delhi station pe dekha.",
            [
                ("name", "Rahul", "Rahul"),
                ("relation", "brother", "Mera bhai"),
                ("age", "24", "24 saal"),
                ("language", "Hindi", "Hindi bolta hai"),
                ("last_seen_place", "Delhi station", "Delhi station"),
            ],
        ),
        ("Mathe par scar hai.", [("marks", "scar on forehead", "Mathe par scar")]),
        ("Male hai.", [("gender", "male", "Male")]),
        ("Blue shirt pehni thi.", [("clothing", "blue shirt", "Blue shirt")]),
    ],
}


def fake_model(req: httpx.Request) -> httpx.Response:
    if req.url.path == "/api/tags":
        return httpx.Response(
            200,
            json={
                "models": [
                    {"name": m}
                    for m in ["gpt-oss:20b", "gpt-oss:120b", "gemma4:31b", "nemotron-3-super"]
                ]
            },
        )
    body = json.loads(req.content)
    if any("images" in m for m in body["messages"]):
        output = {"clothing": "blue shirt", "marks": "", "scene": "outdoor scene"}
    else:
        user = [m["content"] for m in body["messages"] if m["role"] == "user"][-1]
        text = html.unescape(re.sub(r"^<user_message>|</user_message>$", "", user))
        fields = next(
            (
                fields
                for turns in CONVERSATIONS.values()
                for sentence, fields in turns
                if sentence == text
            ),
            [],
        )
        output = {
            "intent": "provide_details" if fields else "other",
            "fields": [dict(name=k, value=v, evidence=e) for k, v, e in fields],
        }
        if fields:
            # The canned model deliberately hallucinates: the graph must remove this.
            output["fields"].append(
                {"name": "hair", "value": "silver", "evidence": "silver hair never said"}
            )
    return httpx.Response(
        200, json={"message": {"content": json.dumps(output, ensure_ascii=False)}, "eval_count": 10}
    )
