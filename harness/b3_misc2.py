#!/usr/bin/env python3
"""Docs 011-050 and React Native 011-050 — the remaining pattern-graded tasks."""

DOCS_EXTRA = [
("doc-011", "Document the REST endpoint GET /api/v1/orders/{id} returning 200 with the order, 404 "
 "when missing and 401 unauthenticated. Include the path parameter.",
 [r"GET", r"/api/v1/orders", r"\{?id\}?", r"200", r"404", r"401"],
 "### GET /api/v1/orders/{id}\n\nPath parameters:\n- `id` (int) order identifier\n\nResponses:\n"
 "- `200` the order\n- `404` not found\n- `401` unauthenticated"),
("doc-012", "Document DELETE /api/v1/orders/{id} returning 204 on success, 404 when missing and 409 "
 "when the order has already shipped.",
 [r"DELETE", r"/api/v1/orders", r"204", r"404", r"409"],
 "### DELETE /api/v1/orders/{id}\n\nResponses:\n- `204` deleted\n- `404` not found\n"
 "- `409` already shipped"),
("doc-013", "Document PUT /api/v1/users/{id} accepting name and email, returning 200 with the "
 "updated user, 400 on validation error and 403 when editing another user.",
 [r"PUT", r"/api/v1/users", r"name", r"email", r"200", r"400", r"403"],
 "### PUT /api/v1/users/{id}\n\nBody: `name` (string), `email` (string)\n\nResponses:\n"
 "- `200` updated user\n- `400` validation error\n- `403` cannot edit another user"),
("doc-014", "Write a module-level Python docstring for a module `retry.py` providing decorators for "
 "retrying flaky calls, stating what it provides and one usage example.",
 [r"retry", r"(decorator|Decorator)", r"(Example|example|>>>)"],
 "Retry helpers.\n\nProvides decorators for retrying flaky calls with bounded attempts.\n\n"
 "Example:\n    @retry(3)\n    def fetch(): ..."),
("doc-015", "Write a class docstring for `class RateLimiter` documenting its purpose, its two "
 "constructor arguments capacity and refill_rate, and thread-safety.",
 [r"RateLimiter|Rate limiter|rate limit", r"capacity", r"refill_rate", r"(thread|Thread)"],
 "Token-bucket rate limiter.\n\nArgs:\n    capacity: Maximum tokens held.\n    refill_rate: "
 "Tokens added per second.\n\nNot thread-safe; guard with a lock if shared."),
("doc-016", "Write an Architecture Decision Record with Context, Decision and Consequences sections "
 "for choosing PostgreSQL over MongoDB.",
 [r"Context", r"Decision", r"Consequences", r"PostgreSQL", r"MongoDB"],
 "# ADR 4: Use PostgreSQL\n\n## Context\nWe need relational integrity and ad-hoc reporting.\n\n"
 "## Decision\nUse PostgreSQL rather than MongoDB.\n\n## Consequences\nSchema migrations become "
 "explicit; horizontal sharding is harder."),
("doc-017", "Write a troubleshooting guide entry for 'service returns 502' with symptoms, likely "
 "causes and steps to resolve.",
 [r"502", r"(Symptom|symptom)", r"(Cause|cause)", r"(Resolution|resolve|Steps|steps)"],
 "## Service returns 502\n\nSymptoms: gateway errors in the client, upstream timeouts in logs.\n\n"
 "Causes: the upstream pod is not ready, or the health check is failing.\n\n"
 "Steps: check pod readiness, inspect upstream logs, roll the deployment."),
("doc-018", "Write release notes for version 3.0.0 with Breaking Changes, Features and Bug Fixes "
 "headings and one item under each.",
 [r"3\.0\.0", r"(Breaking|breaking)", r"(Feature|feature)", r"(Bug|Fix|fix)"],
 "# 3.0.0\n\n## Breaking Changes\n- Removed the v1 API.\n\n## Features\n- Added streaming export.\n\n"
 "## Bug Fixes\n- Fixed a crash on empty input."),
("doc-019", "Write a SECURITY.md section explaining how to report a vulnerability privately, the "
 "response time commitment, and which versions are supported.",
 [r"(vulnerab|Vulnerab)", r"(report|Report)", r"(supported|Supported)"],
 "## Reporting a Vulnerability\n\nEmail security@example.com; do not open a public issue. We "
 "acknowledge reports within 3 business days.\n\n## Supported Versions\nOnly the latest minor "
 "release is supported."),
("doc-020", "Write a code comment explaining WHY a retry loop sleeps with exponential backoff rather "
 "than a fixed delay. Output only the comment.",
 [r"(backoff|Backoff)", r"(why|because|avoid|thunder|herd|overwhelm|contention)"],
 "# Exponential backoff, not a fixed delay: a fixed delay makes every client retry in lockstep\n"
 "# after an outage, which re-overwhelms the service (thundering herd). Growing the gap spreads\n"
 "# the retries out and lets the upstream recover."),
("doc-021", "Document the environment variables DATABASE_URL (required), LOG_LEVEL (default info) "
 "and PORT (default 8080) as a markdown table.",
 [r"\|", r"DATABASE_URL", r"LOG_LEVEL", r"PORT", r"8080", r"info"],
 "| Variable | Required | Default | Purpose |\n|---|---|---|---|\n| DATABASE_URL | yes | - | "
 "Connection string |\n| LOG_LEVEL | no | info | Verbosity |\n| PORT | no | 8080 | Listen port |"),
("doc-022", "Write the --help output for a CLI called `sift` with subcommands scan and report, and "
 "global flags --verbose and --config.",
 [r"sift", r"scan", r"report", r"--verbose", r"--config", r"(Usage|usage)"],
 "Usage: sift [OPTIONS] COMMAND\n\nCommands:\n  scan     Scan a directory\n  report   Produce a "
 "report\n\nOptions:\n  --verbose   Verbose output\n  --config    Path to config file"),
("doc-023", "Write a getting-started tutorial section with three numbered steps: install, configure "
 "and run, for a tool called `pulse`.",
 [r"pulse", r"1\.", r"2\.", r"3\.", r"(install|Install)", r"(config|Config)", r"(run|Run)"],
 "## Getting Started\n\n1. Install: `pip install pulse`\n2. Configure: create `pulse.toml` with "
 "your endpoint.\n3. Run: `pulse watch`"),
("doc-024", "Write a deprecation notice for the `--legacy` flag, stating the version it is removed "
 "in and what to use instead.",
 [r"--legacy", r"(deprecat|Deprecat)", r"(remove|Remove)", r"instead|replaced"],
 "> **Deprecated:** `--legacy` is deprecated and will be removed in 4.0. Use `--compat=v1` "
 "instead."),
("doc-025", "Document an API rate limit of 1000 requests per hour per API key, the headers returned, "
 "and the 429 response.",
 [r"1000", r"(hour|hourly)", r"429", r"(header|Header)"],
 "## Rate limits\n\n1000 requests per hour per API key. Each response carries "
 "`X-RateLimit-Limit`, `X-RateLimit-Remaining` and `X-RateLimit-Reset` headers. Exceeding the "
 "limit returns `429 Too Many Requests`."),
("doc-026", "Document bearer-token authentication: the Authorization header format, how to obtain a "
 "token, and the 401 response.",
 [r"Authorization", r"Bearer", r"401", r"(token|Token)"],
 "## Authentication\n\nSend `Authorization: Bearer <token>` on every request. Obtain a token from "
 "`POST /api/v1/auth/token`. Requests without a valid token receive `401 Unauthorized`."),
("doc-027", "Document a webhook: the POST payload fields event and data, the signature header, and "
 "the expectation that handlers return 2xx quickly.",
 [r"(webhook|Webhook)", r"POST", r"event", r"data", r"(signature|Signature)", r"2xx|200"],
 "## Webhooks\n\nWe POST a JSON body with `event` (string) and `data` (object). Verify the "
 "`X-Signature` header before trusting it. Return a `2xx` within 5 seconds; slow handlers are "
 "retried."),
("doc-028", "Write a commit message convention section describing Conventional Commits with the "
 "types feat, fix and docs, and one example.",
 [r"feat", r"fix", r"docs", r"(Conventional|conventional)", r":"],
 "## Commit messages\n\nUse Conventional Commits: `type(scope): summary`. Types include `feat`, "
 "`fix` and `docs`.\n\nExample: `fix(parser): handle empty input`"),
("doc-029", "Write a pull request template with sections Summary, Changes, Testing and Checklist.",
 [r"Summary", r"Changes", r"Testing", r"Checklist"],
 "## Summary\n\n## Changes\n-\n\n## Testing\n-\n\n## Checklist\n- [ ] Tests pass\n- [ ] Docs "
 "updated"),
("doc-030", "Write a bug report issue template asking for expected behaviour, actual behaviour, "
 "steps to reproduce and environment.",
 [r"(Expected|expected)", r"(Actual|actual)", r"(reproduce|Reproduce)", r"(Environment|environment)"],
 "### Expected behaviour\n\n### Actual behaviour\n\n### Steps to reproduce\n1.\n\n### Environment\n"
 "- OS:\n- Version:"),
("doc-031", "Write three FAQ entries for a backup tool covering where backups are stored, how to "
 "restore, and how long they are kept. Use question headings.",
 [r"(FAQ|Frequently)", r"(restore|Restore)", r"(stored|storage)", r"(kept|retention|retain)"],
 "## FAQ\n\n### Where are backups stored?\nIn the configured object storage bucket.\n\n"
 "### How do I restore?\nRun `tool restore --snapshot <id>`.\n\n### How long are they kept?\n"
 "Backups are retained for 35 days."),
("doc-032", "Write a glossary defining the terms idempotent, backpressure and eventual consistency.",
 [r"(idempotent|Idempotent)", r"(backpressure|Backpressure)", r"(eventual|Eventual)"],
 "## Glossary\n\n**Idempotent** — repeating the operation produces the same result.\n\n"
 "**Backpressure** — a consumer signalling a producer to slow down.\n\n"
 "**Eventual consistency** — replicas converge given no new writes."),
("doc-033", "Document the data model for a Book with fields id, title, author_id and published, "
 "giving type and nullability for each, as a table.",
 [r"\|", r"id", r"title", r"author_id", r"published"],
 "| Field | Type | Nullable |\n|---|---|---|\n| id | int | no |\n| title | string | no |\n"
 "| author_id | int | no |\n| published | date | yes |"),
("doc-034", "Describe in prose the request flow for a login: client posts credentials, service "
 "validates, issues a token, client stores it. Number the steps.",
 [r"1\.", r"2\.", r"3\.", r"(token|Token)", r"(credential|password)"],
 "1. The client posts credentials to `/auth/login`.\n2. The service validates them against the "
 "user store.\n3. On success it issues a signed token.\n4. The client stores the token and sends "
 "it on later requests."),
("doc-035", "Write a testing guide section explaining how to run unit tests, integration tests and "
 "how to get a coverage report.",
 [r"(unit|Unit)", r"(integration|Integration)", r"(coverage|Coverage)"],
 "## Testing\n\nUnit tests: `pytest tests/unit`\n\nIntegration tests: `pytest tests/integration` "
 "(requires Docker)\n\nCoverage: `pytest --cov=src --cov-report=term`"),
("doc-036", "Write a style guide section covering naming, line length and import ordering for a "
 "Python project.",
 [r"(naming|Naming)", r"(line length|79|88|100)", r"(import|Import)"],
 "## Style\n\nNaming: `snake_case` for functions, `PascalCase` for classes.\n\nLine length: 88 "
 "characters.\n\nImports: standard library, third party, then local, each group separated."),
("doc-037", "Document performance expectations: p50 under 50ms, p99 under 500ms, and what to do if "
 "they regress.",
 [r"p50", r"p99", r"50\s*ms", r"500\s*ms"],
 "## Performance targets\n\n- p50 latency under 50 ms\n- p99 latency under 500 ms\n\nIf a change "
 "regresses these, profile before merging and open an issue with the flame graph."),
("doc-038", "Document the logging convention: structured JSON, required fields timestamp, level and "
 "request_id, and that secrets must never be logged.",
 [r"(JSON|structured)", r"timestamp", r"level", r"request_id", r"(secret|Secret)"],
 "## Logging\n\nEmit structured JSON. Every line must carry `timestamp`, `level` and "
 "`request_id`.\n\nNever log secrets, tokens or full request bodies."),
("doc-039", "Document a feature flag named `new_checkout`: its default, how to enable it per user, "
 "and when it will be removed.",
 [r"new_checkout", r"(default|Default)", r"(enable|Enable)", r"[Rr]emov"],
 "## `new_checkout`\n\nDefault: off.\n\nEnable per user with `flags set new_checkout --user <id>`.\n\n"
 "Removal: once rollout reaches 100 percent, expected in 3.2."),
("doc-040", "Write a backup and restore procedure with numbered steps for taking a snapshot and "
 "restoring it.",
 [r"(snapshot|Snapshot)", r"(restore|Restore)", r"1\.", r"2\."],
 "## Backup\n\n1. Run `tool snapshot create`.\n2. Verify the snapshot id is listed.\n\n"
 "## Restore\n\n1. Stop the service.\n2. Run `tool restore --snapshot <id>`.\n3. Start the "
 "service and verify health."),
("doc-041", "Write a postmortem template with Impact, Timeline, Root Cause, and Action Items sections.",
 [r"Impact", r"Timeline", r"Root Cause", r"Action Items"],
 "# Postmortem\n\n## Impact\n\n## Timeline\n\n## Root Cause\n\n## Action Items\n- [ ]"),
("doc-042", "Write an onboarding checklist for a new engineer covering access, local setup and first "
 "task.",
 [r"(access|Access)", r"(setup|Setup|install)", r"(first|First)"],
 "## Onboarding\n\n- [ ] Request access to the repo and VPN\n- [ ] Local setup: clone, "
 "`make install`, run tests\n- [ ] Pick a `good first issue` and open a PR"),
("doc-043", "Document pagination for a list endpoint using page and per_page query parameters and "
 "the shape of the response metadata.",
 [r"(pagination|Pagination)", r"page", r"per_page", r"(total|meta)"],
 "## Pagination\n\nUse `?page=1&per_page=50`. Responses include a `meta` object with `page`, "
 "`per_page` and `total`."),
("doc-044", "Document the health check endpoint GET /healthz returning 200 when ready and 503 when "
 "dependencies are unavailable.",
 [r"/healthz", r"GET", r"200", r"503"],
 "### GET /healthz\n\nReturns `200` when the service and its dependencies are ready, `503` "
 "otherwise. Used by the load balancer."),
("doc-045", "Write documentation for a config file key `timeout_seconds` explaining its type, "
 "default, valid range and effect.",
 [r"timeout_seconds", r"(default|Default)", r"(range|minimum|maximum)"],
 "### `timeout_seconds`\n\nType: integer. Default: 30. Valid range: 1 to 300.\n\nHow long to wait "
 "for an upstream response before failing the request."),
("doc-046", "Write a short document explaining the difference between the staging and production "
 "environments including data and access.",
 [r"(staging|Staging)", r"(production|Production)", r"(data|Data)", r"(access|Access)"],
 "## Environments\n\n**Staging** uses anonymised data and is open to all engineers.\n\n"
 "**Production** holds real customer data; access requires an approved ticket."),
("doc-047", "Document three CLI exit codes: 0 success, 1 general error, 2 invalid usage.",
 [r"\b0\b", r"\b1\b", r"\b2\b", r"(exit|Exit)"],
 "## Exit codes\n\n| Code | Meaning |\n|---|---|\n| 0 | Success |\n| 1 | General error |\n"
 "| 2 | Invalid usage |"),
("doc-048", "Write a note explaining idempotency keys on POST requests: the header, why they exist, "
 "and how long they are honoured.",
 [r"[Ii]dempotency", r"(header|Header)", r"POST", r"(retry|duplicate|twice)"],
 "## Idempotency\n\nSend an `Idempotency-Key` header on POST requests. Replaying the same key "
 "returns the original result rather than creating a duplicate, which makes retries safe. Keys "
 "are honoured for 24 hours."),
("doc-049", "Document a migration that adds a non-null column, explaining the two-step deploy needed "
 "to avoid downtime.",
 [r"(migration|Migration)", r"(null|NULL)", r"(two|2)[- ]step|backfill", r"(downtime|deploy)"],
 "## Migration: adding a non-null column\n\nSplit the migration across two deploys to avoid "
 "downtime:\n\n1. Add the column as nullable and backfill existing rows.\n2. Once the backfill "
 "completes, add the NOT NULL constraint."),
("doc-050", "Write a support escalation policy describing three tiers and when to escalate between "
 "them.",
 [r"(tier|Tier|level|Level)", r"(escalat|Escalat)", r"1", r"2", r"3"],
 "## Escalation\n\n**Tier 1** handles known issues from the runbook.\n\n**Tier 2** takes anything "
 "unresolved after 30 minutes.\n\n**Tier 3** is the owning engineering team, escalated to for "
 "suspected defects or any Sev1."),
]

RN_EXTRA = [
("rn-011", "a React Native Modal shown when a visible prop is true, with a close button calling "
 "onClose.", [r"Modal", r"visible", r"onClose"],
 "import React from 'react';\nimport {Modal, Pressable, Text} from 'react-native';\n"
 "export function Dialog({visible, onClose}) {\n  return (\n    <Modal visible={visible}>\n"
 "      <Pressable onPress={onClose}><Text>Close</Text></Pressable>\n    </Modal>\n  );\n}"),
("rn-012", "a React Native Image with a remote uri source and explicit width and height.",
 [r"Image", r"uri", r"width", r"height"],
 "import React from 'react';\nimport {Image} from 'react-native';\nexport function Avatar({url}) {\n"
 "  return <Image source={{uri: url}} style={{width: 48, height: 48}} />;\n}"),
("rn-013", "a React Native TouchableOpacity button with an onPress handler and activeOpacity.",
 [r"TouchableOpacity", r"onPress", r"activeOpacity"],
 "import React from 'react';\nimport {TouchableOpacity, Text} from 'react-native';\n"
 "export function Btn({onPress}) {\n  return (\n"
 "    <TouchableOpacity onPress={onPress} activeOpacity={0.7}><Text>Go</Text></TouchableOpacity>\n"
 "  );\n}"),
("rn-014", "a React Native KeyboardAvoidingView wrapping a TextInput, with behavior chosen by "
 "Platform.", [r"KeyboardAvoidingView", r"Platform", r"TextInput", r"behavior"],
 "import React from 'react';\nimport {KeyboardAvoidingView, TextInput, Platform} from 'react-native';\n"
 "export function Form() {\n  return (\n"
 "    <KeyboardAvoidingView behavior={Platform.OS === 'ios' ? 'padding' : 'height'}>\n"
 "      <TextInput />\n    </KeyboardAvoidingView>\n  );\n}"),
("rn-015", "a React Native ScrollView with a RefreshControl bound to refreshing and onRefresh props.",
 [r"ScrollView", r"RefreshControl", r"refreshing", r"onRefresh"],
 "import React from 'react';\nimport {ScrollView, RefreshControl} from 'react-native';\n"
 "export function Page({refreshing, onRefresh, children}) {\n  return (\n"
 "    <ScrollView refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} />}>\n"
 "      {children}\n    </ScrollView>\n  );\n}"),
("rn-016", "a React Native component animating opacity from 0 to 1 with Animated and useRef.",
 [r"Animated", r"useRef", r"useEffect", r"timing"],
 "import React, {useRef, useEffect} from 'react';\nimport {Animated} from 'react-native';\n"
 "export function FadeIn({children}) {\n  const o = useRef(new Animated.Value(0)).current;\n"
 "  useEffect(() => {\n"
 "    Animated.timing(o, {toValue: 1, duration: 300, useNativeDriver: true}).start();\n  }, [o]);\n"
 "  return <Animated.View style={{opacity: o}}>{children}</Animated.View>;\n}"),
("rn-017", "a React Native component using useMemo to avoid recomputing a filtered list on each render.",
 [r"useMemo", r"filter", r"\[.*\]"],
 "import React, {useMemo} from 'react';\nimport {Text} from 'react-native';\n"
 "export function Filtered({items, q}) {\n"
 "  const shown = useMemo(() => items.filter((i) => i.name.includes(q)), [items, q]);\n"
 "  return <Text>{shown.length}</Text>;\n}"),
("rn-018", "a React Native component passing a useCallback-wrapped handler to a child to keep its "
 "identity stable.", [r"useCallback", r"\[.*\]"],
 "import React, {useCallback} from 'react';\nimport {Pressable, Text} from 'react-native';\n"
 "export function Parent({onPick}) {\n"
 "  const handle = useCallback((id) => onPick(id), [onPick]);\n"
 "  return <Pressable onPress={() => handle(1)}><Text>Pick</Text></Pressable>;\n}"),
("rn-019", "a React context and provider for a theme, plus a useTheme hook reading it.",
 [r"createContext", r"useContext", r"Provider"],
 "import React, {createContext, useContext} from 'react';\nconst ThemeContext = createContext('light');\n"
 "export function ThemeProvider({value, children}) {\n"
 "  return <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>;\n}\n"
 "export function useTheme() {\n  return useContext(ThemeContext);\n}"),
("rn-020", "a React Native FlatList with a ListEmptyComponent shown when data is empty.",
 [r"FlatList", r"ListEmptyComponent", r"data"],
 "import React from 'react';\nimport {FlatList, Text} from 'react-native';\n"
 "export function List({data}) {\n  return (\n    <FlatList\n      data={data}\n"
 "      renderItem={({item}) => <Text>{item.name}</Text>}\n"
 "      ListEmptyComponent={<Text>Nothing here</Text>}\n    />\n  );\n}"),
("rn-021", "a React Native FlatList with an ItemSeparatorComponent drawing a thin divider View.",
 [r"FlatList", r"ItemSeparatorComponent", r"View"],
 "import React from 'react';\nimport {FlatList, Text, View} from 'react-native';\n"
 "export function List({data}) {\n  return (\n    <FlatList\n      data={data}\n"
 "      renderItem={({item}) => <Text>{item.name}</Text>}\n"
 "      ItemSeparatorComponent={() => <View style={{height: 1}} />}\n    />\n  );\n}"),
("rn-022", "a React Native FlatList implementing infinite scroll with onEndReached and "
 "onEndReachedThreshold.",
 [r"FlatList", r"onEndReached", r"onEndReachedThreshold"],
 "import React from 'react';\nimport {FlatList, Text} from 'react-native';\n"
 "export function Feed({data, loadMore}) {\n  return (\n    <FlatList\n      data={data}\n"
 "      renderItem={({item}) => <Text>{item.name}</Text>}\n      onEndReached={loadMore}\n"
 "      onEndReachedThreshold={0.5}\n    />\n  );\n}"),
("rn-023", "a React Native list row wrapped in React.memo to avoid re-rendering unchanged rows.",
 [r"memo", r"export"],
 "import React, {memo} from 'react';\nimport {Text} from 'react-native';\n"
 "export const Row = memo(function Row({name}) {\n  return <Text>{name}</Text>;\n});"),
("rn-024", "a React Native Switch bound to a boolean state with onValueChange.",
 [r"Switch", r"onValueChange", r"useState"],
 "import React, {useState} from 'react';\nimport {Switch} from 'react-native';\n"
 "export function Toggle() {\n  const [on, setOn] = useState(false);\n"
 "  return <Switch value={on} onValueChange={setOn} />;\n}"),
("rn-025", "a React Native Alert shown from a button press with two buttons Cancel and OK.",
 [r"Alert", r"Cancel", r"OK"],
 "import React from 'react';\nimport {Alert, Pressable, Text} from 'react-native';\n"
 "export function Danger({onConfirm}) {\n  const ask = () =>\n"
 "    Alert.alert('Delete?', 'This cannot be undone', [\n"
 "      {text: 'Cancel', style: 'cancel'},\n      {text: 'OK', onPress: onConfirm},\n    ]);\n"
 "  return <Pressable onPress={ask}><Text>Delete</Text></Pressable>;\n}"),
("rn-026", "a React Native component opening an external URL with Linking after checking canOpenURL.",
 [r"Linking", r"canOpenURL", r"openURL"],
 "import React from 'react';\nimport {Linking, Pressable, Text} from 'react-native';\n"
 "export function Link({url}) {\n  const go = async () => {\n"
 "    if (await Linking.canOpenURL(url)) await Linking.openURL(url);\n  };\n"
 "  return <Pressable onPress={go}><Text>Open</Text></Pressable>;\n}"),
("rn-027", "a React Native StatusBar configured with a dark content style and a background colour.",
 [r"StatusBar", r"barStyle", r"backgroundColor"],
 "import React from 'react';\nimport {StatusBar} from 'react-native';\nexport function Bar() {\n"
 "  return <StatusBar barStyle=\"dark-content\" backgroundColor=\"#ffffff\" />;\n}"),
("rn-028", "a React Native layout using flexDirection row with justifyContent space-between.",
 [r"flexDirection:\s*'row'", r"justifyContent", r"space-between"],
 "import React from 'react';\nimport {View, StyleSheet} from 'react-native';\n"
 "const s = StyleSheet.create({row: {flexDirection: 'row', justifyContent: 'space-between'}});\n"
 "export function Row({children}) {\n  return <View style={s.row}>{children}</View>;\n}"),
("rn-029", "a React Native absolutely positioned badge in the top right of a container.",
 [r"position:\s*'absolute'", r"top", r"right"],
 "import React from 'react';\nimport {View, StyleSheet} from 'react-native';\n"
 "const s = StyleSheet.create({badge: {position: 'absolute', top: 0, right: 0}});\n"
 "export function Badge() {\n  return <View style={s.badge} />;\n}"),
("rn-030", "a React Native card with a shadow on iOS and elevation on Android.",
 [r"shadow", r"elevation", r"Platform"],
 "import React from 'react';\nimport {View, StyleSheet, Platform} from 'react-native';\n"
 "const s = StyleSheet.create({card: Platform.select({\n"
 "  ios: {shadowColor: '#000', shadowOpacity: 0.2, shadowRadius: 4},\n"
 "  android: {elevation: 4},\n})});\nexport function Card() {\n  return <View style={s.card} />;\n}"),
("rn-031", "a horizontally scrolling React Native ScrollView with paging enabled.",
 [r"ScrollView", r"horizontal", r"pagingEnabled"],
 "import React from 'react';\nimport {ScrollView} from 'react-native';\n"
 "export function Carousel({children}) {\n"
 "  return <ScrollView horizontal pagingEnabled>{children}</ScrollView>;\n}"),
("rn-032", "a React Native ImageBackground with a source uri wrapping a Text child.",
 [r"ImageBackground", r"uri", r"<Text"],
 "import React from 'react';\nimport {ImageBackground, Text} from 'react-native';\n"
 "export function Hero({url}) {\n  return (\n    <ImageBackground source={{uri: url}}>\n"
 "      <Text>Title</Text>\n    </ImageBackground>\n  );\n}"),
("rn-033", "a React Native component using useReducer to manage a counter with increment and reset "
 "actions.", [r"useReducer", r"increment", r"reset", r"dispatch"],
 "import React, {useReducer} from 'react';\nimport {Text} from 'react-native';\n"
 "function reducer(s, a) {\n  if (a.type === 'increment') return s + 1;\n"
 "  if (a.type === 'reset') return 0;\n  return s;\n}\nexport function Counter() {\n"
 "  const [n, dispatch] = useReducer(reducer, 0);\n"
 "  return <Text onPress={() => dispatch({type: 'increment'})}>{n}</Text>;\n}"),
("rn-034", "a React Native TextInput exposed through forwardRef so a parent can focus it.",
 [r"forwardRef", r"ref", r"TextInput"],
 "import React, {forwardRef} from 'react';\nimport {TextInput} from 'react-native';\n"
 "export const Field = forwardRef(function Field(props, ref) {\n"
 "  return <TextInput ref={ref} {...props} />;\n});"),
("rn-035", "a React Native component measuring its own size with onLayout and storing it in state.",
 [r"onLayout", r"useState", r"nativeEvent"],
 "import React, {useState} from 'react';\nimport {View} from 'react-native';\n"
 "export function Measured() {\n  const [w, setW] = useState(0);\n  return (\n"
 "    <View onLayout={(e) => setW(e.nativeEvent.layout.width)} style={{width: '100%'}} />\n  );\n}"),
("rn-036", "a React Native component reading the colour scheme with useColorScheme and picking a "
 "background colour.", [r"useColorScheme", r"dark", r"backgroundColor"],
 "import React from 'react';\nimport {View, useColorScheme} from 'react-native';\n"
 "export function Surface() {\n  const scheme = useColorScheme();\n"
 "  return <View style={{backgroundColor: scheme === 'dark' ? '#000' : '#fff'}} />;\n}"),
("rn-037", "a React Native Pressable whose style is a function of the pressed state.",
 [r"Pressable", r"pressed", r"style=\{"],
 "import React from 'react';\nimport {Pressable, Text} from 'react-native';\n"
 "export function Btn({onPress}) {\n  return (\n"
 "    <Pressable onPress={onPress} style={({pressed}) => ({opacity: pressed ? 0.5 : 1})}>\n"
 "      <Text>Tap</Text>\n    </Pressable>\n  );\n}"),
("rn-038", "a React Native button with accessibility props: an accessibilityLabel and "
 "accessibilityRole.", [r"accessibilityLabel", r"accessibilityRole"],
 "import React from 'react';\nimport {Pressable, Text} from 'react-native';\n"
 "export function Btn({onPress}) {\n  return (\n"
 "    <Pressable onPress={onPress} accessibilityRole=\"button\" accessibilityLabel=\"Save\">\n"
 "      <Text>Save</Text>\n    </Pressable>\n  );\n}"),
("rn-039", "a React Native class component acting as an error boundary with "
 "componentDidCatch and a fallback render.",
 [r"componentDidCatch", r"(getDerivedStateFromError|hasError)", r"render"],
 "import React from 'react';\nimport {Text} from 'react-native';\n"
 "export class Boundary extends React.Component {\n  state = {hasError: false};\n"
 "  static getDerivedStateFromError() {\n    return {hasError: true};\n  }\n"
 "  componentDidCatch(err) {\n    console.warn(err);\n  }\n  render() {\n"
 "    return this.state.hasError ? <Text>Something broke</Text> : this.props.children;\n  }\n}"),
("rn-040", "a React Native FlatList supplying getItemLayout for fixed-height rows of 60 pixels.",
 [r"getItemLayout", r"60", r"index"],
 "import React from 'react';\nimport {FlatList, Text} from 'react-native';\n"
 "export function List({data}) {\n  return (\n    <FlatList\n      data={data}\n"
 "      renderItem={({item}) => <Text>{item.name}</Text>}\n"
 "      getItemLayout={(d, index) => ({length: 60, offset: 60 * index, index})}\n    />\n  );\n}"),
("rn-041", "a React Native hook that fetches data on mount and cancels the request in the cleanup "
 "using an AbortController.",
 [r"useEffect", r"AbortController", r"abort", r"return\s*\(\s*\)\s*=>"],
 "import {useEffect, useState} from 'react';\nexport function useFetch(url) {\n"
 "  const [data, setData] = useState(null);\n  useEffect(() => {\n"
 "    const c = new AbortController();\n"
 "    fetch(url, {signal: c.signal}).then((r) => r.json()).then(setData).catch(() => {});\n"
 "    return () => c.abort();\n  }, [url]);\n  return data;\n}"),
("rn-042", "a React Native component rendering a list of tags using map with a key on each element.",
 [r"\.map\(", r"key=", r"<Text"],
 "import React from 'react';\nimport {View, Text} from 'react-native';\n"
 "export function Tags({tags}) {\n  return (\n    <View>\n"
 "      {tags.map((t) => (\n        <Text key={t}>{t}</Text>\n      ))}\n    </View>\n  );\n}"),
("rn-043", "a React Native component that conditionally renders one of two views based on a prop.",
 [r"\?", r":", r"<View"],
 "import React from 'react';\nimport {View, Text} from 'react-native';\n"
 "export function Toggle({on}) {\n  return <View>{on ? <Text>On</Text> : <Text>Off</Text>}</View>;\n}"),
("rn-044", "a React Native styled Text using fontWeight bold and a numeric fontSize.",
 [r"fontWeight", r"bold", r"fontSize"],
 "import React from 'react';\nimport {Text, StyleSheet} from 'react-native';\n"
 "const s = StyleSheet.create({title: {fontWeight: 'bold', fontSize: 20}});\n"
 "export function Title({children}) {\n  return <Text style={s.title}>{children}</Text>;\n}"),
("rn-045", "a React Native component that composes two styles by passing an array to the style prop.",
 [r"style=\{\[", r"StyleSheet"],
 "import React from 'react';\nimport {View, StyleSheet} from 'react-native';\n"
 "const s = StyleSheet.create({base: {padding: 8}, active: {opacity: 1}});\n"
 "export function Box({active}) {\n"
 "  return <View style={[s.base, active && s.active]} />;\n}"),
("rn-046", "a React Native ActivityIndicator with a large size and an explicit colour.",
 [r"ActivityIndicator", r"large", r"color"],
 "import React from 'react';\nimport {ActivityIndicator} from 'react-native';\n"
 "export function Spinner() {\n  return <ActivityIndicator size=\"large\" color=\"#0080a0\" />;\n}"),
("rn-047", "a React Native FlatList whose keyExtractor falls back to the index when an item has no id.",
 [r"keyExtractor", r"index", r"id"],
 "import React from 'react';\nimport {FlatList, Text} from 'react-native';\n"
 "export function List({data}) {\n  return (\n    <FlatList\n      data={data}\n"
 "      keyExtractor={(item, index) => (item.id != null ? String(item.id) : String(index))}\n"
 "      renderItem={({item}) => <Text>{item.name}</Text>}\n    />\n  );\n}"),
("rn-048", "a React Native component using useRef to keep a mutable value across renders without "
 "re-rendering.", [r"useRef", r"\.current"],
 "import React, {useRef} from 'react';\nimport {Pressable, Text} from 'react-native';\n"
 "export function Taps() {\n  const count = useRef(0);\n  return (\n"
 "    <Pressable onPress={() => {count.current += 1;}}><Text>tap</Text></Pressable>\n  );\n}"),
("rn-049", "a React Native View with testID and a nested Text also carrying a testID, for automated "
 "testing.", [r"testID", r"<View", r"<Text"],
 "import React from 'react';\nimport {View, Text} from 'react-native';\n"
 "export function Panel() {\n  return (\n    <View testID=\"panel\">\n"
 "      <Text testID=\"panel-title\">Title</Text>\n    </View>\n  );\n}"),
("rn-050", "a React Native component that renders nothing when a prop is falsy by returning null.",
 [r"return null", r"if\s*\("],
 "import React from 'react';\nimport {Text} from 'react-native';\n"
 "export function Maybe({show, label}) {\n  if (!show) {\n    return null;\n  }\n"
 "  return <Text>{label}</Text>;\n}"),
]

if __name__ == "__main__":
    import re
    bad = 0
    for name, rows in (("DOC", DOCS_EXTRA), ("RN", RN_EXTRA)):
        for tid, _p, pats, ref in rows:
            miss = [x for x in pats if not re.search(x, ref, re.I | re.S)]
            if miss:
                bad += 1
                print(f"  {name} {tid} reference fails own patterns: {miss}")
    print(f"docs_extra={len(DOCS_EXTRA)} rn_extra={len(RN_EXTRA)} failing={bad}")
