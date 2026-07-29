#!/usr/bin/env python3
"""Strip an unterminated <think> too, not just a balanced pair.

`strip_think` matched `<think>.*?</think>`. In the native reasoning arm that was
harmless -- vLLM separates the trace into `reasoning` and leaves `content` holding
the answer alone, so there were no tags in the graded text at all.

The prompted-CoT arm puts the reasoning INSIDE the answer, and a run that hits the
token cap mid-thought never emits `</think>`. The regex then matches nothing and
the entire chain of thought is graded as if it were the answer. For the executed
categories that just fails. For the 250 pattern-graded ones it is worse than
failing: the reasoning discusses the task in the task's own vocabulary, so it can
match the very keywords the rubric looks for and score a pass for a task where no
answer was ever produced.

An unclosed <think> means everything after it is deliberation, so drop it.
"""
p = "/root/bench2/b3.py"
s = open(p).read()

old = '''def strip_think(t):
    return re.sub(r"<think>.*?</think>", "", t, flags=re.S)'''

new = '''def strip_think(t):
    t = re.sub(r"<think>.*?</think>", "", t, flags=re.S)
    # An unclosed <think> means the cap landed mid-thought: everything after it is
    # deliberation, never an answer. Left in, it would be graded AS the answer, and
    # a rubric can match a model reasoning aloud in the task's own vocabulary.
    return re.sub(r"<think>.*\\Z", "", t, flags=re.S)'''

if "unclosed <think>" in s:
    print("already patched")
else:
    assert old in s, "strip_think did not match"
    open(p, "w").write(s.replace(old, new, 1))
    print("strip_think: unterminated <think> tail now dropped")
