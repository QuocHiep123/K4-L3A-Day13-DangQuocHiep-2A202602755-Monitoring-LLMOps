from __future__ import annotations

import json
import math
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any

from .logging_config import LOG_PATH


def _percentile(values: list[float], p: float) -> float:
    if not values:
        return 0.0
    values = sorted(values)
    k = (len(values) - 1) * (p / 100.0)
    f = math.floor(k)
    c = math.ceil(k)
    if f == c:
        return float(values[int(k)])
    d0 = values[int(f)] * (c - k)
    d1 = values[int(c)] * (k - f)
    return float(d0 + d1)


def get_dashboard_metrics() -> dict[str, Any]:
    if not LOG_PATH.exists():
        return {
            "latency": {"p50": 0, "p95": 0, "p99": 0, "ttft_p95": 0},
            "traffic": {"count": 0, "rate_per_minute": 0},
            "errors": {"error_rate_pct": 0.0, "count_by_value": {}, "tool_success_rate_pct": 100.0},
            "cost": {"total": 0.0, "sum_by_minute": []},
            "tokens": {"tokens_in": 0, "tokens_out": 0, "sum_by_field": 0},
            "quality": {"mean": 0.0},
            "time_range_minutes": 60,
        }

    records = []
    now = datetime.now(timezone.utc)
    window_start = now - timedelta(minutes=60)

    for line in LOG_PATH.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            rec = json.loads(line)
            # Parse timestamp if available
            ts_str = rec.get("ts")
            if ts_str:
                ts = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
                if ts >= window_start:
                    records.append(rec)
            else:
                records.append(rec)
        except Exception:
            continue

    latencies: list[float] = []
    ttfts: list[float] = []
    requests_received = 0
    requests_failed = 0
    error_types: dict[str, int] = {}
    tool_successes = 0
    tool_total = 0
    cost_total = 0.0
    cost_by_minute: dict[str, float] = {}
    tokens_in_total = 0
    tokens_out_total = 0
    quality_scores: list[float] = []

    for r in records:
        event = r.get("event")
        if event == "request_received":
            requests_received += 1
        elif event == "request_failed":
            requests_failed += 1
            etype = r.get("error_type", "UnknownError")
            error_types[etype] = error_types.get(etype, 0) + 1
            if r.get("tool_name") == "retrieval":
                tool_total += 1

        if event == "response_sent":
            lat = r.get("latency_ms")
            if lat is not None:
                latencies.append(float(lat))
            ttft = r.get("ttft_ms")
            if ttft is not None:
                ttfts.append(float(ttft))
            cost = r.get("cost_usd", 0.0)
            cost_total += cost
            ts_min = r.get("ts", "")[:16]
            cost_by_minute[ts_min] = cost_by_minute.get(ts_min, 0.0) + cost
            tokens_in_total += int(r.get("tokens_in", 0))
            tokens_out_total += int(r.get("tokens_out", 0))
            q = r.get("quality_score")
            if q is not None:
                quality_scores.append(float(q))
            if r.get("tool_name") == "retrieval":
                tool_total += 1
                if r.get("tool_success") is True:
                    tool_successes += 1

    error_rate = (requests_failed / requests_received * 100) if requests_received > 0 else 0.0
    tool_success_rate = (tool_successes / tool_total * 100) if tool_total > 0 else 100.0
    quality_mean = (sum(quality_scores) / len(quality_scores)) if quality_scores else 0.0

    return {
        "latency": {
            "p50": round(_percentile(latencies, 50), 1),
            "p95": round(_percentile(latencies, 95), 1),
            "p99": round(_percentile(latencies, 99), 1),
            "ttft_p95": round(_percentile(ttfts, 95), 1),
            "unit": "ms",
            "threshold": 3000,
        },
        "traffic": {
            "count": requests_received,
            "rate_per_minute": round(requests_received / 60.0, 2),
            "unit": "requests_per_minute",
            "threshold": 1,
        },
        "errors": {
            "error_rate_pct": round(error_rate, 2),
            "count_by_value": error_types,
            "tool_success_rate_pct": round(tool_success_rate, 1),
            "unit": "percent",
            "threshold": 2,
        },
        "cost": {
            "total": round(cost_total, 4),
            "sum_by_minute": [{"minute": k, "cost": round(v, 4)} for k, v in sorted(cost_by_minute.items())],
            "unit": "usd",
            "threshold": 2.5,
        },
        "tokens": {
            "tokens_in": tokens_in_total,
            "tokens_out": tokens_out_total,
            "sum_by_field": tokens_in_total + tokens_out_total,
            "unit": "tokens",
            "threshold": 50000,
        },
        "quality": {
            "mean": round(quality_mean, 3),
            "unit": "score_0_to_1",
            "threshold": 0.75,
        },
        "time_range_minutes": 60,
    }


def render_dashboard_html() -> str:
    m = get_dashboard_metrics()
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>K4-L3A Day 13 Monitoring &amp; LLMOps Dashboard</title>
  <meta http-equiv="refresh" content="30">
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500;700&family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap" rel="stylesheet">
  <style>
    :root {{
      --bg: #090d16;
      --card-bg: rgba(18, 24, 38, 0.75);
      --card-border: rgba(255, 255, 255, 0.08);
      --card-hover: rgba(255, 255, 255, 0.12);
      --text: #f1f5f9;
      --text-muted: #94a3b8;
      --primary: #38bdf8;
      --accent: #818cf8;
      --success: #34d399;
      --warning: #fbbf24;
      --danger: #f87171;
    }}
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{
      background: radial-gradient(circle at top right, #111827, var(--bg));
      color: var(--text);
      font-family: 'Plus Jakarta Sans', sans-serif;
      min-height: 100vh;
      padding: 28px;
    }}
    .header {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 24px;
      padding-bottom: 20px;
      border-bottom: 1px solid var(--card-border);
    }}
    .title h1 {{
      font-size: 24px;
      font-weight: 800;
      letter-spacing: -0.02em;
      background: linear-gradient(135deg, #fff 30%, #94a3b8);
      -webkit-background-clip: text;
      -webkit-text-fill-color: transparent;
    }}
    .subtitle {{
      color: var(--text-muted);
      font-size: 13px;
      margin-top: 4px;
    }}
    .meta-badges {{
      display: flex;
      gap: 10px;
      align-items: center;
    }}
    .badge {{
      background: rgba(255, 255, 255, 0.05);
      border: 1px solid var(--card-border);
      padding: 6px 12px;
      border-radius: 20px;
      font-size: 12px;
      font-family: 'JetBrains Mono', monospace;
      color: var(--text-muted);
    }}
    .badge.active {{
      border-color: rgba(56, 189, 248, 0.3);
      color: var(--primary);
      background: rgba(56, 189, 248, 0.08);
    }}
    .grid {{
      display: grid;
      grid-template-columns: repeat(3, 1fr);
      gap: 20px;
    }}
    @media (max-width: 1024px) {{
      .grid {{ grid-template-columns: repeat(2, 1fr); }}
    }}
    @media (max-width: 640px) {{
      .grid {{ grid-template-columns: 1fr; }}
    }}
    .panel {{
      background: var(--card-bg);
      backdrop-filter: blur(12px);
      border: 1px solid var(--card-border);
      border-radius: 16px;
      padding: 22px;
      position: relative;
      display: flex;
      flex-direction: column;
      justify-content: space-between;
      transition: all 0.2s ease;
    }}
    .panel:hover {{
      border-color: var(--card-hover);
      transform: translateY(-2px);
      box-shadow: 0 12px 30px rgba(0, 0, 0, 0.35);
    }}
    .panel-header {{
      display: flex;
      justify-content: space-between;
      align-items: flex-start;
      margin-bottom: 16px;
    }}
    .panel-title {{
      font-size: 14px;
      font-weight: 600;
      color: var(--text);
    }}
    .panel-id {{
      font-family: 'JetBrains Mono', monospace;
      font-size: 11px;
      color: var(--text-muted);
      text-transform: uppercase;
      letter-spacing: 0.05em;
    }}
    .metric-value {{
      font-size: 32px;
      font-weight: 800;
      font-family: 'JetBrains Mono', monospace;
      letter-spacing: -0.03em;
      margin-bottom: 8px;
    }}
    .metric-unit {{
      font-size: 14px;
      font-weight: 500;
      color: var(--text-muted);
      margin-left: 4px;
    }}
    .stats-row {{
      display: grid;
      grid-template-columns: repeat(2, 1fr);
      gap: 10px;
      margin-top: 14px;
      padding-top: 14px;
      border-top: 1px solid rgba(255, 255, 255, 0.05);
    }}
    .stat-item {{
      font-size: 12px;
      color: var(--text-muted);
    }}
    .stat-item strong {{
      color: var(--text);
      font-family: 'JetBrains Mono', monospace;
      display: block;
      font-size: 14px;
      margin-top: 2px;
    }}
    .threshold-badge {{
      display: inline-flex;
      align-items: center;
      gap: 6px;
      font-size: 11px;
      font-family: 'JetBrains Mono', monospace;
      padding: 4px 8px;
      border-radius: 6px;
      margin-top: 12px;
      background: rgba(255, 255, 255, 0.04);
      border: 1px solid rgba(255, 255, 255, 0.06);
    }}
    .status-dot {{
      width: 6px;
      height: 6px;
      border-radius: 50%;
    }}
    .status-ok {{ background: var(--success); box-shadow: 0 0 8px var(--success); }}
    .status-warn {{ background: var(--warning); box-shadow: 0 0 8px var(--warning); }}
    .status-danger {{ background: var(--danger); box-shadow: 0 0 8px var(--danger); }}
    .footer {{
      margin-top: 28px;
      text-align: center;
      font-size: 12px;
      color: var(--text-muted);
    }}
  </style>
</head>
<body>
  <div class="header">
    <div class="title">
      <h1>K4-L3A Day 13 Monitoring &amp; LLMOps</h1>
      <div class="subtitle">System Observability Dashboard &bull; Live Contract Runtime</div>
    </div>
    <div class="meta-badges">
      <div class="badge active">&bull; Time Range: 60m</div>
      <div class="badge active">&bull; Refresh: 30s</div>
      <div class="badge">Source: data/logs.jsonl</div>
    </div>
  </div>

  <div class="grid">
    <!-- Panel 1: Latency -->
    <div class="panel" id="panel-latency">
      <div class="panel-header">
        <div class="panel-title">Latency percentiles and TTFT</div>
        <div class="panel-id">latency</div>
      </div>
      <div>
        <div class="metric-value" style="color: {'var(--danger)' if m['latency']['p95'] > m['latency']['threshold'] else 'var(--primary)'}">
          {m['latency']['p95']}<span class="metric-unit">ms (P95)</span>
        </div>
        <div class="threshold-badge">
          <span class="status-dot {'status-danger' if m['latency']['p95'] > m['latency']['threshold'] else 'status-ok'}"></span>
          Threshold: P95 &le; {m['latency']['threshold']} ms
        </div>
      </div>
      <div class="stats-row">
        <div class="stat-item">Latency P50<strong>{m['latency']['p50']} ms</strong></div>
        <div class="stat-item">Latency P99<strong>{m['latency']['p99']} ms</strong></div>
        <div class="stat-item">TTFT P95<strong>{m['latency']['ttft_p95']} ms</strong></div>
        <div class="stat-item">SLO Limit<strong>&le; 3000 ms</strong></div>
      </div>
    </div>

    <!-- Panel 2: Traffic -->
    <div class="panel" id="panel-traffic">
      <div class="panel-header">
        <div class="panel-title">Request traffic</div>
        <div class="panel-id">traffic</div>
      </div>
      <div>
        <div class="metric-value" style="color: var(--primary)">
          {m['traffic']['count']}<span class="metric-unit">reqs</span>
        </div>
        <div class="threshold-badge">
          <span class="status-dot {'status-ok' if m['traffic']['rate_per_minute'] >= m['traffic']['threshold'] else 'status-warn'}"></span>
          Threshold: Rate &ge; {m['traffic']['threshold']} req/min
        </div>
      </div>
      <div class="stats-row">
        <div class="stat-item">Rate/Min<strong>{m['traffic']['rate_per_minute']} req/m</strong></div>
        <div class="stat-item">Window<strong>60 min</strong></div>
      </div>
    </div>

    <!-- Panel 3: Errors -->
    <div class="panel" id="panel-errors">
      <div class="panel-header">
        <div class="panel-title">Error rate and retrieval success</div>
        <div class="panel-id">errors</div>
      </div>
      <div>
        <div class="metric-value" style="color: {'var(--danger)' if m['errors']['error_rate_pct'] > m['errors']['threshold'] else 'var(--success)'}">
          {m['errors']['error_rate_pct']}<span class="metric-unit">% err</span>
        </div>
        <div class="threshold-badge">
          <span class="status-dot {'status-danger' if m['errors']['error_rate_pct'] > m['errors']['threshold'] else 'status-ok'}"></span>
          Threshold: Error Rate &le; {m['errors']['threshold']}%
        </div>
      </div>
      <div class="stats-row">
        <div class="stat-item">Retrieval Success<strong>{m['errors']['tool_success_rate_pct']}%</strong></div>
        <div class="stat-item">Error Breakdown<strong>{len(m['errors']['count_by_value'])} types</strong></div>
      </div>
    </div>

    <!-- Panel 4: Cost -->
    <div class="panel" id="panel-cost">
      <div class="panel-header">
        <div class="panel-title">Cost over time</div>
        <div class="panel-id">cost</div>
      </div>
      <div>
        <div class="metric-value" style="color: var(--accent)">
          ${m['cost']['total']}<span class="metric-unit">USD</span>
        </div>
        <div class="threshold-badge">
          <span class="status-dot {'status-danger' if m['cost']['total'] > m['cost']['threshold'] else 'status-ok'}"></span>
          Threshold: Total &le; ${m['cost']['threshold']}
        </div>
      </div>
      <div class="stats-row">
        <div class="stat-item">Active Minutes<strong>{len(m['cost']['sum_by_minute'])} min</strong></div>
        <div class="stat-item">Budget Limit<strong>$2.50 USD</strong></div>
      </div>
    </div>

    <!-- Panel 5: Tokens -->
    <div class="panel" id="panel-tokens">
      <div class="panel-header">
        <div class="panel-title">Input and output tokens</div>
        <div class="panel-id">tokens</div>
      </div>
      <div>
        <div class="metric-value" style="color: var(--text)">
          {m['tokens']['sum_by_field']:,}<span class="metric-unit">tok</span>
        </div>
        <div class="threshold-badge">
          <span class="status-dot {'status-danger' if m['tokens']['sum_by_field'] > m['tokens']['threshold'] else 'status-ok'}"></span>
          Threshold: Sum &le; {m['tokens']['threshold']:,} tok
        </div>
      </div>
      <div class="stats-row">
        <div class="stat-item">Tokens In<strong>{m['tokens']['tokens_in']:,}</strong></div>
        <div class="stat-item">Tokens Out<strong>{m['tokens']['tokens_out']:,}</strong></div>
      </div>
    </div>

    <!-- Panel 6: Quality -->
    <div class="panel" id="panel-quality">
      <div class="panel-header">
        <div class="panel-title">Quality proxy</div>
        <div class="panel-id">quality</div>
      </div>
      <div>
        <div class="metric-value" style="color: {'var(--success)' if m['quality']['mean'] >= m['quality']['threshold'] else 'var(--warning)'}">
          {m['quality']['mean']}<span class="metric-unit">/ 1.0</span>
        </div>
        <div class="threshold-badge">
          <span class="status-dot {'status-ok' if m['quality']['mean'] >= m['quality']['threshold'] else 'status-warn'}"></span>
          Threshold: Mean &ge; {m['quality']['threshold']}
        </div>
      </div>
      <div class="stats-row">
        <div class="stat-item">Evaluator<strong>Heuristic RAG</strong></div>
        <div class="stat-item">Quality Target<strong>&ge; 0.75</strong></div>
      </div>
    </div>
  </div>

  <div class="footer">
    Student: Đặng Quốc Hiệp &bull; MSSV: 2A202602755 &bull; K4-L3A Day 13 LLMOps
  </div>
</body>
</html>"""
