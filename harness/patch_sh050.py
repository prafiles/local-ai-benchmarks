#!/usr/bin/env python3
"""Make sh-050 test its own prompt.

Found by the null oracle (grade a run that answers nothing -- every task must
fail). sh-050 was the only task in 600 that passed on an empty answer:

    setup  mkdir -p arch && echo data > arch/f && tar -czf bundle.tar.gz arch
    check  test -f arch/f && test "$(cat arch/f)" = data

The setup already satisfies the check, so doing nothing scored a pass. The
reference oracle could never catch this -- it only verifies that the correct
answer passes, and the correct answer does.

The prompt asks for two things: delete arch, then extract. The fix makes the
live directory diverge from the archived one, so only a real extraction restores
it, and leaves a file that is not in the tarball, so only a real delete removes
it. Now:

    do nothing               arch/f is "stale"      -> FAIL
    extract without deleting arch/leftover survives -> FAIL
    delete then extract                             -> PASS

This changes scores for any model that skipped the delete, so every stored run in
the repository is re-graded against it -- baselines included, not just the
reasoning arm. The task was chosen by an audit that never looked at which model
it would help.
"""
p = "/root/bench2/b3_shell.py"
s = open(p).read()

old = '''("sh-050", "mkdir -p arch && echo data > arch/f && tar -czf bundle.tar.gz arch",
 "Extract the archive bundle.tar.gz into the current directory after first deleting the arch directory.",
 "test -f arch/f && test \\"$(cat arch/f)\\" = data",
 "rm -rf arch && tar -xzf bundle.tar.gz"),'''

new = '''("sh-050", "mkdir -p arch && echo data > arch/f && tar -czf bundle.tar.gz arch "
 "&& echo stale > arch/f && touch arch/leftover",
 "Extract the archive bundle.tar.gz into the current directory after first deleting the arch directory.",
 # arch/f diverges from the archived copy so only extracting restores it, and
 # arch/leftover is absent from the tarball so only deleting first removes it
 "test -f arch/f && test \\"$(cat arch/f)\\" = data && ! test -e arch/leftover",
 "rm -rf arch && tar -xzf bundle.tar.gz"),'''

if "leftover" in s:
    print("already patched")
else:
    assert old in s, "sh-050 did not match"
    open(p, "w").write(s.replace(old, new, 1))
    print("sh-050: check now requires the delete AND the extract")
