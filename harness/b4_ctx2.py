#!/usr/bin/env python3
"""Long-context multi-turn sessions, part 2: Bash / Git / SSH / GitHub / Docs /
ReactNative / RAG.

Same contract as part 1: conventions stated once in the opening turns, never
repeated, then probed from ever deeper in the window.
"""
from b4_ctx import DEPTHS, P

# =========================================================== Bash
SH_BASE = r"""
mkdir -p "$AER_LOG_DIR" ops/bin var/spool/billing var/spool/notify var/spool/ingest
cat > ops/bin/aerlog <<'XEOF'
#!/bin/sh
lvl=$(echo "$1" | tr 'a-z' 'A-Z'); shift
echo "$lvl $*" >> "$AER_LOG_DIR/aer.log"
XEOF
cat > ops/bin/aerpurge <<'XEOF'
#!/bin/sh
echo "purged $1" >> "$AER_LOG_DIR/purge.log"
rm -rf "$1"
XEOF
chmod +x ops/bin/aerlog ops/bin/aerpurge
printf '{"tenant_id": "t-101", "n": 1}\n{"tenant_id": "t-102", "n": 2}\n' > var/spool/billing/a.ndjson
printf '{"tenant_id": "t-101", "n": 3}\n{"tenant_id": "t-205", "n": 4}\n{"tenant_id": "t-102", "n": 5}\n' > var/spool/billing/b.ndjson
printf '{"tenant_id": "t-205", "n": 6}\n' > var/spool/billing/c.ndjson
printf 'a\nb\nc\nd\n' > var/spool/notify/n1.ndjson
printf 'x\ny\n' > var/spool/ingest/i1.ndjson
printf 'p\nq\nr\ns\nt\n' > var/spool/ingest/i2.ndjson
touch -t 202001010000 var/spool/billing/a.ndjson var/spool/ingest/i1.ndjson
"""

SH_INTRO = [
    ("Ops side of the same repo now. Layout you need to know:\n\n"
     "```\nops/bin/aerlog      # aerlog <level> <message>  -> appends 'LEVEL message' "
     "to $AER_LOG_DIR/aer.log\nops/bin/aerpurge    # aerpurge <dir>            -> records "
     "the deletion, then removes the dir\nvar/spool/<service>/*.ndjson\n```\n\n"
     "`$AER_LOG_DIR` is exported in every shell on these boxes; never hardcode the path.",
     "Noted — `ops/bin/aerlog` and `ops/bin/aerpurge` are the two repo tools, spool data is "
     "`var/spool/<service>/*.ndjson`, and the log directory comes from `$AER_LOG_DIR`."),

    ("Shell rules on these hosts:\n\n"
     "1. `rm` and `rm -rf` are banned in anything touching `var/spool`. Deletions go through "
     "`ops/bin/aerpurge` so they land in the audit log.\n"
     "2. Log through `ops/bin/aerlog`, never `echo >> file`.\n"
     "3. POSIX sh. No bashisms, no GNU-only flags beyond what busybox and coreutils share.\n"
     "4. When I ask for a command, give me exactly one line and nothing else.\n\n"
     "Clear?",
     "Clear — purge via `ops/bin/aerpurge`, log via `ops/bin/aerlog`, POSIX sh, one line per "
     "answer."),
]

_SH = ("{p} Reply with a single shell command only, no explanation, no markdown.")

SH_PROBES = [
    P("x-sh-1", DEPTHS[0],
      _SH.format(p="Record an info-level log line whose message is exactly `sweep started`."),
      200, "shx",
      {"setup": SH_BASE,
       "chk": 'grep -q "^INFO sweep started$" "$AER_LOG_DIR/aer.log"'},
      'ops/bin/aerlog info "sweep started"'),

    P("x-sh-2", DEPTHS[1],
      _SH.format(p="Delete the directory `var/spool/notify` and everything in it."),
      200, "shx",
      {"setup": SH_BASE,
       "chk": 'test ! -d var/spool/notify && '
              'grep -q "purged var/spool/notify" "$AER_LOG_DIR/purge.log"'},
      "ops/bin/aerpurge var/spool/notify"),

    P("x-sh-3", DEPTHS[2],
      _SH.format(p="Print the total number of lines across every .ndjson file anywhere under "
                   "`var/spool`, as a bare number."),
      200, "shx",
      {"setup": SH_BASE,
       "chk": 'test "$(tr -cd 0-9 < "$OUT")" = "17"'},
      "find var/spool -name '*.ndjson' -exec cat {} + | wc -l"),

    P("x-sh-4", DEPTHS[3],
      _SH.format(p="Compress with `gzip -9` every .ndjson under `var/spool` that was last "
                   "modified more than 7 days ago, leaving newer ones alone."),
      200, "shx",
      {"setup": SH_BASE,
       "chk": 'test -f var/spool/billing/a.ndjson.gz && test -f var/spool/ingest/i1.ndjson.gz '
              '&& test -f var/spool/billing/b.ndjson && test ! -f var/spool/billing/b.ndjson.gz'},
      "find var/spool -name '*.ndjson' -mtime +7 -exec gzip -9 {} +"),

    P("x-sh-5", DEPTHS[4],
      _SH.format(p="Write the distinct tenant_id values appearing in "
                   "`var/spool/billing/*.ndjson` — sorted, one per line — to a file named "
                   "`tenants.txt` in the log directory."),
      220, "shx",
      {"setup": SH_BASE,
       "chk": 'test "$(tr -cd \'a-z0-9-\' < "$AER_LOG_DIR/tenants.txt")" = "t-101t-102t-205"'},
      "grep -ho '\"tenant_id\": *\"[^\"]*\"' var/spool/billing/*.ndjson | "
      "sed 's/.*\"\\([^\"]*\\)\"$/\\1/' | sort -u > \"$AER_LOG_DIR/tenants.txt\""),
]


# =========================================================== Git
GIT_BASE = r"""
git init -q -b trunk .
git config user.email t@aerelith.test
git config user.name Tester
echo one > a.txt
git add . && git commit -qm "base"
git tag rel/2026.05.1
git tag rel/2026.06.4
echo two >> a.txt
git commit -qam "second"
echo three > b.txt
git add . && git commit -qm "third"
git tag rel/2026.07.1
git init -q --bare /tmp/origin.git
git init -q --bare /tmp/mirror.git
git remote add origin /tmp/origin.git
git remote add mirror /tmp/mirror.git
"""

GIT_TAGS_EXTRA = """
echo four > c.txt
git add . && git commit -qm "fourth"
git tag rel/2026.07.2
git tag rel/2026.08.1
"""

GIT_INTRO = [
    ("Repo conventions for the aerelith monorepo — these differ from the defaults, so please "
     "hold on to them:\n\n"
     "1. The default branch is **`trunk`**. There is no `main` and no `master`; the migration "
     "finished in 2024 and the old names are not aliases.\n"
     "2. Two remotes: `origin` is the one everyone pulls from, `mirror` is a write-only "
     "off-site backup. Never fetch from `mirror`.\n"
     "3. Release tags are `rel/YYYY.MM.N` — for example `rel/2026.07.1` is the first July "
     "2026 release.\n"
     "4. Published history is immutable. To undo a released commit you add a commit that "
     "reverses it; `reset --hard`, `rebase` and force-push on `trunk` are all forbidden.\n\n"
     "Confirm and we'll get to work.",
     "Confirmed — default branch `trunk`, `origin` for reads and `mirror` for backup pushes, "
     "`rel/YYYY.MM.N` tags, and undo by reverting rather than rewriting."),
]

_G = "{p} Reply with a single shell command only, no explanation, no markdown."

GIT_PROBES = [
    P("x-git-1", DEPTHS[0],
      _G.format(p="Create a topic branch called `feat/quota-cap` starting at the tip of the "
                  "default branch, and switch to it."),
      200, "gitx",
      {"setup": GIT_BASE,
       "chk": 'test "$(git rev-parse --abbrev-ref HEAD)" = "feat/quota-cap" && '
              'test "$(git rev-parse feat/quota-cap)" = "$(git rev-parse trunk)"'},
      "git checkout -b feat/quota-cap trunk"),

    P("x-git-2", DEPTHS[1],
      _G.format(p="The commit tagged `rel/2026.07.1` broke production. Undo its changes on "
                  "the default branch, following our history policy."),
      200, "gitx",
      {"setup": GIT_BASE,
       "chk": 'test ! -f b.txt && '
              'test "$(git rev-parse HEAD~1)" = "$(git rev-parse rel/2026.07.1^{commit})" && '
              'test "$(git rev-list --count HEAD)" = "4"'},
      "git revert --no-edit rel/2026.07.1"),

    P("x-git-3", DEPTHS[2],
      _G.format(p="Push the default branch to the off-site backup, and only there."),
      200, "gitx",
      {"setup": GIT_BASE,
       "chk": 'git --git-dir=/tmp/mirror.git rev-parse trunk >/dev/null 2>&1 && '
              '! git --git-dir=/tmp/origin.git rev-parse trunk >/dev/null 2>&1'},
      "git push mirror trunk"),

    P("x-git-4", DEPTHS[3],
      _G.format(p="List only the release tags belonging to July 2026."),
      200, "gitx",
      {"setup": GIT_BASE + GIT_TAGS_EXTRA,
       "chk": 'grep -q "rel/2026.07.1" "$OUT" && grep -q "rel/2026.07.2" "$OUT" && '
              '! grep -q "2026.06" "$OUT" && ! grep -q "2026.05" "$OUT" && '
              '! grep -q "2026.08" "$OUT"'},
      "git tag -l 'rel/2026.07.*'"),

    P("x-git-5", DEPTHS[4],
      _G.format(p="Show just the names of the files that changed between release "
                  "`rel/2026.07.1` and release `rel/2026.07.2`."),
      200, "gitx",
      {"setup": GIT_BASE + GIT_TAGS_EXTRA,
       "chk": 'grep -q "^c.txt$" "$OUT" && ! grep -q "a.txt" "$OUT" && '
              '! grep -q "b.txt" "$OUT"'},
      "git diff --name-only rel/2026.07.1 rel/2026.07.2"),
]


# =========================================================== SSH
SSH_INTRO = [
    ("Access layout for the aerelith fleet. Nothing internal is reachable directly; every "
     "connection goes through one bastion.\n\n"
     "```\nbastion   edge.aerelith.internal   port 2202   user aer-ops   "
     "key ~/.ssh/aer_ed25519\ninternal  <name>.eu-west.aerelith.internal   port 22   "
     "user svc-aer   key ~/.ssh/aer_ed25519\n```\n\n"
     "So `ingest-01` means `ingest-01.eu-west.aerelith.internal`, jumped through the bastion.",
     "Noted — bastion `aer-ops@edge.aerelith.internal:2202`, internal hosts are "
     "`<name>.eu-west.aerelith.internal` as `svc-aer`, both using `~/.ssh/aer_ed25519`."),

    ("Client config rules:\n\n"
     "1. Every internal host block sets `ProxyJump aer-ops@edge.aerelith.internal:2202`.\n"
     "2. `StrictHostKeyChecking accept-new` — not `no`, we still pin after first use.\n"
     "3. `ForwardAgent no` everywhere. Agent forwarding to internal hosts is a fireable "
     "offence here.\n"
     "4. `ServerAliveInterval 30`.\n\n"
     "Ready for the first block.",
     "Ready — ProxyJump through the bastion, `accept-new`, `ForwardAgent no`, "
     "`ServerAliveInterval 30`."),
]

BASTION_JUMP = "aer-ops@edge.aerelith.internal:2202"

SSH_PROBES = [
    P("x-ssh-1", DEPTHS[0],
      "Write the OpenSSH client config block for the alias `ingest-01`. Output only the "
      "config, no markdown.", 300, "sshcfgx",
      {"alias": "ingest-01",
       "spec": {"hostname": "ingest-01.eu-west.aerelith.internal", "user": "svc-aer",
                "port": "22", "proxyjump": BASTION_JUMP,
                "stricthostkeychecking": "accept-new", "forwardagent": "no",
                "serveraliveinterval": "30"},
       "pats": [r"aer_ed25519"]},
      "Host ingest-01\n    HostName ingest-01.eu-west.aerelith.internal\n"
      "    User svc-aer\n    Port 22\n    IdentityFile ~/.ssh/aer_ed25519\n"
      "    ProxyJump " + BASTION_JUMP + "\n    StrictHostKeyChecking accept-new\n"
      "    ForwardAgent no\n    ServerAliveInterval 30\n"),

    P("x-ssh-2", DEPTHS[1],
      "Give the command to copy `/var/log/aer.log` off `ingest-01` into the current "
      "directory. Reply with a single shell command only, no explanation, no markdown.",
      200, "rubricx",
      {"must": [r"\bscp\b|\brsync\b", r"ingest-01", r"/var/log/aer\.log",
                r"(\s|:)\.\s*$|\s\./?\s*$"], "must_not": []},
      "scp ingest-01:/var/log/aer.log ."),

    P("x-ssh-3", DEPTHS[2],
      "Write the OpenSSH client config block for the alias `db-01` which, in addition to the "
      "standard rules, forwards local port 15432 to port 5432 on the database host itself and "
      "reuses one connection for 10 minutes via a multiplexed control socket. Output only the "
      "config, no markdown.", 350, "sshcfgx",
      {"alias": "db-01",
       "spec": {"hostname": "db-01.eu-west.aerelith.internal", "user": "svc-aer",
                "proxyjump": BASTION_JUMP, "stricthostkeychecking": "accept-new",
                "forwardagent": "no", "controlmaster": "auto", "controlpersist": "600"},
       "pats": [r"LocalForward\s+15432\s+(localhost|127\.0\.0\.1):5432"]},
      "Host db-01\n    HostName db-01.eu-west.aerelith.internal\n    User svc-aer\n"
      "    IdentityFile ~/.ssh/aer_ed25519\n    ProxyJump " + BASTION_JUMP + "\n"
      "    StrictHostKeyChecking accept-new\n    ForwardAgent no\n"
      "    ServerAliveInterval 30\n    LocalForward 15432 localhost:5432\n"
      "    ControlMaster auto\n    ControlPath ~/.ssh/cm-%r@%h:%p\n    ControlPersist 10m\n"),

    P("x-ssh-4", DEPTHS[3],
      "Give the command that opens the `db-01` tunnel in the background without running any "
      "remote command. Reply with a single shell command only, no explanation, no markdown.",
      200, "rubricx",
      {"must": [r"\bssh\b", r"db-01", r"-\w*f|\-f\b", r"-\w*N|\-N\b"], "must_not": []},
      "ssh -fN db-01"),

    P("x-ssh-5", DEPTHS[4],
      "Write one OpenSSH config block that applies the standard internal-host rules to every "
      "host in the internal domain at once, using a pattern rather than a single alias. "
      "Output only the config, no markdown.", 350, "sshcfgx",
      {"alias": "search-07.eu-west.aerelith.internal",
       "spec": {"user": "svc-aer", "proxyjump": BASTION_JUMP,
                "stricthostkeychecking": "accept-new", "forwardagent": "no",
                "serveraliveinterval": "30"},
       "pats": [r"Host\s+\*\.eu-west\.aerelith\.internal"]},
      "Host *.eu-west.aerelith.internal\n    User svc-aer\n"
      "    IdentityFile ~/.ssh/aer_ed25519\n    ProxyJump " + BASTION_JUMP + "\n"
      "    StrictHostKeyChecking accept-new\n    ForwardAgent no\n"
      "    ServerAliveInterval 30\n"),
]


# =========================================================== GitHub Actions
GH_INTRO = [
    ("CI now. We run on self-hosted hardware, so a workflow copied from a blog post will not "
     "work here. The house template:\n\n"
     "```yaml\npermissions:\n  contents: read          # mandatory top-level, we deny by "
     "default\nconcurrency:\n  group: ${{ github.workflow }}-${{ github.ref }}\n"
     "  cancel-in-progress: true\njobs:\n  <name>:\n    runs-on: aer-linux-x64   # our runner "
     "label; ubuntu-latest does not exist in this org\n    steps:\n"
     "      - uses: actions/checkout@v4\n```\n\n"
     "The registry credential is the repository secret `AER_REGISTRY_TOKEN`.",
     "Read. Top-level `permissions: contents: read`, the concurrency block, `runs-on: "
     "aer-linux-x64`, `actions/checkout@v4`, and `AER_REGISTRY_TOKEN` for the registry."),

    ("Two more things and then we can start:\n\n"
     "1. The default branch is `trunk`, so branch filters name `trunk`, not `main`.\n"
     "2. Every workflow file must contain the `permissions` and `concurrency` blocks above. "
     "A PR that omits either is auto-rejected by our policy check, so include them even when "
     "I don't restate them.\n\n"
     "Understood?",
     "Understood — filter on `trunk`, and always emit the `permissions` and `concurrency` "
     "blocks."),
]

_GH = "{p} Output only the YAML, no markdown fences."

GH_PROBES = [
    P("x-gh-1", DEPTHS[0],
      _GH.format(p="Write a workflow named `test` that runs `make test` on every push to the "
                   "default branch and on every pull request targeting it."),
      600, "yamlx",
      "assert d.get('permissions', {}).get('contents') == 'read', 'permissions'\n"
      "assert 'cancel-in-progress' in st_all, 'concurrency'\n"
      "assert 'aer-linux-x64' in st and 'ubuntu' not in st.lower(), 'runner'\n"
      "assert 'trunk' in s and 'main' not in s, 'branch filter'\n"
      "assert 'push' in s and 'pull_request' in s\n"
      "assert 'actions/checkout@v4' in st and 'make test' in st\n",
      "permissions:\n  contents: read\nconcurrency:\n"
      "  group: ${{ github.workflow }}-${{ github.ref }}\n  cancel-in-progress: true\n"
      "name: test\non:\n  push:\n    branches: [trunk]\n  pull_request:\n"
      "    branches: [trunk]\njobs:\n  test:\n    runs-on: aer-linux-x64\n    steps:\n"
      "      - uses: actions/checkout@v4\n      - run: make test\n"),

    P("x-gh-2", DEPTHS[1],
      _GH.format(p="Write a workflow named `reconcile` that runs `ops/bin/reconcile.sh` every "
                   "night at 04:20 UTC."),
      600, "yamlx",
      "assert d.get('permissions', {}).get('contents') == 'read', 'permissions'\n"
      "assert 'cancel-in-progress' in st_all, 'concurrency'\n"
      "assert 'aer-linux-x64' in st and 'ubuntu' not in st.lower(), 'runner'\n"
      "assert 'schedule' in s and '20 4' in s.replace(\"'\", ''), 'cron'\n"
      "assert 'ops/bin/reconcile.sh' in st\n",
      "permissions:\n  contents: read\nconcurrency:\n"
      "  group: ${{ github.workflow }}-${{ github.ref }}\n  cancel-in-progress: true\n"
      "name: reconcile\non:\n  schedule:\n    - cron: '20 4 * * *'\njobs:\n"
      "  reconcile:\n    runs-on: aer-linux-x64\n    steps:\n"
      "      - uses: actions/checkout@v4\n      - run: ops/bin/reconcile.sh\n"),

    P("x-gh-3", DEPTHS[2],
      _GH.format(p="Write a workflow named `image` that builds the container image and pushes "
                   "it to our registry on every push to the default branch, authenticating "
                   "with the repository's registry credential."),
      650, "yamlx",
      "assert d.get('permissions', {}).get('contents') == 'read', 'permissions'\n"
      "assert 'cancel-in-progress' in st_all, 'concurrency'\n"
      "assert 'aer-linux-x64' in st and 'ubuntu' not in st.lower(), 'runner'\n"
      "assert 'AER_REGISTRY_TOKEN' in st and 'secrets' in st, 'secret'\n"
      "assert 'trunk' in s and 'main' not in s, 'branch filter'\n"
      "assert 'docker' in st.lower() or 'buildx' in st.lower() or 'podman' in st.lower()\n",
      "permissions:\n  contents: read\nconcurrency:\n"
      "  group: ${{ github.workflow }}-${{ github.ref }}\n  cancel-in-progress: true\n"
      "name: image\non:\n  push:\n    branches: [trunk]\njobs:\n  image:\n"
      "    runs-on: aer-linux-x64\n    steps:\n      - uses: actions/checkout@v4\n"
      "      - run: docker login -u aer --password ${{ secrets.AER_REGISTRY_TOKEN }} "
      "registry.aerelith.internal\n      - run: docker build -t "
      "registry.aerelith.internal/aer:${{ github.sha }} .\n"
      "      - run: docker push registry.aerelith.internal/aer:${{ github.sha }}\n"),

    P("x-gh-4", DEPTHS[3],
      _GH.format(p="Write a workflow named `release` with two jobs, `build` then `publish`, "
                   "where publish only starts if build succeeded, triggered only by pushing a "
                   "tag that starts with `rel/`."),
      650, "yamlx",
      "assert d.get('permissions', {}).get('contents') == 'read', 'permissions'\n"
      "assert 'cancel-in-progress' in st_all, 'concurrency'\n"
      "assert 'aer-linux-x64' in st and 'ubuntu' not in st.lower(), 'runner'\n"
      "assert set(['build','publish']) <= set(d['jobs'].keys()), list(d['jobs'])\n"
      "assert 'build' in json.dumps(d['jobs']['publish'].get('needs')), 'needs'\n"
      "assert 'tags' in s and 'rel/' in s, 'tag filter'\n",
      "permissions:\n  contents: read\nconcurrency:\n"
      "  group: ${{ github.workflow }}-${{ github.ref }}\n  cancel-in-progress: true\n"
      "name: release\non:\n  push:\n    tags: ['rel/*']\njobs:\n  build:\n"
      "    runs-on: aer-linux-x64\n    steps:\n      - uses: actions/checkout@v4\n"
      "      - run: make build\n  publish:\n    needs: build\n    runs-on: aer-linux-x64\n"
      "    steps:\n      - uses: actions/checkout@v4\n      - run: make publish\n"),

    P("x-gh-5", DEPTHS[4],
      _GH.format(p="Write a workflow named `migrate` that only runs when a human starts it by "
                   "hand, takes a required `environment` input, gives the job a 20 minute "
                   "cap, and runs `aerctl migrate --env <that input>`."),
      650, "yamlx",
      "assert d.get('permissions', {}).get('contents') == 'read', 'permissions'\n"
      "assert 'cancel-in-progress' in st_all, 'concurrency'\n"
      "assert 'aer-linux-x64' in st and 'ubuntu' not in st.lower(), 'runner'\n"
      "assert 'workflow_dispatch' in s and 'environment' in s, 'dispatch input'\n"
      "assert j.get('timeout-minutes') == 20, j.get('timeout-minutes')\n"
      "assert 'aerctl migrate' in st and 'inputs.environment' in st\n",
      "permissions:\n  contents: read\nconcurrency:\n"
      "  group: ${{ github.workflow }}-${{ github.ref }}\n  cancel-in-progress: true\n"
      "name: migrate\non:\n  workflow_dispatch:\n    inputs:\n      environment:\n"
      "        required: true\n        type: string\njobs:\n  migrate:\n"
      "    runs-on: aer-linux-x64\n    timeout-minutes: 20\n    steps:\n"
      "      - uses: actions/checkout@v4\n"
      "      - run: aerctl migrate --env ${{ inputs.environment }}\n"),
]


# =========================================================== Docs
DOC_INTRO = [
    ("Docs work now. Our glossary is not the industry-standard one, so use ours:\n\n"
     "- **tranche** — a batch of *tenants* processed together in one pass. (Not a batch of "
     "records; that's a *chunk*, and we rarely document those.)\n"
     "- **beacon** — the per-tenant heartbeat record written once per pass.\n"
     "- **flush** — the act of forcing a tranche through ahead of schedule.\n"
     "- **aerctl** — the operator CLI. Subcommands: `tranche`, `beacon`, `release`.\n"
     "- Error codes are always four digits with an `E` prefix: `E1042`, `E2210`.\n"
     "- The current release line is **2026.07**.",
     "Noted the glossary: tranche = batch of tenants, beacon = per-tenant heartbeat, flush = "
     "forced early pass, `aerctl` with `tranche`/`beacon`/`release`, `E####` codes, current "
     "line 2026.07."),

    ("House style for everything you write from here on:\n\n"
     "1. Second person, present tense. Never the future tense — write \"the job retries\", "
     "not \"the job will retry\". Our style checker greps for it.\n"
     "2. Every procedure names the exact `aerctl` command.\n"
     "3. Reference the current release line by number when a section is version-specific.\n"
     "4. No marketing adjectives.\n\n"
     "Ready when you are.",
     "Ready — second person present tense with no future \"will\", exact `aerctl` commands, "
     "and version references to the current line."),
]

DOC_PROBES = [
    P("x-doc-1", DEPTHS[0],
      "Write the CLI reference entry for forcing a tranche through early. Cover what it does, "
      "the exact command, and when an operator should reach for it. Six sentences at most.",
      450, "rubricx",
      {"must": [r"aerctl\s+tranche", r"\bflush\b", r"tranche"],
       "must_not": [r"\bwill\b"]},
      "Use `aerctl tranche flush --id <tranche-id>` to push a tranche through ahead of its "
      "scheduled pass. The command re-runs the pass immediately for every tenant in that "
      "tranche and writes a fresh beacon for each one. Reach for it when a tranche is stuck "
      "behind a slow upstream and you need its tenants current before the next scheduled "
      "pass. The command is idempotent, so a repeat run is safe. It exits non-zero and "
      "reports an `E####` code if the tranche is already mid-pass."),

    P("x-doc-2", DEPTHS[1],
      "Write the troubleshooting section for a tranche that has been stuck in the same state "
      "for more than one pass. Give the operator an ordered diagnosis. Eight sentences at "
      "most.", 500, "rubricx",
      {"must": [r"tranche", r"aerctl", r"beacon"], "must_not": [r"\bwill\b"]},
      "First confirm the tranche is genuinely stuck: run `aerctl tranche status --id "
      "<tranche-id>` and compare the last pass timestamp against the schedule. Next check "
      "whether any beacon was written during that window with `aerctl beacon list --tranche "
      "<tranche-id>`; a tranche that writes no beacon at all is blocked before the pass "
      "starts. Read the error code on the failed pass — an `E1###` code points at input data "
      "and an `E2###` code points at the downstream service. If the upstream is healthy, "
      "force the pass with `aerctl tranche flush --id <tranche-id>` and watch for a beacon "
      "within one minute. If the flush also stalls, escalate rather than retrying a third "
      "time."),

    P("x-doc-3", DEPTHS[2],
      "Write the two-paragraph introduction to the release notes for the current release "
      "line, describing how operators upgrade and what they check afterwards.", 500, "rubricx",
      {"must": [r"2026\.07", r"aerctl\s+release"], "must_not": []},
      "The 2026.07 release line changes how tranches are scheduled and how beacons are "
      "retained. You upgrade with `aerctl release apply --to 2026.07` on one node at a time, "
      "waiting for each node to report healthy before you move to the next. The command "
      "refuses to start while a tranche is mid-pass, so drain the schedule first.\n\n"
      "After the upgrade you check three things: that every tenant has a beacon newer than "
      "the upgrade timestamp, that no pass reports an `E####` code it did not report before, "
      "and that the schedule matches the one recorded before you started. If any check fails, "
      "roll back with `aerctl release rollback --to <previous-tag>` before you upgrade "
      "another node."),

    P("x-doc-4", DEPTHS[3],
      "Document the beacon record: what it is, when it is written, and what an operator "
      "concludes from a missing one. Six sentences at most.", 450, "rubricx",
      {"must": [r"beacon", r"tenant", r"aerctl\s+beacon"], "must_not": []},
      "A beacon is the heartbeat record the platform writes for a single tenant once per "
      "pass. Each beacon records the tenant id, the tranche it belonged to, the pass "
      "timestamp, and the outcome. You list them with `aerctl beacon list --tenant "
      "<tenant-id>`. A missing beacon means the tenant's pass did not complete, not that the "
      "tenant is idle — an idle tenant still gets a beacon with a zero-work outcome. When a "
      "beacon is missing for one tenant but present for the rest of its tranche, the fault is "
      "tenant-specific data rather than the tranche itself. Two consecutive missing beacons "
      "for the same tenant is an escalation."),

    P("x-doc-5", DEPTHS[4],
      "Write the runbook step an on-call engineer follows when a reconciliation pass fails "
      "with an error code. Include what to record and when to stop retrying. Eight sentences "
      "at most.", 500, "rubricx",
      # Originally demanded a literal E#### code. The prompt only says the pass
      # "fails with an error code" -- it never asks the model to invent one, so
      # that requirement tested nothing and every model failed it identically.
      {"must": [r"error code|E\d{4}", r"aerctl", r"tranche|beacon"],
       "must_not": [r"\bwill\b"]},
      "Record the exact error code — for example `E2210` — together with the tranche id and "
      "the pass timestamp before you touch anything. Run `aerctl tranche status --id "
      "<tranche-id>` and copy the output into the incident note. Codes in the `E1###` range "
      "mean the input data is malformed, so the pass does not succeed on a retry; codes in "
      "the `E2###` range mean a downstream service refused the write and a retry is "
      "reasonable. Retry once with `aerctl tranche flush --id <tranche-id>`. If the second "
      "attempt fails with the same code, stop and escalate; a third attempt only widens the "
      "gap in the beacon history. Note in the incident whether any beacon was written during "
      "the failed pass, because that distinguishes a partial pass from a pass that never "
      "started."),
]


# =========================================================== React Native
RN_INTRO = [
    ("Mobile app now. Two things every component in `mobile/src` uses:\n\n"
     "```tsx\n// mobile/src/theme.ts\nexport function useAerTheme(): {\n"
     "  color: { ink: string; muted: string; accent: string; bg: string; danger: string };\n"
     "  space: { sm: number; md: number; lg: number };\n"
     "  radius: { sm: number; md: number };\n};\n\n"
     "// mobile/src/components/AerButton.tsx\nexport function AerButton(props: {\n"
     "  label: string;\n  onPress: () => void;\n  variant?: 'primary' | 'ghost';\n"
     "}): JSX.Element;\n```",
     "Read — `useAerTheme()` from `../theme` gives `color`, `space` and `radius` scales, and "
     "`AerButton` from `../components/AerButton` takes `label`, `onPress` and an optional "
     "`variant`."),

    ("Component rules, enforced by lint:\n\n"
     "1. No colour literals. Every colour comes from `useAerTheme().color`. A `#` followed by "
     "hex in a component file fails the build.\n"
     "2. No `StyleSheet.create`. We pass plain inline style objects built from the theme "
     "scales, because the theme switches at runtime.\n"
     "3. Function components only, TypeScript, props typed inline or with an exported "
     "interface.\n"
     "4. Any tappable thing that looks like a button IS `AerButton` — never a bare "
     "`TouchableOpacity`.\n\n"
     "Clear?",
     "Clear — theme colours only, no `StyleSheet.create`, typed function components, and "
     "`AerButton` for anything button-shaped."),
]

_RN = "{p} Output only the code, no explanation."

RN_PROBES = [
    P("x-rn-1", DEPTHS[0],
      _RN.format(p="Write `AerEmptyState`, a component taking `title`, `message` and "
                   "`onRetry`, showing the two strings stacked with a primary retry button "
                   "underneath."),
      600, "rubricx",
      {"must": [r"useAerTheme", r"AerButton", r"onRetry", r"theme\.color\.",
                r"export\s+function\s+AerEmptyState|export\s+const\s+AerEmptyState"],
       "must_not": [r"#[0-9a-fA-F]{3,8}\b", r"StyleSheet\.create"]},
      "import React from 'react';\nimport { View, Text } from 'react-native';\n"
      "import { useAerTheme } from '../theme';\n"
      "import { AerButton } from '../components/AerButton';\n\n"
      "export function AerEmptyState({ title, message, onRetry }: { title: string; "
      "message: string; onRetry: () => void }) {\n  const theme = useAerTheme();\n"
      "  return (\n    <View style={{ padding: theme.space.lg, gap: theme.space.sm }}>\n"
      "      <Text style={{ color: theme.color.ink }}>{title}</Text>\n"
      "      <Text style={{ color: theme.color.muted }}>{message}</Text>\n"
      "      <AerButton label=\"Try again\" onPress={onRetry} variant=\"primary\" />\n"
      "    </View>\n  );\n}\n"),

    P("x-rn-2", DEPTHS[1],
      _RN.format(p="Write `AerBadge`, taking `label` and a `tone` of 'neutral' | 'danger', "
                   "rendering a rounded pill whose text colour follows the tone."),
      600, "rubricx",
      {"must": [r"useAerTheme", r"tone", r"theme\.color\.danger", r"theme\.radius\.",
                r"export\s+function\s+AerBadge|export\s+const\s+AerBadge"],
       "must_not": [r"#[0-9a-fA-F]{3,8}\b", r"StyleSheet\.create"]},
      "import React from 'react';\nimport { View, Text } from 'react-native';\n"
      "import { useAerTheme } from '../theme';\n\n"
      "export function AerBadge({ label, tone }: { label: string; tone: 'neutral' | 'danger' "
      "}) {\n  const theme = useAerTheme();\n"
      "  const fg = tone === 'danger' ? theme.color.danger : theme.color.muted;\n"
      "  return (\n    <View style={{ paddingHorizontal: theme.space.sm, "
      "paddingVertical: theme.space.sm, borderRadius: theme.radius.md, "
      "backgroundColor: theme.color.bg }}>\n"
      "      <Text style={{ color: fg }}>{label}</Text>\n    </View>\n  );\n}\n"),

    P("x-rn-3", DEPTHS[2],
      _RN.format(p="Write `AerListRow`, taking `label`, `value` and `onPress`, laying the "
                   "label out on the left and the value on the right in one row, the whole "
                   "row tappable."),
      600, "rubricx",
      {"must": [r"useAerTheme", r"theme\.color\.", r"onPress",
                r"space-between|justifyContent",
                r"export\s+function\s+AerListRow|export\s+const\s+AerListRow"],
       "must_not": [r"#[0-9a-fA-F]{3,8}\b", r"StyleSheet\.create"]},
      "import React from 'react';\nimport { Pressable, View, Text } from 'react-native';\n"
      "import { useAerTheme } from '../theme';\n\n"
      "export function AerListRow({ label, value, onPress }: { label: string; value: string; "
      "onPress: () => void }) {\n  const theme = useAerTheme();\n"
      "  return (\n    <Pressable onPress={onPress}>\n"
      "      <View style={{ flexDirection: 'row', justifyContent: 'space-between', "
      "padding: theme.space.md }}>\n"
      "        <Text style={{ color: theme.color.ink }}>{label}</Text>\n"
      "        <Text style={{ color: theme.color.muted }}>{value}</Text>\n"
      "      </View>\n    </Pressable>\n  );\n}\n"),

    P("x-rn-4", DEPTHS[3],
      _RN.format(p="Write `AerSection`, taking `heading` and `children`, rendering the heading "
                   "above its children with the standard large spacing around the block."),
      600, "rubricx",
      {"must": [r"useAerTheme", r"children", r"theme\.space\.lg", r"heading",
                r"export\s+function\s+AerSection|export\s+const\s+AerSection"],
       "must_not": [r"#[0-9a-fA-F]{3,8}\b", r"StyleSheet\.create"]},
      "import React from 'react';\nimport { View, Text } from 'react-native';\n"
      "import { useAerTheme } from '../theme';\n\n"
      "export function AerSection({ heading, children }: { heading: string; "
      "children: React.ReactNode }) {\n  const theme = useAerTheme();\n"
      "  return (\n    <View style={{ padding: theme.space.lg, gap: theme.space.sm }}>\n"
      "      <Text style={{ color: theme.color.ink }}>{heading}</Text>\n"
      "      {children}\n    </View>\n  );\n}\n"),

    P("x-rn-5", DEPTHS[4],
      _RN.format(p="Write `AerConfirmBar`, taking `confirmLabel`, `onConfirm` and `onCancel`, "
                   "rendering a cancel action and a confirm action side by side with the "
                   "confirm one emphasised."),
      650, "rubricx",
      {"must": [r"useAerTheme", r"AerButton", r"onConfirm", r"onCancel",
                r"variant=[\"']primary[\"']", r"variant=[\"']ghost[\"']",
                r"export\s+function\s+AerConfirmBar|export\s+const\s+AerConfirmBar"],
       "must_not": [r"#[0-9a-fA-F]{3,8}\b", r"StyleSheet\.create", r"TouchableOpacity"]},
      "import React from 'react';\nimport { View } from 'react-native';\n"
      "import { useAerTheme } from '../theme';\n"
      "import { AerButton } from '../components/AerButton';\n\n"
      "export function AerConfirmBar({ confirmLabel, onConfirm, onCancel }: "
      "{ confirmLabel: string; onConfirm: () => void; onCancel: () => void }) {\n"
      "  const theme = useAerTheme();\n"
      "  return (\n    <View style={{ flexDirection: 'row', gap: theme.space.sm, "
      "padding: theme.space.md }}>\n"
      "      <AerButton label=\"Cancel\" onPress={onCancel} variant=\"ghost\" />\n"
      "      <AerButton label={confirmLabel} onPress={onConfirm} variant=\"primary\" />\n"
      "    </View>\n  );\n}\n"),
]


# =========================================================== RAG
RAG_INTRO = [
    ("I'm going to paste the Aerelith operations runbook a section at a time. Read each one "
     "and hold on to it; I'll ask about any of it later.\n\n"
     "## 1. Scheduled work\n\n"
     "The billing reconciliation job runs once daily at **03:17 UTC**. The offset from the "
     "hour is deliberate: it keeps the job clear of the 03:00 tranche boundary, when the "
     "scheduler is busiest. The beacon retention sweep runs at 05:00 UTC. The quota "
     "recalculation runs hourly at 12 minutes past.\n\n"
     "## 2. Escalation\n\n"
     "The escalation path has exactly three steps. First the primary on-call engineer. If "
     "unacknowledged after 15 minutes, it goes to the platform lead, **Rhea Vance**. If still "
     "unacknowledged after a further 15 minutes, it goes to the CTO. There is no secondary "
     "on-call rotation; the platform lead is the second step.",
     "Read sections 1 and 2 — reconciliation at 03:17 UTC, retention sweep at 05:00, hourly "
     "quota recalc at :12, and a three-step escalation ending at the CTO."),

    ("## 3. Vault\n\n"
     "The credential vault is sealed at rest. Unsealing requires a quorum of **3 of the 5** "
     "key holders. Key holders are drawn from the platform and security teams; no single team "
     "holds three keys, so an unseal always crosses a team boundary. Re-sealing happens "
     "automatically 30 minutes after the last privileged operation.\n\n"
     "## 4. Release and rollback\n\n"
     "Roll back with `aerctl release rollback --to <tag>`. This is **not safe to run during a "
     "tranche flush** — the rollback and the flush both take the schedule lock, and the loser "
     "aborts mid-write. Drain the flush first, confirm with `aerctl tranche status`, and only "
     "then roll back. Rollback across more than one release line is not supported; step back "
     "one line at a time.",
     "Read sections 3 and 4 — a 3-of-5 unseal quorum with automatic re-seal after 30 minutes, "
     "and rollback via `aerctl release rollback --to <tag>` which must not overlap a tranche "
     "flush."),

    ("## 5. Plan limits\n\n"
     "The free plan is capped at **2,000 beacons per day** per tenant. The pro plan is capped "
     "at 250,000 per day. Exceeding the cap does not drop data: the tranche still completes, "
     "but the overflow is billed at the metered rate and the tenant's dashboard shows an "
     "overage banner until the next UTC midnight. There is no burst allowance and no way to "
     "raise the cap from the CLI; a plan change is the only mechanism.",
     "Read section 5 — free is 2,000 beacons/day, pro is 250,000, overflow is billed rather "
     "than dropped, and only a plan change lifts the cap."),
]

RAG_PROBES = [
    P("x-rag-1", DEPTHS[0],
      "From the runbook: at what time does the billing reconciliation job run? Answer in one "
      "sentence.", 120, "ragx",
      {"must": [r"03:?17"], "unanswerable": False}, "It runs daily at 03:17 UTC."),

    P("x-rag-2", DEPTHS[1],
      "From the runbook: how many key holders have to take part to unseal the credential "
      "vault? Answer in one sentence.", 120, "ragx",
      {"must": [r"\b3\b|three"], "unanswerable": False},
      "Three of the five key holders are required."),

    P("x-rag-3", DEPTHS[2],
      "From the runbook: who is the second step in the escalation path? Give the name.",
      120, "ragx", {"must": [r"Rhea\s+Vance"], "unanswerable": False},
      "The platform lead, Rhea Vance."),

    P("x-rag-4", DEPTHS[3],
      "From the runbook: what is the daily beacon cap on the free plan, and what happens when "
      "a tenant exceeds it? Answer in two sentences.", 160, "ragx",
      {"must": [r"2[,.]?000", r"bill|meter|overage"], "unanswerable": False},
      "The free plan is capped at 2,000 beacons per day. Exceeding it does not drop data — "
      "the overflow is billed at the metered rate and an overage banner shows until the next "
      "UTC midnight."),

    P("x-rag-5", DEPTHS[4],
      "From the runbook: what percentage SLA credit does a customer receive for a Sev-1 "
      "incident lasting more than four hours? Answer in one sentence.", 140, "ragx",
      {"must": [], "unanswerable": True},
      "The runbook does not specify SLA credit percentages."),
]


PART2 = {
    "Bash": {"intro": SH_INTRO, "probes": SH_PROBES},
    "Git": {"intro": GIT_INTRO, "probes": GIT_PROBES},
    "SSH": {"intro": SSH_INTRO, "probes": SSH_PROBES},
    "GitHub": {"intro": GH_INTRO, "probes": GH_PROBES},
    "Docs": {"intro": DOC_INTRO, "probes": DOC_PROBES},
    "ReactNative": {"intro": RN_INTRO, "probes": RN_PROBES},
    "RAG": {"intro": RAG_INTRO, "probes": RAG_PROBES},
}

REFUSAL = [r"not (specified|stated|mentioned|covered|given|documented|in the)",
           r"does not (specify|state|mention|cover|say|define|document)",
           r"no (information|mention|section|figure|percentage|detail)",
           r"isn'?t (specified|stated|mentioned|covered|in the)",
           r"can'?t (find|determine|tell)", r"cannot (find|determine|tell)",
           r"unable to (find|determine)", r"the runbook does not",
           r"not (present|available) in"]
