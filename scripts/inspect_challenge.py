import json
from pathlib import Path

logs_path = Path("data/logs.jsonl")
with open(logs_path, "r", encoding="utf-8") as f:
    logs = [json.loads(line) for line in f if line.strip()]

monitoring_logs = [l for l in logs if l.get("feature") == "monitoring"]
print(f"Total monitoring logs: {len(monitoring_logs)}")
for l in monitoring_logs:
    ev = l.get("event")
    ts = l.get("ts")
    cid = l.get("correlation_id")
    lat = l.get("latency_ms")
    uid = l.get("user_id_hash")
    err = l.get("error_type")
    print(f"[{ts}] event={ev} cid={cid} latency={lat}ms user={uid} err={err}")
