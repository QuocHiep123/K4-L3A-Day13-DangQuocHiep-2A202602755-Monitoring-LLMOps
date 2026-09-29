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

from_time = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(hours=2)

obs = client.api.observations.get_many(
    from_start_time=from_time,
    name="lab-agent-run",
    fields="id,trace_id,name,metadata,version,start_time,end_time",
    limit=50,
)

incident_cids = ["req-777e84cf", "req-44c808aa", "req-a2f92ad3", "req-80c44ad0", "req-37f3fb5c"]
found_traces = {}

for o in obs.data:
    meta = getattr(o, "metadata", {}) or {}
    cid = meta.get("correlation_id")
    if cid in incident_cids:
        duration = ((o.end_time - o.start_time).total_seconds() * 1000) if (o.end_time and o.start_time) else 0.0
        found_traces[cid] = {
            "trace_id": o.trace_id,
            "root_obs_id": o.id,
            "duration_ms": duration,
            "metadata": meta,
        }

print("Found incident traces:")
for cid, info in found_traces.items():
    print(f"CID: {cid} -> Trace ID: {info['trace_id']} (Duration: {info['duration_ms']:.1f}ms)")

# Fetch spans for primary incident trace: req-37f3fb5c
target_cid = "req-37f3fb5c"
target_trace_id = found_traces[target_cid]["trace_id"]
print(f"\nFetching spans for target trace: {target_trace_id}")

trace_spans = client.api.observations.get_many(
    from_start_time=from_time,
    trace_id=target_trace_id,
    fields="id,name,type,start_time,end_time,metadata,model,parent_observation_id",
    limit=20,
)

print(f"Total spans found: {len(trace_spans.data)}")
for s in trace_spans.data:
    duration = ((s.end_time - s.start_time).total_seconds() * 1000) if (s.end_time and s.start_time) else 0.0
    print(f"  [{s.type}] {s.name} - Duration: {duration:.1f}ms - Parent: {s.parent_observation_id}")
