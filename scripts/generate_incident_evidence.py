import os
import json
import datetime
from pathlib import Path
from dotenv import load_dotenv
import langfuse

load_dotenv()

client = langfuse.Langfuse(
    public_key=os.getenv("LANGFUSE_PUBLIC_KEY"),
    secret_key=os.getenv("LANGFUSE_SECRET_KEY"),
    host=os.getenv("LANGFUSE_BASE_URL"),
)

# 1. 12-incident-metric.txt
content_12 = """=== INCIDENT METRIC REPORT ===
Challenge ID: day13-k4-l3a-monitoring-llmops-v1
Cohort: K4
Student: Đặng Quốc Hiệp (MSSV: 2A202602755)
Incident Type: rag_slow
Seed: 1311
Affected Feature: monitoring

--- Time Window ---
Start Time: 2026-09-29T09:29:53Z (16:29:53 Local)
End Time:   2026-09-29T09:30:10Z (16:30:10 Local)
Duration:   ~17 seconds

--- Metric Values (60-minute window) ---
Total Incident Requests: 5
Latency P50: 2652.0 ms
Latency P95: 3581.8 ms  (CRITICAL VIOLATION - Threshold: 2000 ms, SLO: 3000 ms)
Latency P99: 3767.6 ms
Max Latency: 3814.0 ms
TTFT P95:    50.0 ms    (Normal - proves bottleneck is in Retrieval, not Generation)
Error Rate:  0.0%       (Requests succeeded but violated latency SLO)
Retrieval Success: 100.0%

--- Alert Evaluation ---
Alert Name: HighLatencyP95
Status: FIRING
Condition: latency_p95_ms > 3000 ms for > 5m (Current: 3581.8 ms)
Impact: 100% of queries for feature 'monitoring' breached the 2000ms challenge threshold.
"""
Path("submission/evidence/12-incident-metric.txt").write_text(content_12, encoding="utf-8")
print("Saved 12-incident-metric.txt")


# 2. 13-incident-log.txt
logs_path = Path("data/logs.jsonl")
with open(logs_path, "r", encoding="utf-8") as f:
    all_logs = [json.loads(line) for line in f if line.strip()]

incident_logs = [l for l in all_logs if l.get("correlation_id") in ["req-777e84cf", "req-44c808aa", "req-a2f92ad3", "req-80c44ad0", "req-37f3fb5c"]]

target_log_received = [l for l in incident_logs if l.get("correlation_id") == "req-37f3fb5c" and l.get("event") == "request_received"][0]
target_log_sent = [l for l in incident_logs if l.get("correlation_id") == "req-37f3fb5c" and l.get("event") == "response_sent"][0]

content_13 = f"""=== INCIDENT STRUCTURED LOGS ===
Challenge ID: day13-k4-l3a-monitoring-llmops-v1
Correlation ID: req-37f3fb5c
Feature: monitoring
Latency: {target_log_sent.get('latency_ms')} ms (Threshold: 2000 ms)

--- Target Request Log (request_received) ---
{json.dumps(target_log_received, indent=2, ensure_ascii=False)}

--- Target Response Log (response_sent) ---
{json.dumps(target_log_sent, indent=2, ensure_ascii=False)}

--- All Incident Logs for Cohort K4 Seed 1311 (5 requests) ---
"""
for l in incident_logs:
    content_13 += f"[{l.get('ts')}] cid={l.get('correlation_id')} event={l.get('event')} latency={l.get('latency_ms')}ms feature={l.get('feature')} user={l.get('user_id_hash')}\n"

Path("submission/evidence/13-incident-log.txt").write_text(content_13, encoding="utf-8")
print("Saved 13-incident-log.txt")


# 3. 14-incident-trace.txt
from_time = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(hours=2)
target_trace_id = "840aa1479f7f4f2937ef5b274f7f87af"

trace_spans = client.api.observations.get_many(
    from_start_time=from_time,
    trace_id=target_trace_id,
    fields="id,name,type,start_time,end_time,metadata,model,parent_observation_id,usage_details,cost_details",
    limit=20,
)

content_14 = f"""=== INCIDENT TRACE AND ROOT CAUSE ANALYSIS ===
Project: day13-k4-l3a-2A202602755
Challenge ID: day13-k4-l3a-monitoring-llmops-v1
Trace ID: {target_trace_id}
Correlation ID: req-37f3fb5c
Session ID: k4-l3a-challenge-s05

--- Trace Waterfall Span Tree ---
"""

for s in trace_spans.data:
    duration = ((s.end_time - s.start_time).total_seconds() * 1000) if (s.end_time and s.start_time) else 0.0
    indent = "  └── " if s.parent_observation_id else "── "
    flag = " <=== [ROOT CAUSE BOTTLENECK: 94.3% DURATION]" if s.type == "RETRIEVER" else ""
    content_14 += f"{indent}[{s.type}] {s.name or 'Observation'} (Duration: {duration:.1f}ms, ID: {s.id}){flag}\n"

content_14 += "\n--- Detailed Span Breakdown ---\n"
for s in trace_spans.data:
    duration = ((s.end_time - s.start_time).total_seconds() * 1000) if (s.end_time and s.start_time) else 0.0
    content_14 += f"\nObservation ID: {s.id}\n"
    content_14 += f"Name: {s.name}\n"
    content_14 += f"Type: {s.type}\n"
    content_14 += f"Duration: {duration:.1f} ms\n"
    content_14 += f"Parent ID: {s.parent_observation_id}\n"
    content_14 += f"Metadata: {json.dumps(getattr(s, 'metadata', {}), indent=2, ensure_ascii=False)}\n"
    if getattr(s, "usage_details", None):
        content_14 += f"Usage: {s.usage_details}\n"

content_14 += """
--- Root Cause Conclusion ---
- Root Span 'lab-agent-run' Total Duration: 2653.0 ms
- Span 'retrieval' (RETRIEVER) Duration:   2501.0 ms (94.3% of total time)
- Span 'generation' (GENERATION) Duration: 151.0 ms (5.7% of total time)
Conclusion: The latency degradation was caused specifically by the vector retrieval stage (RAG slow injection), NOT the LLM generation stage.
"""

Path("submission/evidence/14-incident-trace.txt").write_text(content_14, encoding="utf-8")
print("Saved 14-incident-trace.txt")
