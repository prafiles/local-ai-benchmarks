#!/usr/bin/env python3
"""Git category — 50 tasks.

Read-only commands are graded on their OUTPUT (captured to $OUT by the runner),
never with a `true` checker, and fixtures include decoy commits/files so that
filtering actually has to work. State-changing commands are graded on repo state.
"""

INIT = ("git init -q . && git config user.email a@b.c && git config user.name tester && "
        "git config commit.gpgsign false")
BASE = INIT + " && echo one > f.txt && git add . && git commit -qm first"
TWO = BASE + " && echo two >> f.txt && git add . && git commit -qm second"
# decoy file + commit, so "only f.txt" style filters are testable
DECOY = BASE + " && echo o > other.txt && git add . && git commit -qm otherwork"

GIT = [
# ---- state-changing
("git-001", TWO, "Undo the most recent commit but keep its changes staged in the index.",
 "test \"$(git rev-list --count HEAD)\" = 1 && ! git diff --cached --quiet",
 "git reset --soft HEAD~1"),
("git-002", TWO, "Undo the most recent commit and discard its changes entirely.",
 "test \"$(git rev-list --count HEAD)\" = 1 && git diff --quiet && git diff --cached --quiet",
 "git reset --hard HEAD~1"),
("git-003", BASE + " && echo bad > f.txt && git add . && git commit -qm bad",
 "Create a new commit that undoes the changes of the most recent commit, without rewriting "
 "history. Do not open an editor.",
 "test \"$(cat f.txt)\" = one && test \"$(git rev-list --count HEAD)\" = 3",
 "git revert --no-edit HEAD"),
("git-004", BASE + " && echo y > secret.env && git add . && git commit -qm add",
 "Stop tracking secret.env in git but keep the file on disk.",
 "test -f secret.env && ! git ls-files --error-unmatch secret.env 2>/dev/null",
 "git rm --cached secret.env"),
("git-005", BASE, "Create an annotated tag v1.0.0 with the message 'release one' on the current commit.",
 "git cat-file -t \"$(git rev-parse v1.0.0)\" | grep -q tag && git tag -l -n1 v1.0.0 | grep -q 'release one'",
 "git tag -a v1.0.0 -m 'release one'"),
("git-006", BASE + " && git branch -m oldname", "Rename the current branch from oldname to newname.",
 "test \"$(git rev-parse --abbrev-ref HEAD)\" = newname", "git branch -m newname"),
("git-007", BASE + " && git checkout -q -b feature && echo feat > g.txt && git add . && "
 "git commit -qm featwork && git checkout -q -",
 "Apply only the single tip commit from branch feature onto the current branch.",
 "test -f g.txt && test \"$(git rev-parse --abbrev-ref HEAD)\" != feature", "git cherry-pick feature"),
("git-008", BASE, "Create a new branch called feature/login and switch to it in one command.",
 "test \"$(git rev-parse --abbrev-ref HEAD)\" = feature/login", "git checkout -b feature/login"),
("git-009", BASE, "Change the message of the most recent commit to 'fix parser' without opening an editor.",
 "git log -1 --pretty=%s | grep -q 'fix parser'", "git commit --amend -m 'fix parser'"),
("git-010", BASE + " && echo tracked > t.txt && git add t.txt && echo untracked > u.txt",
 "Stash all local changes including untracked files.",
 "test -z \"$(git status --porcelain)\" && test \"$(git stash list | wc -l)\" -ge 1", "git stash -u"),
("git-011", BASE + " && echo x > s.txt && git add . && git stash -q",
 "Restore the most recent stash and remove it from the stash list.",
 "test -f s.txt && test \"$(git stash list | wc -l)\" = 0", "git stash pop"),
("git-013", BASE + " && echo mod >> f.txt",
 "Discard the uncommitted local modifications to f.txt, restoring it to the last commit.",
 "test \"$(cat f.txt)\" = one", "git checkout -- f.txt"),
("git-014", BASE + " && echo a > new.txt", "Stage all changes including new files.",
 "git diff --cached --name-only | grep -q new.txt", "git add -A"),
("git-015", BASE + " && echo a > staged.txt && git add staged.txt",
 "Unstage staged.txt but keep the file and its content.",
 "test -f staged.txt && ! git diff --cached --name-only | grep -q staged.txt",
 "git restore --staged staged.txt"),
("git-016", BASE + " && git checkout -q -b other && echo o > o.txt && git add . && "
 "git commit -qm o && git checkout -q -",
 "Merge the branch other into the current branch without fast-forwarding, no editor.",
 "test -f o.txt && test \"$(git rev-list --count HEAD)\" -ge 3", "git merge --no-ff --no-edit other"),
("git-017", BASE + " && git checkout -q -b gone && git checkout -q -", "Delete the branch named gone.",
 "! git rev-parse --verify gone 2>/dev/null", "git branch -d gone"),
("git-020", BASE, "Configure the local repository so that user.email is dev@example.com.",
 "test \"$(git config user.email)\" = dev@example.com", "git config user.email dev@example.com"),
("git-023", BASE, "Add a remote named origin pointing at https://example.com/repo.git",
 "test \"$(git remote get-url origin)\" = https://example.com/repo.git",
 "git remote add origin https://example.com/repo.git"),
("git-025", BASE + " && git remote add origin https://example.com/old.git",
 "Change the URL of the existing remote origin to https://example.com/new.git",
 "test \"$(git remote get-url origin)\" = https://example.com/new.git",
 "git remote set-url origin https://example.com/new.git"),
("git-027", BASE, "Create a lightweight tag named v0.1 on the current commit.",
 "git rev-parse v0.1 >/dev/null 2>&1", "git tag v0.1"),
("git-028", BASE + " && git tag v0.9", "Delete the tag named v0.9.",
 "! git rev-parse v0.9 2>/dev/null", "git tag -d v0.9"),
("git-030", BASE + " && echo m >> f.txt && git add . && git commit -qm m2 && "
 "echo n >> f.txt && git add . && git commit -qm m3",
 "Reset the branch back two commits, discarding those commits and their changes completely.",
 "test \"$(git rev-list --count HEAD)\" = 1", "git reset --hard HEAD~2"),
("git-037", BASE + " && echo a >> f.txt && git add . && git commit -qm second && "
 "echo b >> f.txt && git add . && git commit -qm third",
 "Combine the last two commits into one without changing the working tree content, using a reset "
 "then a single commit. Do not open an editor.",
 "test \"$(git rev-list --count HEAD)\" = 2 && test \"$(git status --porcelain)\" = ''",
 "git reset --soft HEAD~2 && git commit -qm squashed"),
("git-038", BASE, "Create and switch to a new branch named dev using the modern switch command.",
 "test \"$(git rev-parse --abbrev-ref HEAD)\" = dev", "git switch -c dev"),
("git-039", BASE + " && git checkout -q -b work && git checkout -q -",
 "Switch back to the branch you were on immediately before the current one.",
 "test \"$(git rev-parse --abbrev-ref HEAD)\" = work", "git checkout -"),
("git-043", BASE + " && echo x > extra.txt",
 "Delete all untracked files in the working tree without prompting.",
 "! test -f extra.txt", "git clean -fd"),
("git-044", BASE + " && echo a >> f.txt && git add . && git commit -qm a2",
 "Create a branch named snapshot pointing at the previous commit without switching to it.",
 "test \"$(git rev-parse snapshot)\" = \"$(git rev-parse HEAD~1)\"", "git branch snapshot HEAD~1"),
("git-047", BASE + " && echo m >> f.txt", "Save the current changes to the stash with the message wip.",
 "git stash list | grep -q wip", "git stash push -m wip"),
("git-050", BASE + " && echo r > r.txt && git add r.txt && git commit -qm r",
 "Move the file r.txt to renamed.txt using git so the rename is staged.",
 "test -f renamed.txt && git diff --cached --name-only | grep -q renamed.txt",
 "git mv r.txt renamed.txt"),

# ---- read-only: graded on captured OUTPUT, with decoys so filters must work
("git-012", DECOY, "Show the commit history for only the file f.txt.",
 "grep -q first \"$OUT\" && ! grep -q otherwork \"$OUT\"", "git log -- f.txt"),
("git-018", BASE, "Print the total number of commits on the current branch.",
 "test \"$(tr -dc '0-9' < \"$OUT\")\" = 1", "git rev-list --count HEAD"),
("git-019", BASE + " && echo zeta >> f.txt && git add . && git commit -qm z",
 "Show the changes introduced by the most recent commit.",
 "grep -q '^+zeta' \"$OUT\"", "git show HEAD"),
("git-021", BASE + " && echo wnew >> f.txt", "Show the unstaged differences in the working tree.",
 "grep -q '^+wnew' \"$OUT\"", "git diff"),
("git-022", BASE + " && echo wstaged >> f.txt && git add .",
 "Show the differences that are staged for the next commit.",
 "grep -q '^+wstaged' \"$OUT\"", "git diff --cached"),
("git-024", BASE + " && git remote add origin https://example.com/repo.git",
 "Print the URL of the remote named origin.",
 "grep -q 'example.com/repo.git' \"$OUT\"", "git remote get-url origin"),
("git-026", DECOY + " && echo c > c.txt && git add . && git commit -qm ccommit",
 "List only the file names changed by the most recent commit, with no commit header.",
 "grep -q '^c.txt' \"$OUT\" && ! grep -qi 'commit ' \"$OUT\" && ! grep -q other.txt \"$OUT\"",
 "git show --name-only --pretty=format: HEAD"),
("git-029", BASE + " && echo p > puntracked.txt",
 "Show the status of the working tree in the short porcelain format.",
 "grep -qE '^\\?\\? puntracked.txt' \"$OUT\"", "git status --porcelain"),
("git-031", BASE, "Print the abbreviated commit hash of the current HEAD.",
 "grep -qE '^[0-9a-f]{7,40}$' \"$OUT\"", "git rev-parse --short HEAD"),
("git-032", BASE + " && git branch topicbranch", "List all local branches.",
 "grep -q topicbranch \"$OUT\"", "git branch"),
("git-033", BASE + " && echo ig > ignored.log && printf '*.log\\n' > .gitignore",
 "Show the files that are being ignored by gitignore rules.",
 "grep -q 'ignored.log' \"$OUT\"", "git status --ignored --porcelain"),
("git-034", DECOY, "Show the commit log with one line per commit.",
 "grep -qE '^[0-9a-f]{7,} ' \"$OUT\" && test \"$(grep -c . \"$OUT\")\" = 2", "git log --oneline"),
("git-035", BASE, "Show who last modified each line of f.txt.",
 "grep -q 'one' \"$OUT\" && grep -q 'tester' \"$OUT\"", "git blame f.txt"),
("git-036", BASE + " && echo s > s.txt && git add . && git commit -qm needlecommit",
 "Show only the commits whose message contains the word needlecommit.",
 "grep -q needlecommit \"$OUT\" && ! grep -q first \"$OUT\"", "git log --grep=needlecommit"),
("git-040", BASE + " && echo big > big.bin && printf 'big.bin\\n' > .gitignore",
 "Show which gitignore rule causes big.bin to be ignored.",
 "grep -q 'big.bin' \"$OUT\" && grep -q gitignore \"$OUT\"", "git check-ignore -v big.bin"),
("git-041", BASE + " && echo dnew >> f.txt && git add . && git commit -qm d",
 "Show the diff between the current HEAD and its parent.",
 "grep -q '^+dnew' \"$OUT\"", "git diff HEAD~1 HEAD"),
("git-042", BASE, "Print the configured user.name for this repository.",
 "grep -q '^tester$' \"$OUT\"", "git config user.name"),
("git-045", BASE + " && git checkout -q -b b1 && echo x > x.txt && git add . && "
 "git commit -qm onlyonb1 && git checkout -q -",
 "Show the commits that are on branch b1 but not on the current branch.",
 "grep -q onlyonb1 \"$OUT\" && ! grep -q first \"$OUT\"", "git log HEAD..b1"),
("git-046", BASE, "Show the reflog of HEAD.",
 "grep -q 'HEAD@{0}' \"$OUT\"", "git reflog"),
("git-048", BASE + " && echo m >> f.txt && git stash -q", "List the entries currently in the stash.",
 "grep -q 'stash@{0}' \"$OUT\"", "git stash list"),
("git-049", BASE, "Print the name of the current branch only.",
 "grep -qE '^(master|main)$' \"$OUT\"", "git rev-parse --abbrev-ref HEAD"),
]


def tasks():
    return [(tid, s, p + " Reply with a single shell command only, no explanation, no markdown.", c)
            for tid, s, p, c, _r in GIT]


if __name__ == "__main__":
    ids = [t[0] for t in GIT]
    assert len(ids) == len(set(ids)), "duplicate ids"
    trivial = [t[0] for t in GIT if t[3].strip() == "true"]
    print(f"git tasks: {len(GIT)}  unique ids: ok  trivial checkers: {len(trivial)}")
    readonly = [t[0] for t in GIT if "$OUT" in t[3]]
    print(f"output-graded: {len(readonly)}  state-graded: {len(GIT) - len(readonly)}")
