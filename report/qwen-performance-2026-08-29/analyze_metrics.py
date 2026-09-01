#!/usr/bin/env python3
import csv
import json
import math
import re
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).parent
SAMPLE_RE = re.compile(r'^([A-Za-z_:][A-Za-z0-9_:]*)(\{.*\})?\s+([^\s]+)$')
LABEL_RE = re.compile(r'(\w+)="((?:\\.|[^"\\])*)"')


def load_prom(path):
    series = {}
    for line in path.read_text().splitlines():
        if not line or line.startswith('#'):
            continue
        match = SAMPLE_RE.match(line)
        if not match:
            continue
        name, raw_labels, raw_value = match.groups()
        try:
            value = float(raw_value)
        except ValueError:
            continue
        labels = tuple(sorted(LABEL_RE.findall(raw_labels or '')))
        series[(name, labels)] = value
    return series


def load_host(path):
    lines = path.read_text().splitlines()
    timestamp = datetime.strptime(lines[0], '%Y-%m-%dT%H:%M:%SZ')
    gpu_util, power, temp, sm_clock = [float(v.strip()) for v in lines[1].split(',')]
    load1, load5, load15 = [float(v) for v in lines[2].split()[:3]]
    mem = [int(v) for v in lines[4].split()[1:]]
    swap = [int(v) for v in lines[5].split()[1:]]
    return {
        'timestamp': timestamp,
        'gpu_util_pct': gpu_util,
        'power_w': power,
        'temp_c': temp,
        'sm_clock_mhz': sm_clock,
        'load1': load1,
        'load5': load5,
        'load15': load15,
        'memory_total_bytes': mem[0],
        'memory_used_bytes': mem[1],
        'memory_available_bytes': mem[-1],
        'swap_total_bytes': swap[0],
        'swap_used_bytes': swap[1],
    }


def labels_dict(labels):
    return dict(labels)


def total(sample, name, required=None):
    required = required or {}
    result = 0.0
    found = False
    for (series_name, labels), value in sample.items():
        if series_name != name:
            continue
        label_map = labels_dict(labels)
        if all(label_map.get(k) == v for k, v in required.items()):
            result += value
            found = True
    return result if found else None


def delta(start, end, name, required=None):
    a = total(start, name, required)
    b = total(end, name, required)
    return None if a is None or b is None else b - a


def ratio(num, den):
    return None if den in (None, 0) or num is None else num / den


def histogram_quantile(start, end, metric, q):
    buckets = {}
    bucket_name = metric + '_bucket'
    for (name, labels), end_value in end.items():
        if name != bucket_name:
            continue
        label_map = labels_dict(labels)
        le = label_map.get('le')
        if le is None:
            continue
        start_value = start.get((name, labels), 0.0)
        boundary = math.inf if le == '+Inf' else float(le)
        buckets[boundary] = buckets.get(boundary, 0.0) + end_value - start_value
    if not buckets:
        return None
    count = max(buckets.values())
    if count <= 0:
        return None
    target = q * count
    for boundary in sorted(buckets):
        if buckets[boundary] >= target:
            return boundary
    return None


def interval_row(label, start, end, start_host, end_host):
    seconds = (end_host['timestamp'] - start_host['timestamp']).total_seconds()
    drafts = delta(start, end, 'vllm:spec_decode_num_drafts_total')
    draft_tokens = delta(start, end, 'vllm:spec_decode_num_draft_tokens_total')
    accepted = delta(start, end, 'vllm:spec_decode_num_accepted_tokens_total')
    prompt = delta(start, end, 'vllm:prompt_tokens_total')
    prompt_compute = delta(start, end, 'vllm:prompt_tokens_by_source_total', {'source': 'local_compute'})
    prompt_cached = delta(start, end, 'vllm:prompt_tokens_by_source_total', {'source': 'local_cache_hit'})
    generated = delta(start, end, 'vllm:generation_tokens_total')
    completions = delta(start, end, 'vllm:request_success_total')
    ttft_count = delta(start, end, 'vllm:time_to_first_token_seconds_count')
    ttft_sum = delta(start, end, 'vllm:time_to_first_token_seconds_sum')
    tpot_count = delta(start, end, 'vllm:request_time_per_output_token_seconds_count')
    tpot_sum = delta(start, end, 'vllm:request_time_per_output_token_seconds_sum')
    queue_count = delta(start, end, 'vllm:request_queue_time_seconds_count')
    queue_sum = delta(start, end, 'vllm:request_queue_time_seconds_sum')
    row = {
        'interval': label,
        'seconds': seconds,
        'prompt_tokens_per_s': ratio(prompt, seconds),
        'computed_prompt_tokens_per_s': ratio(prompt_compute, seconds),
        'cached_prompt_tokens_per_s': ratio(prompt_cached, seconds),
        'generation_tokens_per_s': ratio(generated, seconds),
        'completed_requests': completions,
        'requests_per_min': ratio(completions * 60 if completions is not None else None, seconds),
        'spec_drafts': drafts,
        'draft_tokens': draft_tokens,
        'accepted_draft_tokens': accepted,
        'spec_token_acceptance': ratio(accepted, draft_tokens),
        'accepted_tokens_per_draft': ratio(accepted, drafts),
        'prefix_cache_hit_rate': ratio(prompt_cached, prompt),
        'avg_ttft_s': ratio(ttft_sum, ttft_count),
        'p50_ttft_upper_s': histogram_quantile(start, end, 'vllm:time_to_first_token_seconds', 0.50),
        'p90_ttft_upper_s': histogram_quantile(start, end, 'vllm:time_to_first_token_seconds', 0.90),
        'avg_time_per_output_token_s': ratio(tpot_sum, tpot_count),
        'avg_completed_request_queue_s': ratio(queue_sum, queue_count),
        'preemptions': delta(start, end, 'vllm:num_preemptions_total'),
        'running_end': total(end, 'vllm:num_requests_running'),
        'waiting_end': total(end, 'vllm:num_requests_waiting'),
        'kv_usage_end': total(end, 'vllm:kv_cache_usage_perc'),
        'gpu_util_end_pct': end_host['gpu_util_pct'],
        'power_end_w': end_host['power_w'],
        'temp_end_c': end_host['temp_c'],
        'memory_available_end_gib': end_host['memory_available_bytes'] / 2**30,
        'swap_used_end_gib': end_host['swap_used_bytes'] / 2**30,
    }
    for position in range(3):
        pos = delta(start, end, 'vllm:spec_decode_num_accepted_tokens_per_pos_total', {'position': str(position)})
        row[f'spec_position_{position + 1}_acceptance'] = ratio(pos, drafts)
    return row


samples = [load_prom(ROOT / f'metrics-t{i}.prom') for i in range(3)]
hosts = [load_host(ROOT / f'host-t{i}.txt') for i in range(3)]
rows = [
    interval_row('T0-T1', samples[0], samples[1], hosts[0], hosts[1]),
    interval_row('T1-T2', samples[1], samples[2], hosts[1], hosts[2]),
    interval_row('T0-T2', samples[0], samples[2], hosts[0], hosts[2]),
]

with (ROOT / 'intervals.csv').open('w', newline='') as handle:
    writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
    writer.writeheader()
    writer.writerows(rows)

summary = {
    'window_start_utc': hosts[0]['timestamp'].isoformat() + 'Z',
    'window_end_utc': hosts[2]['timestamp'].isoformat() + 'Z',
    'intervals': rows,
    'host_samples': [
        {**host, 'timestamp': host['timestamp'].isoformat() + 'Z'} for host in hosts
    ],
}
print(json.dumps(summary, indent=2))
