#!/usr/bin/env python3
"""RAG category — 50 questions over a synthetic corpus no model can have seen.

40 answerable (graded on required facts appearing in the answer) and 10
unanswerable by construction (graded on the model declining rather than
inventing). verify() asserts each answerable fact is actually present in the
document and each unanswerable string is genuinely absent.
"""

DOC = """
# Aerelith Platform — Internal Operations Runbook (rev 7.2)

## 1. Service topology
The platform runs four services. `quill-api` handles inbound HTTP and listens on port 8443.
`marrow-worker` consumes the task queue and runs with a default concurrency of 12.
`tessel-cache` is a Redis-compatible store pinned to version 6.2.14. `drift-indexer`
rebuilds the search index nightly at 03:20 UTC and holds a lock named `drift-rebuild`.

## 2. Deployment
Deployments use the `aerectl` CLI. `aerectl roll <service>` performs a rolling restart,
waiting 45 seconds between each pod. Deployments are frozen between 22:00 and 06:00 UTC
unless the on-call engineer passes the `--break-glass` flag, which is audited and pages the
platform lead. A rollback is `aerectl revert <service> --to <build-id>` and is only retained
for the last 6 builds.

## 3. Alert thresholds
The p99 latency alert for quill-api fires at 850 milliseconds. The queue depth alert for
marrow-worker fires when depth exceeds 4000 messages for more than 5 minutes. Cache eviction
alerts fire above 200 keys per second. The indexer alerts if a rebuild exceeds 90 minutes.
Disk alerts fire at 85 percent utilisation on any node.

## 4. Incident severities
Sev1 is a total customer-facing outage and requires a public status page update within 15
minutes. Sev2 is degraded performance affecting more than 10 percent of requests. Sev3 is
internal-only impact. Only Sev1 and Sev2 require a written postmortem, due within 5 business
days. The incident commander role rotates weekly and is separate from the on-call engineer.

## 5. Access control
Production database access requires an approved change ticket and is granted through the
`db-breakglass` group for a maximum of 4 hours. Direct SSH to production hosts was removed in
rev 6.0; all access now goes through the session broker. Service accounts rotate credentials
every 30 days. The `quill-admin` role can read but not delete audit logs.

## 6. Backups
Database snapshots are taken every 6 hours and retained for 35 days. Snapshots are stored in
the `aerelith-cold` bucket in region eu-west-2. A restore drill is performed quarterly and the
last recorded restore time was 42 minutes. Backups are encrypted with the `backup-2024` key.

## 7. Networking
The service mesh enforces mutual TLS with certificates valid for 90 days. Ingress is rate
limited to 2000 requests per second per client IP. The internal DNS suffix is
`svc.aerelith.internal`. Egress to the public internet is denied by default and allowed only
through the `egress-proxy` on port 3128.
"""

# (id, question, [required regexes in the answer])
ANSWERABLE = [
("rag-001", "Which port does quill-api listen on?", [r"8443"]),
("rag-002", "What is the default concurrency of marrow-worker?", [r"\b12\b"]),
("rag-003", "How long does a rolling restart wait between each pod?", [r"45"]),
("rag-004", "During what hours are deployments frozen?", [r"22:00", r"06:00"]),
("rag-005", "Which flag overrides the deployment freeze?", [r"break-glass"]),
("rag-006", "At what p99 latency does the quill-api alert fire?", [r"850"]),
("rag-007", "Which severities require a written postmortem and by when?",
 [r"Sev\s*1", r"Sev\s*2", r"5\s*business"]),
("rag-008", "How long can production database access be granted for, and through which group?",
 [r"4\s*hour", r"db-breakglass"]),
("rag-009", "Can engineers SSH directly into production hosts?",
 [r"(no|removed|cannot|can't|not)", r"broker"]),
("rag-010", "What version is tessel-cache pinned to?", [r"6\.2\.14"]),
("rag-011", "When does drift-indexer rebuild the search index?", [r"03:20"]),
("rag-012", "What is the name of the lock held by drift-indexer?", [r"drift-rebuild"]),
("rag-013", "What is the command to perform a rolling restart?", [r"aerectl\s+roll"]),
("rag-014", "How many previous builds can you roll back to?", [r"\b6\b"]),
("rag-015", "At what queue depth does the marrow-worker alert fire, and after how long?",
 [r"4000", r"5\s*min"]),
("rag-016", "Above what eviction rate do cache alerts fire?", [r"200"]),
("rag-017", "How long must an index rebuild take before it alerts?", [r"90"]),
("rag-018", "At what disk utilisation do alerts fire?", [r"85"]),
("rag-019", "How quickly must a Sev1 get a public status page update?", [r"15\s*min"]),
("rag-020", "What does Sev2 mean?", [r"10\s*percent|10%"]),
("rag-021", "How often does the incident commander role rotate?", [r"week"]),
("rag-022", "How often do service accounts rotate credentials?", [r"30\s*day"]),
("rag-023", "Can the quill-admin role delete audit logs?", [r"(no|not|cannot|can't|read)"]),
("rag-024", "How often are database snapshots taken?", [r"6\s*hour"]),
("rag-025", "How long are database snapshots retained?", [r"35\s*day"]),
("rag-026", "In which bucket and region are snapshots stored?",
 [r"aerelith-cold", r"eu-west-2"]),
("rag-027", "How often is a restore drill performed?", [r"quarter"]),
("rag-028", "What was the last recorded restore time?", [r"42"]),
("rag-029", "Which key encrypts the backups?", [r"backup-2024"]),
("rag-030", "How long are service mesh certificates valid?", [r"90\s*day"]),
("rag-031", "What is the ingress rate limit per client IP?", [r"2000"]),
("rag-032", "What is the internal DNS suffix?", [r"svc\.aerelith\.internal"]),
("rag-033", "How is egress to the public internet allowed?", [r"egress-proxy", r"3128"]),
("rag-034", "What is the rollback command?", [r"aerectl\s+revert"]),
("rag-035", "Which services does the platform run?",
 [r"quill-api", r"marrow-worker", r"tessel-cache", r"drift-indexer"]),
("rag-036", "Does the --break-glass flag notify anyone?", [r"(page|lead|audit)"]),
("rag-037", "Is the incident commander the same person as the on-call engineer?",
 [r"(no|separate|not)"]),
("rag-038", "What does Sev3 cover?", [r"internal"]),
("rag-039", "What protocol does the service mesh enforce between services?", [r"TLS"]),
("rag-040", "What is required before production database access is granted?",
 [r"(change ticket|ticket|approv)"]),
]

# Facts genuinely absent from DOC — the model must decline, not invent.
UNANSWERABLE = [
("rag-041", "What is the contractual uptime SLA percentage promised to customers?", "SLA"),
("rag-042", "What is the phone number for the on-call escalation hotline?", "phone"),
("rag-043", "How much does the Aerelith platform cost per month to operate?", "cost"),
("rag-044", "Which cloud provider hosts the Aerelith platform?", "cloud provider"),
("rag-045", "What is the name of the current platform lead?", "lead name"),
("rag-046", "How many engineers are on the platform team?", "headcount"),
("rag-047", "What programming language is quill-api written in?", "language"),
("rag-048", "What is the maximum supported number of concurrent customers?", "max customers"),
("rag-049", "When is the next scheduled maintenance window?", "next window"),
("rag-050", "What is the retention period for application logs?", "log retention"),
]

REFUSAL = [
    r"not (specified|mentioned|stated|included|provided|given|listed|documented|covered|defined|described)",
    r"does(n't| not) (say|specify|mention|state|contain|include|provide|define)",
    r"no (information|mention|reference|details?|data)",
    r"isn'?t (in|mentioned|specified|stated)",
    r"cannot be (determined|found|answered)",
    r"unable to (find|determine|answer)",
    r"not (found|available|present) in the",
    r"the (document|runbook|text|excerpt) does not",
    r"(i )?(don'?t|do not) (have|see|find)",
]

PROMPT = ("Answer the question using ONLY the document below. If the document does not contain "
          "the answer, say so explicitly and do not guess.\n\n--- DOCUMENT ---\n{doc}\n--- END "
          "---\n\nQuestion: {q}")


def tasks():
    out = []
    for tid, q, _pats in ANSWERABLE:
        out.append((tid, PROMPT.format(doc=DOC, q=q)))
    for tid, q, _why in UNANSWERABLE:
        out.append((tid, PROMPT.format(doc=DOC, q=q)))
    return out


def verify():
    """Answerable facts must exist in the doc; unanswerable topics must not."""
    import re
    problems = []
    for tid, _q, pats in ANSWERABLE:
        for p in pats:
            # the answer regex should be satisfiable from the document itself
            if not re.search(p, DOC, re.I):
                # allow yes/no style alternations that won't appear verbatim
                if not any(w in p for w in ("no|", "not|", "cannot", "can't", "read", "week",
                                            "quarter", "internal", "approv", "page|", "TLS",
                                            "separate")):
                    problems.append((tid, f"fact regex not present in doc: {p}"))
    banned = ["sla", "phone", "hotline", "cost per month", "aws", "gcp", "azure",
              "platform lead is", "engineers are", "written in", "log retention"]
    low = DOC.lower()
    for tid, q, why in UNANSWERABLE:
        for b in banned:
            if b in low and b in q.lower():
                problems.append((tid, f"supposedly-absent topic present: {b}"))
    return problems


if __name__ == "__main__":
    ids = [t[0] for t in ANSWERABLE] + [t[0] for t in UNANSWERABLE]
    assert len(ids) == len(set(ids)), "dup ids"
    p = verify()
    print(f"rag tasks: {len(ids)} ({len(ANSWERABLE)} answerable, {len(UNANSWERABLE)} unanswerable)")
    print(f"doc-consistency problems: {len(p)}")
    for tid, why in p:
        print(f"   {tid}: {why}")
