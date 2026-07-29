#!/usr/bin/env python3
"""Show exactly what comes back with thinking on, and where it lands."""
import json
import sys
import urllib.request

URL = "http://localhost:8000/v1/chat/completions"
sys.path.insert(0, "/root/bench2")
import b3  # noqa: E402

model = sys.argv[1]
want = sys.argv[2] if len(sys.argv) > 2 else "git-001"
task = [t for t in b3.all_tasks() if t[0] == want][0]
tid, cat, kind, prompt, mt = task

payload = {"model": model, "messages": [{"role": "user", "content": prompt}],
           "max_tokens": 2000, "temperature": 0,
           "chat_template_kwargs": {"enable_thinking": True}}
req = urllib.request.Request(URL, data=json.dumps(payload).encode(),
                             headers={"Content-Type": "application/json"})
d = json.loads(urllib.request.urlopen(req, timeout=900).read())
msg = d["choices"][0]["message"]
content = msg.get("content") or ""
rc = msg.get("reasoning_content") or ""
print(f"task {tid} ({cat})  finish={d['choices'][0]['finish_reason']}  "
      f"completion_tokens={d['usage']['completion_tokens']}")
print(f"message keys: {sorted(msg.keys())}")
print(f"reasoning_content: {len(rc)} chars")
print(f"content: {len(content)} chars")
print("=" * 70)
print("CONTENT (first 1500 chars):")
print(content[:1500])
print("=" * 70)
print("what b3's extractor would hand the grader:")
print(repr(b3.cmd_of(content))[:300])
