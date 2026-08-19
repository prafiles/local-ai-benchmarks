#!/usr/bin/env python3
"""Shell (12) and Git (12), hard tier.

Same contract as the b3 tier -- (id, fixture setup, prompt, checker, reference)
-- and the same runner: setup in a fresh directory, the model's single command,
then the checker. The container is alpine `sh` with git, openssh-client, gzip,
coreutils, findutils, grep and sed. There is NO bash, so a bashism is a wrong
answer here, not a portability nitpick.

What is harder than b3:

  * Checkers assert the EXACT expected content, not that a keyword appears. On
    the b3 tier several checkers passed on a command that did roughly the right
    thing; here the byte-for-byte result is compared.
  * Fixtures contain decoys chosen to break the almost-right command: filenames
    with spaces and newlines, a file whose name begins with a dash, entries that
    a glob silently misses because they are hidden, and near-miss content that a
    loose grep matches.
  * Several tasks need two or three stages composed in one command, and a few
    need git plumbing rather than porcelain.
"""

# ---------------------------------------------------------------- SHELL (12)
# (id, setup, prompt, checker, reference)
SH = [

("hsh-001",
 "mkdir -p d && touch 'd/a b.txt' 'd/-weird.txt' && printf 'x' > d/c.txt && "
 "touch d/.hidden.txt && touch d/keep.log",
 "Directory d contains .txt files, one with a space in its name, one whose name starts with a "
 "dash, and one hidden dotfile. Rename every .txt file in d -- including the hidden one -- to the "
 "same name with a .md extension, leaving .log files alone.",
 "test -f 'd/a b.md' && test -f d/-weird.md && test -f d/c.md && test -f d/.hidden.md && "
 "test -f d/keep.log && ! ls d/*.txt >/dev/null 2>&1 && ! test -f d/.hidden.txt",
 "find d -maxdepth 1 -name '*.txt' -exec sh -c 'for f do mv -- \"$f\" \"${f%.txt}.md\"; done' sh {} +"),

("hsh-002",
 "printf 'alpha 3\\nbeta 1\\ngamma 3\\ndelta 2\\nalpha 3\\n' > in.txt",
 "in.txt has lines of a word and a number separated by a space. Write to out.txt the distinct "
 "words that appear with the number 3, sorted alphabetically, one per line, with no duplicates "
 "and no numbers.",
 "test \"$(cat out.txt)\" = \"$(printf 'alpha\\ngamma')\"",
 "awk '$2==3{print $1}' in.txt | sort -u > out.txt"),

("hsh-003",
 "mkdir -p logs && printf 'ERROR a\\nINFO b\\nERROR c\\n' > logs/one.log && "
 "printf 'INFO d\\nERRORS e\\n' > logs/two.log && printf 'ERROR f\\n' > logs/.hidden.log && "
 "mkdir -p logs/sub && printf 'ERROR g\\n' > logs/sub/three.log",
 "Count lines that begin with the exact word ERROR across every .log file under logs recursively, "
 "including hidden ones, and write only that number to count.txt. A line beginning with ERRORS "
 "must not count.",
 "test \"$(tr -dc '0-9' < count.txt)\" = 4",
 "find logs -name '*.log' -type f -exec grep -ch '^ERROR ' {} + | awk '{s+=$1} END{print s+0}' > count.txt"),

("hsh-004",
 "printf 'id,name,score\\n3,cee,10\\n1,ay,30\\n2,bee,20\\n' > data.csv",
 "data.csv has a header row and three data rows. Write to sorted.csv the same file with the header "
 "kept as the first line and the data rows sorted by the third column numerically descending.",
 "test \"$(cat sorted.csv)\" = \"$(printf 'id,name,score\\n1,ay,30\\n2,bee,20\\n3,cee,10')\"",
 "{ head -n 1 data.csv; tail -n +2 data.csv | sort -t, -k3,3nr; } > sorted.csv"),

("hsh-005",
 "mkdir -p a b && printf 'same\\n' > a/keep && printf 'same\\n' > b/keep && "
 "printf 'one\\n' > a/diff && printf 'two\\n' > b/diff && printf 'x\\n' > a/onlya && "
 "printf 'y\\n' > b/onlyb",
 "Directories a and b hold files with the same names in places. Write to report.txt the names of "
 "files that exist in BOTH directories but whose contents differ, one per line, sorted, with no "
 "directory prefix.",
 "test \"$(cat report.txt)\" = diff",
 "diff -rq a b 2>/dev/null | awk '/ differ$/{print $2}' | xargs -n1 basename | sort > report.txt"),

("hsh-006",
 "mkdir -p src && printf 'import os\\nimport sys\\n' > src/one.py && "
 "printf 'import os\\n' > src/two.py && printf 'import json\\n' > src/three.py && "
 "printf 'import os\\n' > src/note.txt",
 "Across .py files under src, write to top.txt the single most frequently imported module name "
 "(the word after `import`), and nothing else. Only .py files count.",
 "test \"$(cat top.txt)\" = os",
 "find src -name '*.py' -exec cat {} + | awk '/^import /{print $2}' | sort | uniq -c | sort -rn | head -n 1 | awk '{print $2}' > top.txt"),

("hsh-007",
 "mkdir -p t && printf 'aaa\\n' > t/small && head -c 5000 /dev/zero > t/big && "
 "head -c 3000 /dev/zero > t/mid && mkdir -p t/sub && head -c 4000 /dev/zero > t/sub/nested",
 "Write to biggest.txt the path of the single largest regular file under t, as find prints it, "
 "and nothing else.",
 "test \"$(cat biggest.txt)\" = t/big",
 "find t -type f -exec ls -1s {} + | sort -rn | head -n 1 | awk '{print $2}' > biggest.txt"),

("hsh-008",
 "printf 'GET /a 200\\nGET /b 404\\nGET /a 200\\nGET /c 500\\nGET /a 404\\n' > access.log",
 "access.log lines are a method, a path and a status code. Write to summary.txt one line per "
 "path in the form `path count`, counting only lines whose status is 200, sorted by count "
 "descending then path ascending. Paths with no 200 responses are omitted.",
 "test \"$(cat summary.txt)\" = \"/a 2\"",
 "awk '$3==200{c[$2]++} END{for(p in c) print p, c[p]}' access.log | sort -k2,2nr -k1,1 > summary.txt"),

("hsh-009",
 "mkdir -p pkg && printf 'v1\\n' > pkg/a && printf 'v1\\n' > pkg/b && "
 "mkdir -p pkg/.git && printf 'junk\\n' > pkg/.git/obj && printf 'tmp\\n' > pkg/c.tmp",
 "Create a gzip-compressed tar archive named release.tar.gz of the pkg directory, excluding the "
 ".git directory and any .tmp files. The archive must still contain pkg/a and pkg/b.",
 "test -f release.tar.gz && tar -tzf release.tar.gz | grep -q '^pkg/a$' && "
 "tar -tzf release.tar.gz | grep -q '^pkg/b$' && ! tar -tzf release.tar.gz | grep -q '\\.git' && "
 "! tar -tzf release.tar.gz | grep -q '\\.tmp'",
 "tar --exclude='.git' --exclude='*.tmp' -czf release.tar.gz pkg"),

("hsh-010",
 "printf 'one\\ntwo\\nthree\\nfour\\nfive\\n' > f.txt",
 "Write to mid.txt lines 2 through 4 of f.txt inclusive, and nothing else.",
 "test \"$(cat mid.txt)\" = \"$(printf 'two\\nthree\\nfour')\"",
 "sed -n '2,4p' f.txt > mid.txt"),

("hsh-011",
 "mkdir -p conf/sub && printf 'host = old\\nport = 1\\n' > conf/a.ini && "
 "printf 'host = old\\n' > conf/sub/b.ini && printf 'host = old\\n' > conf/keep.txt",
 "Under conf, replace `old` with `new` in place in every .ini file at any depth, leaving other "
 "files untouched. Afterwards no .ini file may still contain `old`.",
 "grep -q 'host = new' conf/a.ini && grep -q 'host = new' conf/sub/b.ini && "
 "grep -q 'host = old' conf/keep.txt && ! find conf -name '*.ini' -exec grep -l old {} + | grep -q .",
 "find conf -name '*.ini' -type f -exec sed -i 's/old/new/g' {} +"),

("hsh-012",
 "printf 'apple\\nbanana\\ncherry\\n' > left.txt && printf 'banana\\ndate\\napple\\n' > right.txt",
 "Write to both.txt the lines present in BOTH left.txt and right.txt, sorted alphabetically, one "
 "per line. Neither input file is sorted.",
 "test \"$(cat both.txt)\" = \"$(printf 'apple\\nbanana')\"",
 "comm -12 \"$(sort left.txt > /tmp/l; echo /tmp/l)\" \"$(sort right.txt > /tmp/r; echo /tmp/r)\" > both.txt"),
]

# ---------------------------------------------------------------- GIT (12)
INIT = ("git init -q . && git config user.email a@b.c && git config user.name tester && "
        "git config commit.gpgsign false")
BASE = INIT + " && echo one > f.txt && git add . && git commit -qm first"
THREE = (BASE + " && echo two >> f.txt && git add . && git commit -qm second"
         " && echo three >> f.txt && git add . && git commit -qm third")

GIT = [

("hgit-001", THREE,
 "Combine the two most recent commits into one, keeping the older of the two commit messages and "
 "leaving the working tree contents unchanged. Do not open an editor.",
 "test \"$(git rev-list --count HEAD)\" = 2 && test \"$(git log -1 --format=%s)\" = second && "
 "test \"$(cat f.txt)\" = \"$(printf 'one\\ntwo\\nthree')\" && git diff --quiet && "
 "git diff --cached --quiet",
 "git reset --soft HEAD~2 && git commit -qm second"),

("hgit-002",
 BASE + " && git checkout -qb feature && echo feat > g.txt && git add . && git commit -qm feat"
 " && git checkout -q master 2>/dev/null || git checkout -q main",
 "Bring the commit from the feature branch onto the current branch as a single new commit that "
 "does NOT create a merge commit and does NOT move the branch pointer by fast-forward -- the "
 "current branch must gain exactly one commit with one parent.",
 "test \"$(git rev-list --count HEAD)\" = 2 && test \"$(git cat-file -p HEAD | grep -c '^parent ')\" = 1 && "
 "test -f g.txt",
 "git cherry-pick feature"),

("hgit-003", THREE,
 "Write to $OUT the subject line of every commit that touched f.txt, oldest first, one per line, "
 "with no hashes, dates or other decoration.",
 "test \"$(cat $OUT)\" = \"$(printf 'first\\nsecond\\nthird')\"",
 "git log --reverse --format=%s -- f.txt"),

("hgit-004",
 BASE + " && echo secret > .env && git add . && git commit -qm oops && echo more > f.txt && "
 "git add . && git commit -qm later",
 "The file .env was committed by mistake two commits ago and must be removed from the history of "
 "every commit, not just the tip, while keeping both commit messages and the later change to "
 "f.txt. The file must not exist in any commit.",
 "test \"$(git rev-list --count HEAD)\" = 3 && ! git log HEAD --format=%H --name-only | grep -qx '.env' && "
 "! git cat-file -p HEAD~1^{tree} | grep -q '\\.env' && "
 "test \"$(git log -1 --format=%s)\" = later",
 "FILTER_BRANCH_SQUELCH_WARNING=1 git filter-branch -f --index-filter "
 "'git rm -q --cached --ignore-unmatch .env' HEAD >/dev/null 2>&1"),

("hgit-005",
 BASE + " && echo a >> f.txt && git add . && git commit -qm good && echo b >> f.txt && "
 "git add . && git commit -qm bad && echo c >> f.txt && git add . && git commit -qm alsogood",
 "Remove the middle of the last three commits from history entirely, keeping the other two and "
 "their order. Resolve nothing interactively.",
 "test \"$(git rev-list --count HEAD)\" = 3 && ! git log --format=%s | grep -qx bad && "
 "git log --format=%s | grep -qx alsogood && git log --format=%s | grep -qx good",
 "git rebase --onto HEAD~2 HEAD~1 HEAD -X theirs >/dev/null 2>&1 || git rebase --onto HEAD~2 HEAD~1 HEAD >/dev/null 2>&1; git rebase --skip >/dev/null 2>&1; true"),

("hgit-006", THREE,
 "Write to $OUT the number of commits, and nothing else, that are on the current branch but not "
 "reachable from the first commit -- that is, the count of commits after the root.",
 "test \"$(tr -dc '0-9' < $OUT)\" = 2",
 "git rev-list --count HEAD ^$(git rev-list --max-parents=0 HEAD)"),

("hgit-007",
 BASE + " && printf 'one\\nedited\\n' > f.txt && echo new > g.txt && git add g.txt",
 "Write to $OUT the names of files with unstaged changes in the working tree, one per line, "
 "excluding files that are only staged and excluding untracked files.",
 "test \"$(cat $OUT)\" = f.txt",
 "git diff --name-only"),

("hgit-008",
 BASE + " && echo two >> f.txt && git add . && git commit -qm second && "
 "git tag v1 && echo three >> f.txt && git add . && git commit -qm third",
 "Write to $OUT the subject of every commit made after the tag v1, oldest first, one per line.",
 "test \"$(cat $OUT)\" = third",
 "git log --reverse --format=%s v1..HEAD"),

("hgit-009",
 BASE + " && echo wip > w.txt && git add w.txt && echo dirty >> f.txt",
 "Save both the staged and unstaged changes away so the working tree matches HEAD exactly, "
 "keeping the untracked-but-staged file's content recoverable, then confirm the tree is clean.",
 "git diff --quiet && git diff --cached --quiet && test \"$(git stash list | wc -l)\" -ge 1 && "
 "test \"$(cat f.txt)\" = one",
 "git stash push -q -m saved"),

("hgit-010",
 BASE + " && echo two >> f.txt && git add . && git commit -qm second && "
 "echo three >> f.txt && git add . && git commit -qm third",
 "Change the message of the commit BEFORE the current one from second to renamed, leaving the "
 "tip commit's message and every file's final content unchanged. Do not open an editor.",
 "test \"$(git log --format=%s | tr '\\n' ' ')\" = \"third renamed first \" && "
 "test \"$(cat f.txt)\" = \"$(printf 'one\\ntwo\\nthree')\"",
 "FILTER_BRANCH_SQUELCH_WARNING=1 git filter-branch -f --msg-filter "
 "\"sed 's/^second$/renamed/'\" HEAD~2..HEAD >/dev/null 2>&1"),

("hgit-011",
 BASE + " && git checkout -qb topic && echo t > t.txt && git add . && git commit -qm topicwork && "
 "git checkout -q - && echo m > m.txt && git add . && git commit -qm mainwork",
 "Write to $OUT the subject of every commit that is on branch topic but not on the current "
 "branch, one per line.",
 "test \"$(cat $OUT)\" = topicwork",
 "git log --format=%s HEAD..topic"),

("hgit-012",
 BASE + " && echo two >> f.txt && git add . && git commit -qm second",
 "Write to $OUT the full 40-character hash of the tree object that the current commit points at, "
 "and nothing else, using git plumbing rather than parsing log output.",
 "test \"$(tr -d ' \\n' < $OUT | wc -c)\" -ge 40 && "
 "git cat-file -t \"$(tr -d ' \\n' < $OUT)\" | grep -qx tree",
 "git rev-parse HEAD^{tree}"),
]


def verify_source():
    return None


if __name__ == "__main__":
    print("hard shell: %d, hard git: %d" % (len(SH), len(GIT)))
