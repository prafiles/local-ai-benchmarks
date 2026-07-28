#!/usr/bin/env python3
"""Does this model have a reachable thinking mode? Try every switch we know of."""
import json
import sys
import urllib.request

URL = "http://localhost:8000/v1/chat/completions"
Q = ("A train leaves at 14:07 and the trip takes 3h49m. Two stops add 12m each. "
     "What time does it arrive?")

CASES = [("no kwargs", None),
         ("enable_thinking=True", {"enable_thinking": True}),
         ("thinking=True", {"thinking": True}),
         ("reasoning=True", {"reasoning": True})]


def main(model):
    for label, kw in CASES:
        payload = {"model": model, "messages": [{"role": "user", "content": Q}],
                   "max_tokens": 1200, "temperature": 0}
        if kw:
            payload["chat_template_kwargs"] = kw
        req = urllib.request.Request(URL, data=json.dumps(payload).encode(),
                                     headers={"Content-Type": "application/json"})
        try:
            d = json.loads(urllib.request.urlopen(req, timeout=900).read())
        except Exception as e:  # noqa: BLE001
            print(f"  {label:<22} ERROR {type(e).__name__}: {str(e)[:140]}")
            continue
        msg = d["choices"][0]["message"]
        content = msg.get("content") or ""
        rc = msg.get("reasoning_content") or ""
        print(f"  {label:<22} tok={d['usage']['completion_tokens']:<5} "
              f"reasoning_content={len(rc):>5}ch  <think>in content={'<think>' in content}")
        print(f"      content head: {content[:100]!r}")


if __name__ == "__main__":
    main(sys.argv[1])
