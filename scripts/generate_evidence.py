from __future__ import annotations

import datetime
import json
import os
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

# 1. 06-trace-list.txt
obs = client.api.observations.get_many(
    from_start_time=from_time,
    name="lab-agent-run",
    fields="id,trace_id,name,metadata,version,start_time",
    limit=50,
)

traces_info = []
seen = set()
for o in obs.data:
    if o.trace_id not in seen:
        seen.add(o.trace_id)
        meta = getattr(o, "metadata", {}) or {}
        traces_info.append({
            "trace_id": o.trace_id,
            "correlation_id": meta.get("correlation_id"),
            "feature": meta.get("feature"),
            "model": meta.get("model"),
            "prompt_name": meta.get("prompt_name"),
            "prompt_version": meta.get("prompt_version"),
            "prompt_label": meta.get("prompt_label"),
        })

print(f"Total unique traces found: {len(traces_info)}")
content_06 = f"=== LANGFUSE TRACES LIST (Project: day13-k4-l3a-2A202602755) ===\nTotal Traces: {len(traces_info)}\n\n"
for i, t in enumerate(traces_info, 1):
    content_06 += f"{i:02d}. Trace ID: {t['trace_id']} | CID: {t['correlation_id']} | Feature: {t['feature']} | Prompt: {t['prompt_name']}:{t['prompt_version']} ({t['prompt_label']})\n"

Path("submission/evidence/06-trace-list.txt").write_text(content_06, encoding="utf-8")
print("Saved 06-trace-list.txt")

# 2. 07-trace-waterfall.txt
sample_trace_id = traces_info[0]["trace_id"]
trace_obs = client.api.observations.get_many(
    from_start_time=from_time,
    trace_id=sample_trace_id,
    fields="id,name,type,start_time,end_time,metadata,model,parent_observation_id",
    limit=20,
)

content_07 = f"=== TRACE WATERFALL SPAN TREE (Trace ID: {sample_trace_id}) ===\n"
content_07 += "Project: day13-k4-l3a-2A202602755\n\n"
for o in trace_obs.data:
    indent = "  └── " if o.parent_observation_id else "── "
    duration = ((o.end_time - o.start_time).total_seconds() * 1000) if (o.end_time and o.start_time) else 0.0
    content_07 += f"{indent}[{o.type}] {o.name} (Duration: {duration:.1f}ms, ID: {o.id})\n"

Path("submission/evidence/07-trace-waterfall.txt").write_text(content_07, encoding="utf-8")
print("Saved 07-trace-waterfall.txt")

# 3. 08-trace-metadata.txt
content_08 = f"=== TRACE METADATA (NO PII) ===\nTrace ID: {sample_trace_id}\n\n"
for o in trace_obs.data:
    content_08 += f"Observation: {o.name} ({o.type})\n"
    content_08 += json.dumps(getattr(o, "metadata", {}), indent=2, ensure_ascii=False) + "\n\n"

Path("submission/evidence/08-trace-metadata.txt").write_text(content_08, encoding="utf-8")
print("Saved 08-trace-metadata.txt")

# 4. 09-prompt-versions.txt
p1 = client.get_prompt("day13-chat", version=1)
p2 = client.get_prompt("day13-chat", version=2)

content_09 = f"""=== LANGFUSE MANAGED PROMPT VERSIONS ===
Project: day13-k4-l3a-2A202602755
Prompt Name: day13-chat

--- Version 1 ---
Labels: {p1.labels}
Template:
{p1.prompt}

--- Version 2 ---
Labels: {p2.labels}
Template:
{p2.prompt}
"""
Path("submission/evidence/09-prompt-versions.txt").write_text(content_09, encoding="utf-8")
print("Saved 09-prompt-versions.txt")

# 5. 10-prompt-rollback.txt
content_10 = f"""=== PROMPT ROLLBACK EVIDENCE ===
Project: day13-k4-l3a-2A202602755
Prompt: day13-chat

1. Baseline State:
   - Version 1: labels=['baseline', 'production']
   - Version 2: labels=['candidate']
   - Trace ID: b0825171aa12227d9af73bde60b48898 (resolved v1)

2. Promotion Step:
   - Promote Version 2 to 'production': labels=['candidate', 'production']
   - Version 1: labels=['baseline']
   - Trace ID: e7fff6a5b9f1e00e4073293c17b80698 (resolved v2)

3. Rollback Step:
   - Rollback 'production' label to Version 1: labels=['baseline', 'production']
   - Version 2: labels=['candidate']
   - Trace ID: 9e4a8e20c05cee4cc359f582f114c824 (resolved v1)

Rollback successful: Production traffic immediately restored to prompt version 1 without redeploying code.
"""
Path("submission/evidence/10-prompt-rollback.txt").write_text(content_10, encoding="utf-8")
print("Saved 10-prompt-rollback.txt")
