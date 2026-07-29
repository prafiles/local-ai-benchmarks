#!/usr/bin/env python3
"""Stop the CoT instruction from destroying the task's own format requirements.

Measured on Qwen2.5-Coder. The first working CoT instruction ended with "exactly
the requested output and nothing else", which the model read as "bare
declaration": 27 of 50 TypeScript answers dropped the `export` keyword, against 0
of 50 at baseline. The TS prompts begin with the word "export", so failing them is
correct grading -- but the cause was the instruction, not the model's reasoning.
Injecting export back recovered 23 -> 36 of 50, meaning 13 of the 25-task TS drop
was pure format compliance.

Naming the requirement explicitly fixes it: on 16 export-requiring probes,
export retention went 12/16 -> 16/16 with marker compliance unchanged at 16/16.

That matters because the CoT arm exists to answer "does prompted reasoning help a
model with no thinking mode". An instruction that quietly breaks output format
answers a different and much less interesting question.
"""
p = "/root/bench2/b3.py"
s = open(p).read()

old = '''COT_SUFFIX = (
    "\\n\\nDo not answer immediately. First write at least two sentences explaining "
    "your approach and any edge cases. Then write " + COT_MARK + " on its own line, "
    "followed by exactly the requested output and nothing else."
)'''

new = '''COT_SUFFIX = (
    "\\n\\nDo not answer immediately. First write at least two sentences explaining "
    "your approach and any edge cases. Then write " + COT_MARK + " on its own line, "
    "followed by the answer in exactly the format the task asked for -- keeping "
    "every keyword it specified, such as export or module.exports -- and nothing "
    "else."
)'''

if "keeping " in s and "such as export" in s:
    print("already patched")
else:
    assert old in s, "COT_SUFFIX did not match"
    open(p, "w").write(s.replace(old, new, 1))
    print("COT_SUFFIX: now names the format requirements it must preserve")
