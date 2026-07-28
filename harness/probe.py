#!/usr/bin/env python3
"""Context capability probe: how deep can this model actually go on this GPU?

    probe.py <model> <target_tokens> [more targets...]

Plants a sentinel at the very start of a long dump and asks for it back at the
end, so a pass means the KV really held the whole span -- not just that the
request was accepted.
"""
import json
import sys
import time
import urllib.request

URL = "http://localhost:8000/v1/chat/completions"

UNIT = (
    "def helper_{i:04d}(payload, retries=3):\n"
    "    total = 0\n"
    "    for attempt in range(retries):\n"
    "        total += len(str(payload)) * attempt\n"
    "    return total\n\n"
    "class Widget{i:04d}:\n"
    "    slug = 'widget-{i:04d}'\n"
    "    def render(self, ctx):\n"
    "        return f'<div>{{self.slug}}:{{ctx}}</div>'\n\n"
)

SENTINEL = "AER-DEPLOY-KEY is quartzite-lantern-7741"


def filler(chars):
    buf = []
    n = 0
    i = 0
    while n < chars:
        s = UNIT.format(i=i % 10000)
        buf.append(s)
        n += len(s)
        i += 1
    return "".join(buf)


def probe(model, target):
    # ~3.5 chars/token for this kind of code text; leave headroom for the tail
    body = filler(int(target * 3.4))
    msgs = [
        {"role": "user",
         "content": f"Remember this for later: {SENTINEL}\n\n"
                    "Now here is the first half of the source dump.\n\n" + body[:len(body) // 2]},
        {"role": "assistant", "content": "Noted. I have the key and the first half."},
        {"role": "user", "content": "Here is the second half.\n\n" + body[len(body) // 2:]},
        {"role": "assistant", "content": "Got it."},
        {"role": "user",
         "content": "What is the AER-DEPLOY-KEY value I gave you at the very start? "
                    "Reply with the value only."},
    ]
    payload = {"model": model, "messages": msgs, "max_tokens": 24, "temperature": 0}
    if "qwen3.5" in model.lower():
        payload["chat_template_kwargs"] = {"enable_thinking": False}
    req = urllib.request.Request(URL, data=json.dumps(payload).encode(),
                                 headers={"Content-Type": "application/json"})
    t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=3600) as f:
            d = json.loads(f.read())
    except Exception as e:  # noqa: BLE001
        return {"target": target, "ok": False,
                "err": f"{type(e).__name__}: {str(e)[:200]}"}
    el = time.time() - t0
    pt = d["usage"]["prompt_tokens"]
    txt = (d["choices"][0]["message"]["content"] or "").strip()
    return {"target": target, "ok": True, "prompt_tokens": pt, "secs": round(el, 1),
            "prefill_tok_s": round(pt / el), "recalled": "quartzite-lantern-7741" in txt,
            "answer": txt[:80]}


if __name__ == "__main__":
    m = sys.argv[1]
    out = []
    for t in [int(x) for x in sys.argv[2:]]:
        r = probe(m, t)
        out.append(r)
        print(json.dumps(r), flush=True)
        if not r["ok"]:
            break
    json.dump({"model": m, "probes": out},
              open("/root/bench2/probe_%s.json" % m.split("/")[-1].replace(".", "_"), "w"))
