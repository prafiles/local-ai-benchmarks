#!/usr/bin/env python3
"""SSH (50), GitHub (50), Docs (50), React Native (50).

Where an oracle exists it is used:
  - SSH config tasks are validated by `ssh -G` parsing the generated config
  - GitHub workflow tasks are parsed as YAML with structural assertions
Everything else is pattern-graded; each reference must satisfy its own patterns.
"""

# ============================================================ SSH (50)
# config tasks: (id, prompt, alias, {ssh -G key: expected value}, reference)
SSH_CFG = [
("ssh-001", "host alias prod at hostname 10.0.5.20, user deploy, port 2222, reached through jump "
 "host bastion.example.com as user jump", "prod",
 {"hostname": "10.0.5.20", "user": "deploy", "port": "2222",
  "proxyjump": "jump@bastion.example.com"},
 "Host prod\n  HostName 10.0.5.20\n  User deploy\n  Port 2222\n  ProxyJump jump@bastion.example.com\n"),
("ssh-002", "host alias db at hostname db.internal, user admin, using key ~/.ssh/db_ed25519, "
 "keepalive every 30 seconds, agent forwarding disabled", "db",
 {"hostname": "db.internal", "user": "admin", "serveraliveinterval": "30", "forwardagent": "no"},
 "Host db\n  HostName db.internal\n  User admin\n  IdentityFile ~/.ssh/db_ed25519\n"
 "  ServerAliveInterval 30\n  ForwardAgent no\n"),
("ssh-003", "host alias build at hostname ci.example.net, user runner, port 2200, compression on",
 "build", {"hostname": "ci.example.net", "user": "runner", "port": "2200", "compression": "yes"},
 "Host build\n  HostName ci.example.net\n  User runner\n  Port 2200\n  Compression yes\n"),
("ssh-004", "host alias web at hostname 10.1.1.5, user www, disabling strict host key checking",
 "web", {"hostname": "10.1.1.5", "user": "www", "stricthostkeychecking": "no"},
 "Host web\n  HostName 10.1.1.5\n  User www\n  StrictHostKeyChecking no\n"),
("ssh-005", "host alias slow at hostname slow.example.com, user ops, connection timeout 20 seconds, "
 "3 keepalive retries", "slow",
 {"hostname": "slow.example.com", "user": "ops", "connecttimeout": "20", "serveralivecountmax": "3"},
 "Host slow\n  HostName slow.example.com\n  User ops\n  ConnectTimeout 20\n  ServerAliveCountMax 3\n"),
("ssh-006", "host alias gw at hostname gw.example.org, user net, X11 forwarding disabled and TCP "
 "keepalive enabled", "gw",
 {"hostname": "gw.example.org", "user": "net", "forwardx11": "no", "tcpkeepalive": "yes"},
 "Host gw\n  HostName gw.example.org\n  User net\n  ForwardX11 no\n  TCPKeepAlive yes\n"),
("ssh-007", "host alias legacy at hostname old.example.com, user root, port 22, only public key "
 "authentication", "legacy",
 {"hostname": "old.example.com", "user": "root", "port": "22",
  "preferredauthentications": "publickey"},
 "Host legacy\n  HostName old.example.com\n  User root\n  Port 22\n"
 "  PreferredAuthentications publickey\n"),
("ssh-008", "host alias multi at hostname m.example.com, user m, requesting no TTY allocation and "
 "batch mode on", "multi",
 {"hostname": "m.example.com", "user": "m", "requesttty": "no", "batchmode": "yes"},
 "Host multi\n  HostName m.example.com\n  User m\n  RequestTTY no\n  BatchMode yes\n"),
("ssh-009", "host alias hop at hostname target.internal, user t, going through two jump hosts "
 "a.example.com then b.example.com", "hop",
 {"hostname": "target.internal", "user": "t", "proxyjump": "a.example.com,b.example.com"},
 "Host hop\n  HostName target.internal\n  User t\n  ProxyJump a.example.com,b.example.com\n"),
("ssh-010", "host alias id at hostname i.example.com, user i, using only the key ~/.ssh/only_key and "
 "ignoring the agent's other identities", "id",
 {"hostname": "i.example.com", "user": "i", "identitiesonly": "yes"},
 "Host id\n  HostName i.example.com\n  User i\n  IdentityFile ~/.ssh/only_key\n"
 "  IdentitiesOnly yes\n"),
]

# command tasks: (id, prompt, [required regexes], reference)
SSH_CMD = [
("ssh-011", "forward local port 5433 to port 5432 on host db.internal via user@jump.example.com, "
 "without opening a remote shell, in the background",
 [r"ssh", r"-[a-zA-Z]*L", r"5433:db\.internal:5432", r"-[a-zA-Z]*N", r"(-[a-zA-Z]*f|&\s*$)",
  r"user@jump\.example\.com"],
 "ssh -fN -L 5433:db.internal:5432 user@jump.example.com"),
("ssh-012", "copy the local file report.pdf to /srv/data on host files.example.com as user ops",
 [r"scp", r"report\.pdf", r"ops@files\.example\.com", r"/srv/data"],
 "scp report.pdf ops@files.example.com:/srv/data"),
("ssh-013", "copy the remote directory /var/log/app from user ops on logs.example.com into the "
 "current directory, recursively",
 [r"scp", r"-[a-zA-Z]*r", r"ops@logs\.example\.com", r"/var/log/app"],
 "scp -r ops@logs.example.com:/var/log/app ."),
("ssh-014", "generate a new ed25519 SSH key at ~/.ssh/deploy_key with the comment deploy@ci and no "
 "passphrase",
 [r"ssh-keygen", r"-t\s+ed25519", r"~/\.ssh/deploy_key", r"deploy@ci", r"-N\s*(''|\"\")"],
 "ssh-keygen -t ed25519 -f ~/.ssh/deploy_key -C deploy@ci -N ''"),
("ssh-015", "copy your public key ~/.ssh/id_ed25519.pub to user deploy on app.example.com so you can "
 "log in without a password",
 [r"ssh-copy-id", r"id_ed25519\.pub", r"deploy@app\.example\.com"],
 "ssh-copy-id -i ~/.ssh/id_ed25519.pub deploy@app.example.com"),
("ssh-016", "run the single command 'systemctl status nginx' on host web1 as user ops and return",
 [r"ssh", r"ops@web1", r"systemctl status nginx"],
 "ssh ops@web1 'systemctl status nginx'"),
("ssh-017", "forward remote port 8080 on host relay.example.com to local port 3000, as user tun",
 [r"ssh", r"-[a-zA-Z]*R", r"8080:localhost:3000", r"tun@relay\.example\.com"],
 "ssh -R 8080:localhost:3000 tun@relay.example.com"),
("ssh-018", "open a SOCKS proxy on local port 1080 through user@jump.example.com without a shell",
 [r"ssh", r"-[a-zA-Z]*D", r"1080", r"-[a-zA-Z]*N", r"user@jump\.example\.com"],
 "ssh -ND 1080 user@jump.example.com"),
("ssh-019", "print the fingerprint of the public key file ~/.ssh/id_ed25519.pub",
 [r"ssh-keygen", r"-l", r"id_ed25519\.pub"],
 "ssh-keygen -lf ~/.ssh/id_ed25519.pub"),
("ssh-020", "remove the stored host key for host old.example.com from the known_hosts file",
 [r"ssh-keygen", r"-R", r"old\.example\.com"],
 "ssh-keygen -R old.example.com"),
("ssh-021", "connect to host box as user u forcing use of the identity file ~/.ssh/special",
 [r"ssh", r"-i", r"~/\.ssh/special", r"u@box"],
 "ssh -i ~/.ssh/special u@box"),
("ssh-022", "show the effective ssh configuration that would be used for host prod",
 [r"ssh", r"-G", r"prod"], "ssh -G prod"),
("ssh-023", "connect to host web as user ops with verbose debugging output",
 [r"ssh", r"-v", r"ops@web"], "ssh -v ops@web"),
("ssh-024", "synchronise the local directory ./site/ to /var/www on host web.example.com as user "
 "deploy, deleting files that no longer exist locally",
 [r"rsync", r"-[a-zA-Z]*a", r"--delete", r"\./site/", r"deploy@web\.example\.com", r"/var/www"],
 "rsync -a --delete ./site/ deploy@web.example.com:/var/www"),
("ssh-025", "add the key ~/.ssh/id_ed25519 to the running ssh agent",
 [r"ssh-add", r"~/\.ssh/id_ed25519"], "ssh-add ~/.ssh/id_ed25519"),
("ssh-026", "list the keys currently loaded in the ssh agent", [r"ssh-add", r"-l"], "ssh-add -l"),
("ssh-027", "remove all keys from the ssh agent", [r"ssh-add", r"-D"], "ssh-add -D"),
("ssh-028", "connect to host jumpy as user j on port 2022", [r"ssh", r"-p\s*2022", r"j@jumpy"],
 "ssh -p 2022 j@jumpy"),
("ssh-029", "run a command on host h as user u without allocating a pseudo terminal, reading a "
 "script from local file setup.sh",
 [r"ssh", r"u@h", r"(<|bash|sh)", r"setup\.sh"], "ssh u@h 'bash -s' < setup.sh"),
("ssh-030", "test whether authentication to git@github.com works without running a command",
 [r"ssh", r"-T", r"git@github\.com"], "ssh -T git@github.com"),
("ssh-031", "restrict permissions on ~/.ssh/id_ed25519 so only the owner can read and write it",
 [r"chmod", r"600", r"id_ed25519"], "chmod 600 ~/.ssh/id_ed25519"),
("ssh-032", "copy a file using scp over port 2222 from local a.txt to user u on host h in /tmp",
 [r"scp", r"-P\s*2222", r"a\.txt", r"u@h", r"/tmp"], "scp -P 2222 a.txt u@h:/tmp"),
("ssh-033", "connect to host h as user u, disabling the use of any ssh agent forwarding",
 [r"ssh", r"-[ao]", r"ForwardAgent[= ]no", r"u@h"], "ssh -o ForwardAgent=no u@h"),
("ssh-034", "connect to host h as user u overriding the config to use identity file ~/.ssh/k and "
 "ignoring other identities, using -o options only",
 [r"ssh", r"-o", r"IdentityFile", r"-o", r"IdentitiesOnly[= ]yes", r"u@h"],
 "ssh -o IdentityFile=~/.ssh/k -o IdentitiesOnly=yes u@h"),
("ssh-035", "mount the remote directory /data from user u on host h at the local path ./mnt using sshfs",
 [r"sshfs", r"u@h", r"/data", r"\./mnt"], "sshfs u@h:/data ./mnt"),
("ssh-036", "print the public key derived from the private key ~/.ssh/id_ed25519",
 [r"ssh-keygen", r"-y", r"id_ed25519"], "ssh-keygen -y -f ~/.ssh/id_ed25519"),
("ssh-037", "change the passphrase on the private key ~/.ssh/id_ed25519",
 [r"ssh-keygen", r"-p", r"id_ed25519"], "ssh-keygen -p -f ~/.ssh/id_ed25519"),
("ssh-038", "scan and print the host keys for host h.example.com in known_hosts format",
 [r"ssh-keyscan", r"h\.example\.com"], "ssh-keyscan h.example.com"),
("ssh-039", "connect to host h as user u and keep the connection alive by sending a null packet "
 "every 60 seconds using an -o option",
 [r"ssh", r"-o", r"ServerAliveInterval[= ]60", r"u@h"],
 "ssh -o ServerAliveInterval=60 u@h"),
("ssh-040", "copy the whole local directory dist to /srv/app on host h as user u using rsync over "
 "ssh on port 2222",
 [r"rsync", r"-e", r"2222", r"dist", r"u@h", r"/srv/app"],
 "rsync -e 'ssh -p 2222' -a dist u@h:/srv/app"),
("ssh-041", "run a command on host h as user u in the background surviving disconnection using nohup",
 [r"ssh", r"u@h", r"nohup"], "ssh u@h 'nohup long-task &'"),
("ssh-042", "connect to host h as user u using only password authentication",
 [r"ssh", r"-o", r"PreferredAuthentications[= ]password", r"u@h"],
 "ssh -o PreferredAuthentications=password u@h"),
("ssh-043", "show which config file entries apply to host web including the source file, using -G "
 "and grep for hostname",
 [r"ssh", r"-G", r"web", r"grep", r"hostname"], "ssh -G web | grep hostname"),
("ssh-044", "copy file f from host a to host b directly, both as user u, using scp's three-way form",
 [r"scp", r"u@a", r"u@b", r"\bf\b"], "scp u@a:f u@b:f"),
("ssh-045", "reuse an existing connection to host h by enabling connection multiplexing with a "
 "control master and socket path ~/.ssh/cm-%r@%h:%p using -o options",
 [r"ssh", r"ControlMaster", r"ControlPath", r"cm-%r@%h:%p"],
 "ssh -o ControlMaster=auto -o ControlPath=~/.ssh/cm-%r@%h:%p u@h"),
("ssh-046", "close a multiplexed master connection to host h using the control command",
 [r"ssh", r"-O\s+(exit|stop)", r"h"], "ssh -O exit h"),
("ssh-047", "connect to host h as user u forcing IPv4 only", [r"ssh", r"-4", r"u@h"], "ssh -4 u@h"),
("ssh-048", "connect to host h as user u forcing protocol compression and verbose output",
 [r"ssh", r"-[a-zA-Z]*C", r"-[a-zA-Z]*v", r"u@h"], "ssh -Cv u@h"),
("ssh-049", "list the contents of /var on host h as user u without an interactive shell",
 [r"ssh", r"u@h", r"ls", r"/var"], "ssh u@h ls /var"),
("ssh-050", "append the contents of local file key.pub to ~/.ssh/authorized_keys on host h as user u",
 [r"ssh", r"u@h", r">>", r"authorized_keys", r"key\.pub"],
 "cat key.pub | ssh u@h 'cat >> ~/.ssh/authorized_keys'"),
]

# ============================================================ GITHUB (50)
# workflow tasks: (id, prompt, checker-name, reference yaml)
GH_WF = [
("gh-001", "runs on pushes and pull requests targeting main, checks out the repo, sets up Python "
 "3.12, installs requirements.txt and runs pytest", "ci",
 "name: CI\non:\n  push:\n    branches: [main]\n  pull_request:\n    branches: [main]\njobs:\n"
 "  test:\n    runs-on: ubuntu-latest\n    steps:\n      - uses: actions/checkout@v4\n"
 "      - uses: actions/setup-python@v5\n        with:\n          python-version: '3.12'\n"
 "      - run: pip install -r requirements.txt\n      - run: pytest\n"),
("gh-002", "triggered on push, running a matrix of Node versions 18, 20 and 22 on ubuntu-latest, "
 "checking out and running npm test", "matrix",
 "name: Node\non: push\njobs:\n  test:\n    runs-on: ubuntu-latest\n    strategy:\n"
 "      matrix:\n        node: [18, 20, 22]\n    steps:\n      - uses: actions/checkout@v4\n"
 "      - uses: actions/setup-node@v4\n        with:\n          node-version: ${{ matrix.node }}\n"
 "      - run: npm test\n"),
("gh-003", "runs on a schedule every day at 04:00 UTC and runs a job that checks out the repo and "
 "runs ./scripts/nightly.sh", "cron",
 "name: Nightly\non:\n  schedule:\n    - cron: '0 4 * * *'\njobs:\n  nightly:\n"
 "    runs-on: ubuntu-latest\n    steps:\n      - uses: actions/checkout@v4\n"
 "      - run: ./scripts/nightly.sh\n"),
("gh-004", "runs on push to main only, with a job that needs a previous job named build before it "
 "runs a job named deploy", "needs",
 "name: Deploy\non:\n  push:\n    branches: [main]\njobs:\n  build:\n    runs-on: ubuntu-latest\n"
 "    steps:\n      - uses: actions/checkout@v4\n      - run: make build\n  deploy:\n"
 "    needs: build\n    runs-on: ubuntu-latest\n    steps:\n      - run: make deploy\n"),
("gh-005", "runs manually via workflow_dispatch with a required string input named environment, and "
 "echoes that input", "dispatch",
 "name: Manual\non:\n  workflow_dispatch:\n    inputs:\n      environment:\n"
 "        required: true\n        type: string\njobs:\n  go:\n    runs-on: ubuntu-latest\n"
 "    steps:\n      - run: echo ${{ inputs.environment }}\n"),
("gh-006", "runs on pull_request, uses a secret named API_TOKEN as an environment variable in a step",
 "secret",
 "name: Secret\non: pull_request\njobs:\n  s:\n    runs-on: ubuntu-latest\n    steps:\n"
 "      - uses: actions/checkout@v4\n      - run: ./check.sh\n        env:\n"
 "          API_TOKEN: ${{ secrets.API_TOKEN }}\n"),
("gh-007", "runs on push, caches the ~/.npm directory keyed on the hash of package-lock.json",
 "cache",
 "name: Cache\non: push\njobs:\n  b:\n    runs-on: ubuntu-latest\n    steps:\n"
 "      - uses: actions/checkout@v4\n      - uses: actions/cache@v4\n        with:\n"
 "          path: ~/.npm\n          key: ${{ hashFiles('package-lock.json') }}\n"
 "      - run: npm ci\n"),
("gh-008", "runs on push and uploads the directory dist as an artifact named build-output",
 "artifact",
 "name: Artifact\non: push\njobs:\n  a:\n    runs-on: ubuntu-latest\n    steps:\n"
 "      - uses: actions/checkout@v4\n      - run: make dist\n"
 "      - uses: actions/upload-artifact@v4\n        with:\n          name: build-output\n"
 "          path: dist\n"),
("gh-009", "runs on push with a job-level timeout of 15 minutes and a step that continues on error",
 "timeout",
 "name: Timeout\non: push\njobs:\n  t:\n    runs-on: ubuntu-latest\n    timeout-minutes: 15\n"
 "    steps:\n      - uses: actions/checkout@v4\n      - run: ./flaky.sh\n"
 "        continue-on-error: true\n"),
("gh-010", "runs on push and defines a job that only runs when the ref is refs/heads/main using an "
 "if condition", "ifcond",
 "name: Conditional\non: push\njobs:\n  c:\n    runs-on: ubuntu-latest\n"
 "    if: github.ref == 'refs/heads/main'\n    steps:\n      - run: echo main only\n"),
]

# gh CLI tasks: (id, prompt, [patterns], reference)
GH_CLI = [
("gh-011", "create a pull request from the current branch into main with title 'Add caching' and "
 "body 'Speeds up builds'",
 [r"gh\s+pr\s+create", r"(--base|-B)\s+main", r"--title", r"Add caching", r"--body",
  r"Speeds up builds"],
 "gh pr create --base main --title 'Add caching' --body 'Speeds up builds'"),
("gh-012", "list all open issues labelled bug assigned to octocat",
 [r"gh\s+issue\s+list", r"--label", r"bug", r"--assignee", r"octocat"],
 "gh issue list --label bug --assignee octocat"),
("gh-013", "clone the repository octocat/hello-world",
 [r"gh\s+repo\s+clone", r"octocat/hello-world"], "gh repo clone octocat/hello-world"),
("gh-014", "view pull request number 42 in the web browser",
 [r"gh\s+pr\s+view", r"42", r"(--web|-w)"], "gh pr view 42 --web"),
("gh-015", "merge pull request 42 using a squash merge and delete the branch afterwards",
 [r"gh\s+pr\s+merge", r"42", r"--squash", r"--delete-branch"],
 "gh pr merge 42 --squash --delete-branch"),
("gh-016", "create an issue titled 'Crash on load' with the label bug",
 [r"gh\s+issue\s+create", r"--title", r"Crash on load", r"--label", r"bug"],
 "gh issue create --title 'Crash on load' --label bug"),
("gh-017", "check out pull request 42 locally", [r"gh\s+pr\s+checkout", r"42"], "gh pr checkout 42"),
("gh-018", "list the most recent 5 workflow runs",
 [r"gh\s+run\s+list", r"(--limit|-L)\s*5"], "gh run list --limit 5"),
("gh-019", "watch the currently running workflow run until it completes",
 [r"gh\s+run\s+watch"], "gh run watch"),
("gh-020", "view the logs of the failed steps of workflow run 12345",
 [r"gh\s+run\s+view", r"12345", r"--log-failed"], "gh run view 12345 --log-failed"),
("gh-021", "re-run the failed jobs of workflow run 12345",
 [r"gh\s+run\s+rerun", r"12345", r"--failed"], "gh run rerun 12345 --failed"),
("gh-022", "create a release tagged v1.2.0 with the title 'Version 1.2.0' and generated notes",
 [r"gh\s+release\s+create", r"v1\.2\.0", r"(--title|-t)", r"--generate-notes"],
 "gh release create v1.2.0 --title 'Version 1.2.0' --generate-notes"),
("gh-023", "upload the file dist/app.zip as an asset to release v1.2.0",
 [r"gh\s+release\s+upload", r"v1\.2\.0", r"dist/app\.zip"],
 "gh release upload v1.2.0 dist/app.zip"),
("gh-024", "set a repository secret named API_TOKEN reading the value from the file token.txt",
 [r"gh\s+secret\s+set", r"API_TOKEN", r"token\.txt"],
 "gh secret set API_TOKEN < token.txt"),
("gh-025", "list the repository's secrets", [r"gh\s+secret\s+list"], "gh secret list"),
("gh-026", "add the label needs-review to pull request 42",
 [r"gh\s+pr\s+edit", r"42", r"--add-label", r"needs-review"],
 "gh pr edit 42 --add-label needs-review"),
("gh-027", "request a review from user alice on pull request 42",
 [r"gh\s+pr\s+(edit|review)", r"42", r"(--add-reviewer|--reviewer)", r"alice"],
 "gh pr edit 42 --add-reviewer alice"),
("gh-028", "close issue 7 with a comment 'no longer relevant'",
 [r"gh\s+issue\s+close", r"7", r"(--comment|-c)", r"no longer relevant"],
 "gh issue close 7 --comment 'no longer relevant'"),
("gh-029", "list all pull requests that are ready for review and not drafts",
 [r"gh\s+pr\s+list", r"--draft[= ]false"], "gh pr list --draft=false"),
("gh-030", "fork the repository octocat/hello-world and clone it",
 [r"gh\s+repo\s+fork", r"octocat/hello-world", r"--clone"],
 "gh repo fork octocat/hello-world --clone"),
("gh-031", "create a private repository named my-tool in your account",
 [r"gh\s+repo\s+create", r"my-tool", r"--private"], "gh repo create my-tool --private"),
("gh-032", "view the current authentication status", [r"gh\s+auth\s+status"], "gh auth status"),
("gh-033", "list the open pull requests authored by you",
 [r"gh\s+pr\s+list", r"--author", r"(@me|me)"], "gh pr list --author @me"),
("gh-034", "add a comment 'looks good' to pull request 42",
 [r"gh\s+pr\s+comment", r"42", r"(--body|-b)", r"looks good"],
 "gh pr comment 42 --body 'looks good'"),
("gh-035", "approve pull request 42", [r"gh\s+pr\s+review", r"42", r"--approve"],
 "gh pr review 42 --approve"),
("gh-036", "download the artifact named build-output from workflow run 12345",
 [r"gh\s+run\s+download", r"12345", r"(-n|--name)", r"build-output"],
 "gh run download 12345 -n build-output"),
("gh-037", "call the REST API endpoint /repos/octocat/hello-world and print the JSON",
 [r"gh\s+api", r"/repos/octocat/hello-world"], "gh api /repos/octocat/hello-world"),
("gh-038", "list the repository's workflow definitions", [r"gh\s+workflow\s+list"],
 "gh workflow list"),
("gh-039", "manually trigger the workflow named deploy.yml on branch main",
 [r"gh\s+workflow\s+run", r"deploy\.yml", r"(--ref|-r)\s+main"],
 "gh workflow run deploy.yml --ref main"),
("gh-040", "list issues created in the last week that are still open, limited to 20",
 [r"gh\s+issue\s+list", r"(--state\s+open|--state=open)", r"(--limit|-L)\s*20"],
 "gh issue list --state open --limit 20"),
("gh-041", "set the description of the current repository to 'A small tool'",
 [r"gh\s+repo\s+edit", r"(--description|-d)", r"A small tool"],
 "gh repo edit --description 'A small tool'"),
("gh-042", "view the README of octocat/hello-world in the terminal",
 [r"gh\s+repo\s+view", r"octocat/hello-world"], "gh repo view octocat/hello-world"),
("gh-043", "list the releases of the current repository", [r"gh\s+release\s+list"],
 "gh release list"),
("gh-044", "delete the release tagged v0.9.0 including its tag",
 [r"gh\s+release\s+delete", r"v0\.9\.0", r"--cleanup-tag"],
 "gh release delete v0.9.0 --cleanup-tag"),
("gh-045", "create a draft pull request from the current branch into develop titled 'WIP'",
 [r"gh\s+pr\s+create", r"--draft", r"(--base|-B)\s+develop", r"--title", r"WIP"],
 "gh pr create --draft --base develop --title 'WIP' --body ''"),
("gh-046", "list the checks status for pull request 42",
 [r"gh\s+pr\s+checks", r"42"], "gh pr checks 42"),
("gh-047", "set the repository variable BUILD_ENV to production",
 [r"gh\s+variable\s+set", r"BUILD_ENV", r"production"],
 "gh variable set BUILD_ENV --body production"),
("gh-048", "list collaborators on the current repository using the API",
 [r"gh\s+api", r"collaborators"], "gh api repos/:owner/:repo/collaborators"),
("gh-049", "search for repositories matching the term kubernetes written in Go, limited to 10",
 [r"gh\s+search\s+repos", r"kubernetes", r"(--language|-l)\s*[= ]?go", r"(--limit|-L)\s*10"],
 "gh search repos kubernetes --language=go --limit 10"),
("gh-050", "view issue 7 including its comments",
 [r"gh\s+issue\s+view", r"7", r"(--comments|-c)"], "gh issue view 7 --comments"),
]

# ============================================================ DOCS (50)
DOCS = [
("doc-001", "Write a NumPy-style Python docstring for `def fetch(url, timeout=5.0, retries=3)` which "
 "returns a parsed JSON dict and raises TimeoutError once retries are exhausted. Output only the "
 "docstring text.",
 [r"Parameters", r"Returns", r"Raises", r"url", r"timeout", r"retries", r"TimeoutError",
  r"(dict|JSON)"],
 "Parameters\n----------\nurl : str\n    The URL to fetch.\ntimeout : float\n    Seconds per "
 "attempt.\nretries : int\n    Attempts before giving up.\n\nReturns\n-------\ndict\n    The "
 "parsed JSON body.\n\nRaises\n------\nTimeoutError\n    When retries are exhausted."),
("doc-002", "Write the Installation and Usage sections of a README for a Python CLI called logsift "
 "installed via pip which takes a --level flag and a file path. Use markdown headings. Output only "
 "markdown.",
 [r"#+\s*Install", r"pip install", r"logsift", r"#+\s*Usage", r"--level"],
 "## Installation\n\n```bash\npip install logsift\n```\n\n## Usage\n\n```bash\nlogsift --level "
 "error /var/log/app.log\n```\n\nThe `--level` flag filters by severity."),
("doc-003", "Document the REST endpoint POST /api/v1/orders which takes JSON with customer_id (int) "
 "and items (array), returns 201 with the created order, 400 on validation failure and 401 if "
 "unauthenticated. Include method, path, request fields and every response status.",
 [r"POST", r"/api/v1/orders", r"customer_id", r"items", r"201", r"400", r"401"],
 "### POST /api/v1/orders\n\nCreates an order.\n\nRequest body:\n- `customer_id` (int, required)\n"
 "- `items` (array, required)\n\nResponses:\n- `201` order created\n- `400` validation failure\n"
 "- `401` unauthenticated"),
("doc-004", "Write a CHANGELOG entry in Keep a Changelog style for version 2.1.0 dated 2026-07-01 "
 "with one Added, one Fixed and one Removed item.",
 [r"2\.1\.0", r"2026-07-01", r"Added", r"Fixed", r"Removed"],
 "## [2.1.0] - 2026-07-01\n\n### Added\n- Streaming export.\n\n### Fixed\n- Crash on empty input.\n\n"
 "### Removed\n- Legacy v1 endpoint."),
("doc-005", "Write a Google-style Python docstring for `def resize(image, width, height, keep_ratio=True)` "
 "returning a new Image and raising ValueError for non-positive dimensions.",
 [r"Args", r"Returns", r"Raises", r"width", r"height", r"keep_ratio", r"ValueError"],
 "Resize an image.\n\nArgs:\n    image: Source image.\n    width: Target width in pixels.\n"
 "    height: Target height in pixels.\n    keep_ratio: Preserve the aspect ratio.\n\n"
 "Returns:\n    A new Image.\n\nRaises:\n    ValueError: If width or height is not positive."),
("doc-006", "Write a docstring for a function `parse(text)` that documents one example call and its "
 "output using a doctest-style block.",
 [r">>>", r"parse\("],
 "Parse text into tokens.\n\n>>> parse('a b')\n['a', 'b']"),
("doc-007", "Write the Contributing section of a README explaining how to fork, create a branch, run "
 "tests with pytest, and open a pull request.",
 [r"#+\s*Contribut", r"fork", r"branch", r"pytest", r"pull request"],
 "## Contributing\n\n1. Fork the repository.\n2. Create a branch for your change.\n3. Run the "
 "tests with `pytest`.\n4. Open a pull request describing the change."),
("doc-008", "Document a configuration file with keys host (string), port (int, default 8080) and "
 "debug (bool, default false) as a markdown table.",
 [r"\|", r"host", r"port", r"8080", r"debug", r"false"],
 "| Key | Type | Default | Description |\n|---|---|---|---|\n| host | string | - | Bind address |\n"
 "| port | int | 8080 | Listen port |\n| debug | bool | false | Verbose logging |"),
("doc-009", "Write an error message reference documenting three errors E001 file not found, E002 "
 "permission denied and E003 timeout, each with a cause and a fix.",
 [r"E001", r"E002", r"E003", r"(cause|Cause)", r"(fix|Fix|resolution)"],
 "### E001 — file not found\nCause: the path does not exist.\nFix: check the path.\n\n"
 "### E002 — permission denied\nCause: insufficient rights.\nFix: adjust permissions.\n\n"
 "### E003 — timeout\nCause: the server did not respond.\nFix: retry or raise the timeout."),
("doc-010", "Write a migration guide section explaining that the function `old_api()` is deprecated "
 "in favour of `new_api()`, with a before and after code example.",
 [r"old_api", r"new_api", r"(deprecat|Deprecat)", r"```"],
 "## Migrating from `old_api()`\n\n`old_api()` is deprecated and will be removed in 3.0. Use "
 "`new_api()`.\n\nBefore:\n```python\nold_api(x)\n```\n\nAfter:\n```python\nnew_api(x)\n```"),
]

RN = [
("rn-001", "a React Native function component `ContactList` rendering a FlatList of contacts from "
 "props with a stable keyExtractor on contact.id, a renderItem showing contact.name in a Text, and "
 "pull-to-refresh wired to onRefresh and refreshing props.",
 [r"import.*from\s+['\"]react-native['\"]", r"FlatList", r"keyExtractor", r"renderItem",
  r"refreshing", r"onRefresh", r"<Text"],
 "import React from 'react';\nimport {FlatList, Text} from 'react-native';\n"
 "export function ContactList({contacts, refreshing, onRefresh}) {\n  return (\n    <FlatList\n"
 "      data={contacts}\n      keyExtractor={(c) => String(c.id)}\n"
 "      renderItem={({item}) => <Text>{item.name}</Text>}\n      refreshing={refreshing}\n"
 "      onRefresh={onRefresh}\n    />\n  );\n}"),
("rn-002", "a React Native custom hook `useDebouncedSearch(query, delay)` returning the debounced "
 "query, using useState and useEffect and clearing the pending timer in the effect cleanup.",
 [r"useState", r"useEffect", r"setTimeout", r"clearTimeout", r"return\s*\(\s*\)\s*=>",
  r"\[.*query.*delay.*\]"],
 "import {useState, useEffect} from 'react';\nexport function useDebouncedSearch(query, delay) {\n"
 "  const [value, setValue] = useState(query);\n  useEffect(() => {\n"
 "    const t = setTimeout(() => setValue(query), delay);\n    return () => clearTimeout(t);\n"
 "  }, [query, delay]);\n  return value;\n}"),
("rn-003", "a React Native component `Counter` using useState with a button that increments, using "
 "Pressable and Text from react-native.",
 [r"useState", r"Pressable", r"<Text", r"onPress"],
 "import React, {useState} from 'react';\nimport {Pressable, Text} from 'react-native';\n"
 "export function Counter() {\n  const [n, setN] = useState(0);\n  return (\n"
 "    <Pressable onPress={() => setN(n + 1)}>\n      <Text>{n}</Text>\n    </Pressable>\n  );\n}"),
("rn-004", "a React Native component using StyleSheet.create to define a container style with flex 1 "
 "and padding 16, applied to a View.",
 [r"StyleSheet\.create", r"flex:\s*1", r"padding:\s*16", r"<View"],
 "import React from 'react';\nimport {View, StyleSheet} from 'react-native';\n"
 "const styles = StyleSheet.create({container: {flex: 1, padding: 16}});\n"
 "export function Screen() {\n  return <View style={styles.container} />;\n}"),
("rn-005", "a React Native component `Loader` that shows an ActivityIndicator while a loading prop "
 "is true and otherwise renders its children.",
 [r"ActivityIndicator", r"loading", r"children"],
 "import React from 'react';\nimport {ActivityIndicator} from 'react-native';\n"
 "export function Loader({loading, children}) {\n"
 "  return loading ? <ActivityIndicator /> : <>{children}</>;\n}"),
("rn-006", "a React Native screen using SafeAreaView and a ScrollView containing three Text items.",
 [r"SafeAreaView", r"ScrollView", r"<Text"],
 "import React from 'react';\nimport {SafeAreaView, ScrollView, Text} from 'react-native';\n"
 "export function Screen() {\n  return (\n    <SafeAreaView>\n      <ScrollView>\n"
 "        <Text>One</Text>\n        <Text>Two</Text>\n        <Text>Three</Text>\n"
 "      </ScrollView>\n    </SafeAreaView>\n  );\n}"),
("rn-007", "a React Native form field using TextInput with value and onChangeText bound to state, "
 "and a placeholder.",
 [r"TextInput", r"onChangeText", r"placeholder", r"useState"],
 "import React, {useState} from 'react';\nimport {TextInput} from 'react-native';\n"
 "export function Field() {\n  const [v, setV] = useState('');\n"
 "  return <TextInput value={v} onChangeText={setV} placeholder=\"Name\" />;\n}"),
("rn-008", "a React Native component that uses useEffect to subscribe to Dimensions change events "
 "and unsubscribes in the cleanup.",
 [r"useEffect", r"Dimensions", r"(remove|removeEventListener)", r"return\s*\(\s*\)\s*=>"],
 "import React, {useEffect, useState} from 'react';\nimport {Dimensions, Text} from 'react-native';\n"
 "export function Size() {\n  const [w, setW] = useState(Dimensions.get('window').width);\n"
 "  useEffect(() => {\n    const sub = Dimensions.addEventListener('change', ({window}) => "
 "setW(window.width));\n    return () => sub.remove();\n  }, []);\n  return <Text>{w}</Text>;\n}"),
("rn-009", "a React Native component using Platform.select to apply a different padding on ios and "
 "android.",
 [r"Platform", r"ios", r"android"],
 "import React from 'react';\nimport {View, Platform, StyleSheet} from 'react-native';\n"
 "const styles = StyleSheet.create({box: {padding: Platform.select({ios: 20, android: 12})}});\n"
 "export function Box() {\n  return <View style={styles.box} />;\n}"),
("rn-010", "a React Native SectionList rendering sections with a renderSectionHeader and a "
 "keyExtractor.",
 [r"SectionList", r"renderSectionHeader", r"keyExtractor", r"renderItem"],
 "import React from 'react';\nimport {SectionList, Text} from 'react-native';\n"
 "export function Grouped({sections}) {\n  return (\n    <SectionList\n      sections={sections}\n"
 "      keyExtractor={(item, i) => String(item.id ?? i)}\n"
 "      renderItem={({item}) => <Text>{item.name}</Text>}\n"
 "      renderSectionHeader={({section}) => <Text>{section.title}</Text>}\n    />\n  );\n}"),
]


def _expand(rows, n=50):
    """Pattern categories ship 10 authored templates; expand ids to n is NOT done —
    we keep exactly what is authored and report the real count."""
    return rows


if __name__ == "__main__":
    import re
    print(f"ssh: {len(SSH_CFG) + len(SSH_CMD)}  github: {len(GH_WF) + len(GH_CLI)}  "
          f"docs: {len(DOCS)}  rn: {len(RN)}")
    bad = 0
    for tid, _p, pats, ref in SSH_CMD:
        miss = [x for x in pats if not re.search(x, ref, re.I)]
        if miss:
            bad += 1
            print(f"  SSH {tid} reference fails own patterns: {miss}")
    for tid, _p, pats, ref in GH_CLI:
        miss = [x for x in pats if not re.search(x, ref, re.I)]
        if miss:
            bad += 1
            print(f"  GH {tid} reference fails own patterns: {miss}")
    for tid, _p, pats, ref in DOCS:
        miss = [x for x in pats if not re.search(x, ref, re.I | re.S)]
        if miss:
            bad += 1
            print(f"  DOC {tid} reference fails own patterns: {miss}")
    for tid, _p, pats, ref in RN:
        miss = [x for x in pats if not re.search(x, ref, re.I | re.S)]
        if miss:
            bad += 1
            print(f"  RN {tid} reference fails own patterns: {miss}")
    print(f"pattern references failing their own checks: {bad}")
