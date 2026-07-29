#!/usr/bin/env python3
"""Chain-of-thought arm for the two models with no native reasoning mode.

Mellum2 and Qwen2.5-Coder cannot be given a reasoning mode -- there is nothing in
their templates to switch on. The nearest available thing is to ask for the
reasoning in the prompt. That is a DIFFERENT intervention (prompt engineering,
not a trained mode) and it changes the prompt text, so results from this arm are
labelled separately and are not interchangeable with Gemma's and Qwen3.5's.

The reasoning is fenced in <think> tags so the existing extractors can drop it,
which also fixes a latent bug: code_of() searched for a fenced block WITHOUT
stripping <think> first, so a code block inside the reasoning would have been
graded instead of the answer.
"""
import sys

COT_BLOCK = '''
# --------------------------------------------------------------- CoT arm
# For models with no reasoning mode of their own. Asking in the prompt is not the
# same thing as a trained thinking mode, so this arm is reported separately.
COT = os.environ.get("B4_COT") == "1"

COT_PREFIX = (
    "Work through this carefully, step by step, inside <think> and </think> tags.\\n"
    "After the closing </think> tag, give ONLY the final answer in exactly the "
    "format requested below, with no commentary before or after it.\\n\\n"
)


def with_cot(model, prompt):
    """Prepend the reasoning instruction only where the model has no native mode."""
    if COT and not can_think(model):
        return COT_PREFIX + prompt
    return prompt
'''

path = "/root/bench2/b3.py"
s = open(path).read()

if "B4_COT" in s:
    print("already patched")
    sys.exit(0)

# 1. the CoT helper, right after the reasoning helpers the previous patch added
anchor = "THINK_CAPABLE = (\"gemma-4\", \"qwen3.5\")"
assert anchor in s, "reasoning patch must be applied first"
s = s.replace(anchor, anchor + "\n" + COT_BLOCK, 1)

# 2. apply the prefix at the point the prompt becomes a message
old = '''    payload = sampling({"model": model,
                        "messages": [{"role": "user", "content": prompt}],
                        "max_tokens": budget(max_tokens)}, model)'''
new = '''    payload = sampling({"model": model,
                        "messages": [{"role": "user",
                                      "content": with_cot(model, prompt)}],
                        "max_tokens": budget(max_tokens)}, model)'''
assert old in s, "ask() body did not match"
s = s.replace(old, new, 1)

# 3. code_of must drop the reasoning before hunting for a fenced block, or a
#    code block written *inside* <think> gets graded instead of the answer
old_code_of = '''def code_of(t):
    m = FENCE.search(t)
    return m.group(1) if m else t'''
new_code_of = '''def code_of(t):
    t = strip_think(t)
    m = FENCE.search(t)
    return m.group(1) if m else t'''
assert old_code_of in s, "code_of did not match"
s = s.replace(old_code_of, new_code_of, 1)

# strip_think is defined after code_of in this file; move it above so the call resolves
sd = '''def strip_think(t):
    return re.sub(r"<think>.*?</think>", "", t, flags=re.S)


'''
assert sd in s
s = s.replace(sd, "", 1)
s = s.replace("def code_of(t):", sd + "def code_of(t):", 1)

open(path, "w").write(s)
print("b3.py: CoT arm added, code_of now strips reasoning first")
