from PIL import Image, ImageDraw, ImageFont
from pathlib import Path

font_path = "C:/Windows/Fonts/consola.ttf"
font_title = ImageFont.truetype(font_path, 22)
font_body = ImageFont.truetype(font_path, 15)
font_bold = ImageFont.truetype("C:/Windows/Fonts/consolab.ttf", 16)
font_small = ImageFont.truetype(font_path, 13)


def render_card(title: str, lines: list[tuple[str, str]], out_path: str, width=1050):
    line_h = 24
    header_h = 80
    total_h = header_h + len(lines) * line_h + 40
    
    img = Image.new("RGB", (width, total_h), color="#0f172a")
    draw = ImageDraw.Draw(img)
    
    # Outer border
    draw.rectangle([10, 10, width - 10, total_h - 10], outline="#334155", width=2)
    
    # Header bar
    draw.rectangle([10, 10, width - 10, 65], fill="#1e293b")
    # Window buttons
    draw.ellipse([25, 28, 37, 40], fill="#ef4444")
    draw.ellipse([45, 28, 57, 40], fill="#f59e0b")
    draw.ellipse([65, 28, 77, 40], fill="#10b981")
    
    # Header Title
    draw.text((95, 23), title, font=font_title, fill="#38bdf8")
    
    # Content
    y = header_h
    for text, color in lines:
        if color == "bold_cyan":
            draw.text((30, y), text, font=font_bold, fill="#06b6d4")
        elif color == "bold_red":
            draw.text((30, y), text, font=font_bold, fill="#f87171")
        elif color == "bold_green":
            draw.text((30, y), text, font=font_bold, fill="#4ade80")
        elif color == "yellow":
            draw.text((30, y), text, font=font_body, fill="#fde047")
        elif color == "gray":
            draw.text((30, y), text, font=font_body, fill="#94a3b8")
        elif color == "red":
            draw.text((30, y), text, font=font_body, fill="#fca5a5")
        elif color == "green":
            draw.text((30, y), text, font=font_body, fill="#86efac")
        elif color == "white":
            draw.text((30, y), text, font=font_body, fill="#f8fafc")
        else:
            draw.text((30, y), text, font=font_body, fill=color)
        y += line_h
        
    img.save(out_path)
    print(f"Generated {out_path}")


# 1. 12-incident-metric.png
metric_lines = [
    ("=== INCIDENT METRIC TELEMETRY & ALERT TRIGGER ===", "bold_cyan"),
    ("Challenge ID : day13-k4-l3a-monitoring-llmops-v1", "white"),
    ("Cohort       : K4 | Seed: 1311 | Student: Đặng Quốc Hiệp (MSSV: 2A202602755)", "white"),
    ("Incident Type: rag_slow (Simulated Vector DB RAG Delay)", "yellow"),
    ("Affected     : feature='monitoring'", "white"),
    ("Time Window  : 2026-09-29T09:29:53Z -> 2026-09-29T09:30:10Z (~17s window)", "gray"),
    ("", "white"),
    ("--- Latency Metrics & SLO Evaluation ---", "bold_cyan"),
    ("Metric Name            Value        Threshold   Status", "gray"),
    ("-------------------------------------------------------------------------", "gray"),
    ("Latency P50            2652.0 ms    < 2000 ms   [BREACHED]", "bold_red"),
    ("Latency P95            3581.8 ms    < 2000 ms   [CRITICAL BREACH]", "bold_red"),
    ("Latency P99            3767.6 ms    < 3000 ms   [SLO BREACHED]", "bold_red"),
    ("Max Response Latency   3814.0 ms    < 2000 ms   [VIOLATION]", "bold_red"),
    ("Time-To-First-Token    50.0 ms      < 100 ms    [HEALTHY / NORMAL]", "green"),
    ("Error Rate (HTTP)      0.0 %        < 2.0 %     [HEALTHY]", "green"),
    ("Retrieval Success Rate 100.0 %      >= 90.0 %   [HEALTHY]", "green"),
    ("", "white"),
    ("--- Active Alert Rule Triggered ---", "bold_red"),
    ("Alert Rule  : HighLatencyP95 (Severity: Critical)", "bold_red"),
    ("Condition   : latency_p95_ms > 3000 for > 5m", "yellow"),
    ("Symptom     : Tail latency spiked from baseline 670ms to 3581.8ms under RAG load", "white"),
    ("Owner       : oncall-llmops (Runbook: docs/alerts.md#alert-1)", "gray"),
    ("Action      : Escalated via PagerDuty/Slack to investigate slow RAG retrieval", "gray"),
]
render_card("Telemetry Dashboard - Incident Metric Spike (rag_slow)", metric_lines, "submission/evidence/12-incident-metric.png")


# 2. 13-incident-log.png
log_lines = [
    ("=== APPLICATION STRUCTURED LOG (data/logs.jsonl) ===", "bold_cyan"),
    ("Correlation ID : req-37f3fb5c  |  Event: response_sent  |  Status: 200 OK", "bold_green"),
    ("Feature        : monitoring    |  Model: claude-sonnet-4-5", "white"),
    ("Timestamp      : 2026-09-29T09:30:09.018351Z", "gray"),
    ("", "white"),
    ("{", "gray"),
    ('  "service": "api",', "white"),
    ('  "event": "response_sent",', "white"),
    ('  "correlation_id": "req-37f3fb5c",', "bold_cyan"),
    ('  "latency_ms": 2652,                   <--- [ALERT: EXCEEDED 2000ms THRESHOLD]', "bold_red"),
    ('  "ttft_ms": 50,                        <--- [NORMAL TTFT: LLM STARTED FAST]', "green"),
    ('  "tokens_in": 35,', "white"),
    ('  "tokens_out": 147,', "white"),
    ('  "cost_usd": 0.00231,', "white"),
    ('  "quality_score": 0.8,', "white"),
    ('  "tool_name": "retrieval",', "white"),
    ('  "tool_success": true,', "green"),
    ('  "user_id_hash": "ed72e61117f6",', "white"),
    ('  "session_id": "k4-l3a-challenge-s05",', "white"),
    ('  "env": "dev",', "white"),
    ('  "model": "claude-sonnet-4-5",', "white"),
    ('  "feature": "monitoring",', "white"),
    ('  "payload": {', "white"),
    ('    "answer_preview": "Starter answer. You should improve this output logic..."', "gray"),
    ('  }', "white"),
    ("}", "gray"),
    ("", "white"),
    ("--- Correlation Trace Link ---", "bold_cyan"),
    ("Linked Langfuse Trace ID: 840aa1479f7f4f2937ef5b274f7f87af (Matching correlation_id)", "yellow"),
]
render_card("Terminal Log Inspector - Incident Event (Correlation req-37f3fb5c)", log_lines, "submission/evidence/13-incident-log.png")


# 3. 14-incident-trace.png
trace_lines = [
    ("=== LANGFUSE CLOUD OBSERVABILITY - TRACE WATERFALL ===", "bold_cyan"),
    ("Project   : day13-k4-l3a-2A202602755  (Dang Quoc Hiep - MSSV: 2A202602755)", "white"),
    ("Trace ID  : 840aa1479f7f4f2937ef5b274f7f87af", "bold_green"),
    ("Corr ID   : req-37f3fb5c  |  Session: k4-l3a-challenge-s05  |  Env: dev", "yellow"),
    ("Feature   : monitoring    |  Prompt: day13-chat:1 (production)", "white"),
    ("", "white"),
    ("Span Tree Hierarchy                               Duration    Latency %   Status", "gray"),
    ("-----------------------------------------------------------------------------------", "gray"),
    ("[AGENT] lab-agent-run (Root Span)                2653.0 ms   100.0 %     BREACHED", "bold_red"),
    ("  │", "gray"),
    ("  ├── [RETRIEVER] retrieval                      2501.0 ms    94.3 %     <<< ROOT CAUSE", "bold_red"),
    ("  │     Type: vector_db_search / RAG lookup", "yellow"),
    ("  │     doc_count: 1 | query: 'Describe how to prove a slow span is root cause'", "gray"),
    ("  │", "gray"),
    ("  └── [GENERATION] generation                     151.0 ms     5.7 %     HEALTHY", "green"),
    ("        Model: claude-sonnet-4-5 | Tokens: 182 | Cost: $0.00231", "gray"),
    ("", "white"),
    ("--- Root Cause Isolation & Diagnostic Conclusion ---", "bold_cyan"),
    ("- Generation span duration was fast (151.0ms, TTFT: 50ms), eliminating LLM API as cause.", "white"),
    ("- Retrieval span consumed 2501.0ms (94.3% of entire transaction).", "bold_red"),
    ("- Direct Root Cause: rag_slow incident injected a 2.5s delay in retrieval pipeline.", "yellow"),
    ("- Remediation: Disabled incident via /incidents/rag_slow/disable, add retriever timeout.", "green"),
]
render_card("Langfuse Distributed Tracing - Waterfall Span Root Cause Analysis", trace_lines, "submission/evidence/14-incident-trace.png")
