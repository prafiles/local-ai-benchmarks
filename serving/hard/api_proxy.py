#!/usr/bin/env python3
"""OpenAI-shaped shim so hosted models run through the UNMODIFIED harness.

The point is that b5.py, the task set, the extractor and the graders must not
change. If the harness were taught to speak two more protocols, a hosted score
would no longer be comparable to a local one -- the whole tier rests on every
model meeting the same grader through the same path. So the translation lives
here, behind localhost:8900/v1/chat/completions, and b5.py cannot tell the
difference.

What it normalises, per backend:

  gpt-*     OpenAI. max_tokens -> max_completion_tokens (this model rejects the
            old field). temperature is DROPPED: the model accepts only its
            default of 1, so a greedy profile is impossible and passing t=0
            would 400 the whole run. reasoning_effort passes through, including
            "none", which genuinely zeroes reasoning tokens. Reasoning text is
            never returned by this API -- only a token COUNT -- so
            reasoning_content is synthesised as a placeholder of that many
            characters purely so b5's think_chars is non-zero on the thinking
            arm. It is a marker, not a trace, and is labelled as such below.

  claude-*  Anthropic Messages. system goes to its own field; thinking is
            adaptive with output_config.effort. temperature is DROPPED (the
            model deprecates it entirely). "none" is NOT a valid effort here,
            so an off arm cannot be built -- the caller must not ask for one.
            Real thinking blocks ARE returned, so reasoning_content is genuine.

finish_reason is mapped so b5's cap counter keeps working: anything that means
"ran out of room" becomes "length", everything else "stop". Getting this wrong
would silently report truncated answers as clean stops.
"""
import json
import os
import sys
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, HTTPServer

OPENAI_KEY = os.environ.get("OPENAI_API_KEY", "")
ANTHROPIC_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
PORT = int(os.environ.get("PROXY_PORT", "8900"))


def post(url, body, headers, timeout=3600):
    req = urllib.request.Request(url, data=json.dumps(body).encode(), headers=headers)
    return json.loads(urllib.request.urlopen(req, timeout=timeout).read())


def via_openai(req):
    body = {"model": req["model"], "messages": req["messages"]}
    # This model rejects max_tokens outright; the harness always sends it.
    if "max_tokens" in req:
        body["max_completion_tokens"] = req["max_tokens"]
    # temperature deliberately not forwarded -- only the default is accepted.
    if req.get("reasoning_effort"):
        body["reasoning_effort"] = req["reasoning_effort"]
    d = post("https://api.openai.com/v1/chat/completions", body,
             {"content-type": "application/json",
              "authorization": "Bearer " + OPENAI_KEY})
    ch = d["choices"][0]
    usage = d.get("usage", {}) or {}
    rtok = (usage.get("completion_tokens_details") or {}).get("reasoning_tokens", 0) or 0
    fin = "length" if ch.get("finish_reason") == "length" else "stop"
    return {
        "choices": [{"message": {
            "role": "assistant",
            "content": ch["message"].get("content") or "",
            # Placeholder: this API returns a reasoning token COUNT and never the
            # text. b5 only measures len(), so a marker of the right magnitude
            # keeps think_chars meaningful without inventing a trace.
            "reasoning_content": ("█" * rtok) if rtok else ""},
            "finish_reason": fin}],
        "usage": {"completion_tokens": usage.get("completion_tokens", 0),
                  "prompt_tokens": usage.get("prompt_tokens", 0)},
        "_reasoning_tokens": rtok,
    }


def via_anthropic(req):
    msgs, system = [], None
    for m in req["messages"]:
        if m["role"] == "system":
            system = m["content"]
        else:
            msgs.append({"role": m["role"], "content": m["content"]})
    body = {"model": req["model"], "messages": msgs,
            "max_tokens": req.get("max_tokens", 8000)}
    if system:
        body["system"] = system
    eff = req.get("reasoning_effort")
    if eff and eff != "none":
        body["thinking"] = {"type": "adaptive"}
        body["output_config"] = {"effort": eff}
    d = post("https://api.anthropic.com/v1/messages", body,
             {"content-type": "application/json", "x-api-key": ANTHROPIC_KEY,
              "anthropic-version": "2023-06-01"})
    text = "".join(b.get("text", "") for b in d["content"] if b["type"] == "text")
    think = "".join(b.get("thinking", "") for b in d["content"] if b["type"] == "thinking")
    fin = "length" if d.get("stop_reason") == "max_tokens" else "stop"
    u = d.get("usage", {}) or {}
    return {
        "choices": [{"message": {"role": "assistant", "content": text,
                                 "reasoning_content": think},
                     "finish_reason": fin}],
        "usage": {"completion_tokens": u.get("output_tokens", 0),
                  "prompt_tokens": u.get("input_tokens", 0)},
    }


class H(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):  # silence per-request logging
        pass

    def do_POST(self):
        n = int(self.headers.get("content-length", 0))
        req = json.loads(self.rfile.read(n) or b"{}")
        try:
            model = req.get("model", "")
            out = via_anthropic(req) if model.startswith("claude") else via_openai(req)
            code = 200
        except urllib.error.HTTPError as e:
            out = {"error": {"message": e.read().decode()[:400], "code": e.code}}
            code = 200 if e.code < 500 else 502
            sys.stderr.write("upstream %s: %s\n" % (e.code, json.dumps(out)[:200]))
        except Exception as e:  # noqa: BLE001
            out = {"error": {"message": "%s: %s" % (type(e).__name__, e)}}
            code = 502
            sys.stderr.write("proxy error: %s\n" % e)
        payload = json.dumps(out).encode()
        self.send_response(code)
        self.send_header("content-type", "application/json")
        self.send_header("content-length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)


if __name__ == "__main__":
    print("proxy on http://localhost:%d/v1/chat/completions" % PORT, flush=True)
    HTTPServer(("127.0.0.1", PORT), H).serve_forever()
