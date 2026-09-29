# Template Alert và Runbook

Mỗi alert phải dựa trên triệu chứng người dùng hoặc SLO, không dựa trực tiếp vào tên implementation nội bộ.

## Alert 1

- Tên: HighLatencyP95
- Severity: critical
- Duration: 5m
- Kênh thông báo: Slack (#alerts-llmops)
- SLI/SLO liên quan: primary_slo.fast_successful_requests (latency <= 3000ms)
- Điều kiện và thời gian duy trì: `latency_p95_ms > 3000` liên tục trong 5 phút.
- Ảnh hưởng tới người dùng: Người dùng phản hồi chậm hoặc timeout, trải nghiệm chat bị gián đoạn.
- Ba bước kiểm tra đầu tiên:
  1. Kiểm tra panel Latency và TTFT trên Dashboard xem bottleneck ở khâu retrieval hay generation.
  2. Lọc log `data/logs.jsonl` tìm correlation ID có `latency_ms > 3000` và kiểm tra `payload.message_preview`.
  3. Mở trace trên Langfuse theo `correlation_id` để kiểm tra span tree (retrieval vs llm-generation).
- Mitigation tạm thời: Bật fallback prompt, giảm timeout của vector store/retrieval, hoặc chuyển traffic sang model dự phòng.
- Owner: oncall-llmops

## Alert 2

- Tên: HighErrorRate
- Severity: critical
- Duration: 3m
- Kênh thông báo: Slack (#alerts-llmops)
- SLI/SLO liên quan: guardrails.error_rate_pct_max (<= 2%)
- Điều kiện và thời gian duy trì: `error_rate_pct > 2.0%` liên tục trong 3 phút.
- Ảnh hưởng tới người dùng: Người dùng nhận mã lỗi HTTP 500 khi gửi tin nhắn vào hệ thống.
- Ba bước kiểm tra đầu tiên:
  1. Kiểm tra panel Errors trên Dashboard để xác định tỉ lệ lỗi và phân loại theo `error_type`.
  2. Tìm các log có `event == "request_failed"` trong `data/logs.jsonl` để lấy stack trace và `correlation_id`.
  3. Kiểm tra trace trên Langfuse để xem exception phát sinh tại span nào (ví dụ: `tool_fail` timeout, prompt format error).
- Mitigation tạm thời: Tắt incident nếu đang trong diễn tập diễn biến thử nghiệm (`/incidents/{name}/disable`), restart service hoặc điều hướng lưu lượng sang node dự phòng.
- Owner: oncall-llmops

## Alert 3

- Tên: LowRetrievalSuccess
- Severity: warning
- Duration: 5m
- Kênh thông báo: Slack (#alerts-rag)
- SLI/SLO liên quan: guardrails.retrieval_success_rate_pct_min (>= 90%)
- Điều kiện và thời gian duy trì: `retrieval_success_rate_pct < 90.0%` liên tục trong 5 phút.
- Ảnh hưởng tới người dùng: Câu trả lời giảm chất lượng, mô hình trả lời chung chung do thiếu tài liệu ngữ cảnh chính xác.
- Ba bước kiểm tra đầu tiên:
  1. Kiểm tra panel Errors & Retrieval Success trên Dashboard.
  2. Lọc log có `tool_name == "retrieval"` và `tool_success == false` để xác định lỗi kết nối vector database.
  3. Kiểm tra observation `retrieval` trên Langfuse trace xem trạng thái và metadata `doc_count`.
- Mitigation tạm thời: Kích hoạt fallback document cache hoặc chuyển sang corpus local tĩnh để tiếp tục phục vụ người dùng.
- Owner: oncall-rag
