#!/usr/bin/env python3
"""Rebuild the prompted-CoT arm around an instruction the models actually follow.

The first version prefixed the task with "work through this inside <think> tags".
Measured on Mellum2 over 8 probes, that produced reasoning on ZERO of them. Three
variants of the same idea all scored 0/8:

    A  prefix, <think> tags                 reasoned 0/8
    B  suffix, <think>, conflict resolved   reasoned 0/8
    C  suffix, <think>, plain               reasoned 0/8
    F  same instruction in a system role    reasoned 0/8
    D  suffix, ANSWER: marker               reasoned 3/8, 1 answer lost
    G  suffix, "Reasoning:" / ANSWER:       reasoned 5/8
    E  suffix, explicit prohibition         reasoned 8/8, 8/8 answered

Two things were wrong. Every task prompt ENDS with "Output only the code, no
explanation", so a prefix asking for reasoning loses to the later instruction.
And these models will not emit <think> tags at all -- that is a trained format
belonging to models with a real thinking mode, which is precisely what this arm
exists to substitute for.

What works is a suffix that forbids answering immediately, sets a floor on the
reasoning, and delimits the answer with a plain marker.

Because the answer is now delimited by ANSWER: rather than a tag pair, the
graders have to know which arm produced a file. The runner records it and grade()
honours it, rather than the marker being stripped unconditionally -- a Docs or
RAG answer is free to contain the word ANSWER: on its own merits, and silently
truncating there would corrupt the baseline and native arms.
"""
p = "/root/bench2/b3.py"
s = open(p).read()

if "COT_SUFFIX" in s:
    print("already patched")
    raise SystemExit(0)

old = '''COT_PREFIX = (
    "Work through this carefully, step by step, inside <think> and </think> tags.\\n"
    "After the closing </think> tag, give ONLY the final answer in exactly the "
    "format requested below, with no commentary before or after it.\\n\\n"
)


def with_cot(model, prompt):
    """Prepend the reasoning instruction only where the model has no native mode."""
    if COT and not can_think(model):
        return COT_PREFIX + prompt
    return prompt'''

new = '''# Measured, not guessed -- see cotprompt.py. A <think>-tag instruction produced
# reasoning on 0 of 8 probes; this produced it on 8 of 8 with every answer intact.
COT_MARK = "ANSWER:"
COT_SUFFIX = (
    "\\n\\nDo not answer immediately. First write at least two sentences explaining "
    "your approach and any edge cases. Then write " + COT_MARK + " on its own line, "
    "followed by exactly the requested output and nothing else."
)
# kept so older result files stay readable
COT_PREFIX = COT_SUFFIX


def with_cot(model, prompt):
    """Append the reasoning instruction where the model has no native mode.

    Appended, not prefixed: the task prompts end with "Output only the code, no
    explanation", and a prefix loses to that.
    """
    if COT and not can_think(model):
        return prompt + COT_SUFFIX
    return prompt


# Set by grade() from the run's own metadata. Off by default so the baseline and
# native arms are untouched -- an answer may legitimately contain "ANSWER:".
COT_SPLIT = False


def after_mark(t):
    """Text after the last CoT marker; unchanged if the model did not use one."""
    i = t.rfind(COT_MARK)
    return t[i + len(COT_MARK):] if i >= 0 else t'''

assert old in s, "COT_PREFIX block did not match"
s = s.replace(old, new, 1)

old_strip = '''def strip_think(t):
    t = re.sub(r"<think>.*?</think>", "", t, flags=re.S)'''
new_strip = '''def strip_think(t):
    if COT_SPLIT:
        t = after_mark(t)
    t = re.sub(r"<think>.*?</think>", "", t, flags=re.S)'''
assert old_strip in s, "strip_think did not match"
s = s.replace(old_strip, new_strip, 1)

# record the arm on the run so grading is not guesswork
old_res = '''def run(model, out_path):
    tasks = all_tasks()
    res = {"model": model, "items": {}}'''
new_res = '''def run(model, out_path):
    tasks = all_tasks()
    res = {"model": model, "items": {},
           "arm": ("native" if (THINK and can_think(model))
                   else "cot" if (COT and not can_think(model)) else "plain")}'''
assert old_res in s, "run() head did not match"
s = s.replace(old_res, new_res, 1)

old_grade = '''def grade(path):
    data = json.load(open(path))
    items = data["items"]'''
new_grade = '''def grade(path):
    global COT_SPLIT
    data = json.load(open(path))
    COT_SPLIT = data.get("arm") == "cot"
    if COT_SPLIT:
        used = sum(1 for v in data["items"].values() if COT_MARK in (v.get("text") or ""))
        print("  CoT arm: %d/%d answers used the %s marker"
              % (used, len(data["items"]), COT_MARK), flush=True)
    items = data["items"]'''
assert old_grade in s, "grade() head did not match"
s = s.replace(old_grade, new_grade, 1)

open(p, "w").write(s)
print("CoT arm: measured suffix instruction, ANSWER: marker, arm recorded on the run")
