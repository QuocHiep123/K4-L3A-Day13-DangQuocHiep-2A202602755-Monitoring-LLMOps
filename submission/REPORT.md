# Báo cáo cá nhân — K4-L3A Day 13 Monitoring & LLMOps

> Mỗi học viên hoàn thiện một file duy nhất này. Khi dẫn evidence, dùng đường dẫn tương đối, ví dụ `evidence/07-trace-waterfall.txt`.

## 1. Thông tin học viên

- **Họ và tên:** Đặng Quốc Hiệp
- **MSSV:** 2A202602755
- **Lớp:** K4-L3A
- **Repository URL:** https://github.com/QuocHiep123/K4-L3A-Day13-DangQuocHiep-2A202602755-Monitoring-LLMOps
- **Commit SHA cuối:** `759a99bf3e72d20317cb0a3cbf480a7bd36e6b9e`
- **Challenge ID:** `day13-k4-l3a-monitoring-llmops-v1`
- **Tên project Langfuse cá nhân:** `day13-k4-l3a-2A202602755`

## 2. Evidence index

Điền đúng đường dẫn tới evidence thực tế.

| Evidence | Đường dẫn |
|---|---|
| Pytest cuối | `evidence/01-pytest.txt` |
| Log validator | `evidence/02-log-validator.txt` |
| Dashboard validator | `evidence/03-dashboard-validator.txt` |
| Structured log | `evidence/04-structured-log.txt` |
| PII redaction | `evidence/05-pii-redaction.txt` |
| Trace list | `evidence/06-trace-list.txt` |
| Trace waterfall | `evidence/07-trace-waterfall.txt` |
| Trace metadata | `evidence/08-trace-metadata.txt` |
| Prompt versions | `evidence/09-prompt-versions.txt` |
| Prompt rollback | `evidence/10-prompt-rollback.txt` |
| Dashboard runtime | `evidence/11-dashboard-overview.png` |
| Incident metric | `evidence/12-incident-metric.png` |
| Incident log | `evidence/13-incident-log.png` |
| Incident trace | `evidence/14-incident-trace.png` |

## 3. Kết quả kỹ thuật

| Nội dung | Baseline | Kết quả cuối | Nhận xét |
|---|---|---|---|
| `validate_logs.py` | 30/100 | 100/100 | Vượt qua toàn bộ checklist: schema chuẩn, correlation ID propagation, log context enrichment, PII scrubbing sạch |
| `validate_dashboard.py` | 6/6 panel | 6/6 panel | Đầy đủ 6/6 panel contract theo đúng config/dashboard.yaml |
| `pytest` | 22 passed | 25 passed | Thêm unit tests cho CCCD, Credit Card, Passport scrubbing; toàn bộ suite pass 100% |
| Số traces hợp lệ | 0 | 35+ traces | Tự tạo và ghi nhận đầy đủ trên project Langfuse cá nhân với đủ cha-con (Agent -> Retrieval, Generation) |
| Số PII leak | 0 | 0 leak | Khử 100% PII mẫu (email, số điện thoại VN, CCCD, thẻ thanh toán, passport) trước khi serialize và ghi file |
| Latency P95 / TTFT P95 | 1810.9ms / 50ms | 670.5ms / 50.0ms | Độ trễ đuôi P95 duy trì tốt dưới ngưỡng SLO giới hạn 3000ms |
| Retrieval success rate | 100% | 100% | Đạt mục tiêu guardrail >= 90% khi không có sự cố |

## 4. Logging và PII

- **Cách tạo/nhận và truyền correlation ID:**
  - `CorrelationIdMiddleware` kiểm tra header `x-request-id` từ client. Nếu có, middleware sử dụng lại; nếu không, tự động sinh ID mới với format chuẩn `req-<8-hex>` thông qua `f"req-{uuid.uuid4().hex[:8]}"`.
  - Gọi `clear_contextvars()` ở đầu mỗi request để ngăn chặn triệt để rò rỉ dữ liệu giữa các request trong môi trường bất đồng bộ.
  - Sử dụng `bind_contextvars(correlation_id=correlation_id)` của structlog và gán `request.state.correlation_id = correlation_id`.
  - Đính kèm correlation ID và thời gian xử lý vào response header: `response.headers["x-request-id"] = correlation_id` và `response.headers["x-response-time-ms"] = str(duration_ms)`.
- **Các metadata được ghi vào structured log:**
  - Ở tầng API: `user_id_hash` (băm sha256 12 ký tự), `session_id`, `feature`, `model`, `env`, `correlation_id`.
  - Ở tầng Response: `latency_ms`, `ttft_ms`, `tokens_in`, `tokens_out`, `cost_usd`, `quality_score`, `tool_name`, `tool_success`, và `payload.answer_preview`.
  - Các trường chuẩn: `ts` (ISO UTC), `level` (INFO/ERROR), `service` ("api" hoặc "day13-monitoring-llmops-lab"), `event`.
- **Cách bảo đảm PII được scrub trước khi ghi:**
  - Bộ xử lý `scrub_event` trong `app/logging_config.py` duyệt đệ quy toàn bộ các trường chuỗi, từ điển, danh sách trong `event_dict` thông qua `_scrub_nested` và regex trong `PII_PATTERNS`.
  - Đăng ký `scrub_event` trong pipeline structlog ngay trước `JsonlFileProcessor()` và `JSONRenderer()`. Điều này đảm bảo dữ liệu luôn được che mặt nạ (`[REDACTED_...]`) trước khi serialize và ghi xuống đĩa hoặc stdout.
- **Cách kiểm chứng kết quả:**
  - Chạy `python scripts/validate_logs.py` đạt 100/100, xác nhận không còn bất kỳ dấu vết PII thô nào trong `data/logs.jsonl`.
  - Chạy `pytest tests/test_pii.py` xác minh các định dạng số điện thoại VN (`090...`, `+84...`, dấu chấm, gạch ngang), email, CCCD 12 số, thẻ tín dụng 16 số và hộ chiếu đều được che đúng.

## 5. Tracing và prompt versioning

- **Cách xác nhận traces do chính tôi tạo trong project cá nhân:**
  - Toàn bộ trace được gửi vào project `day13-k4-l3a-2A202602755` trên Langfuse Cloud bằng cặp khóa API cá nhân trong `.env`.
  - Mỗi trace chứa `user_id_hash`, `session_id`, environment `dev`, tags `["lab", feature, self.model]`, và metadata `correlation_id` khớp chính xác 1-1 với correlation ID trong structured log `data/logs.jsonl`.
- **Cấu trúc root/retrieval/generation observations:**
  - Root observation: `lab-agent-run` (type `AGENT`, capture input/output tắt để bảo vệ dữ liệu nhạy cảm).
  - Child observation 1: `retrieval` (type `RETRIEVER`, theo dõi quá trình gọi `retrieve()`, lưu `doc_count` và `query_preview`).
  - Child observation 2: `generation` (type `GENERATION`, theo dõi LLM generation, nhận `model`, `usage_details` (input/output/total tokens), `cost_details` (tổng chi phí USD), và đối tượng prompt được liên kết).
- **Cách nối trace với log:**
  - Dùng `correlation_id` làm khóa liên kết duy nhất. Từ một dòng log nghi vấn trong `data/logs.jsonl`, lấy `correlation_id` và lọc trên Langfuse để mở trace tương ứng.
- **Prompt name:** `day13-chat`
- **Version/label baseline:** Version 1 với labels `['baseline', 'production']`.
- **Version/label candidate:** Version 2 với label `['candidate']` (bổ sung chỉ dẫn trả lời ngắn gọn và căn cứ theo tài liệu).
- **Trace ID của mỗi version:**
  - Version 1 (label `baseline`): `b0825171aa12227d9af73bde60b48898` (CID: `req-92fc28d7`)
  - Version 2 (label `candidate`): `e170d696598751e6b64caecb0cb514d2` (CID: `req-e3182979`)
  - Version 2 sau khi promote (label `production`): `e7fff6a5b9f1e00e4073293c17b80698` (CID: `req-0fd096db`)
  - Version 1 sau khi rollback (label `production`): `9e4a8e20c05cee4cc359f582f114c824` (CID: `req-f6b86686`)
- **Cách promote và rollback `production`:**
  - Promote: Cập nhật nhãn thông qua SDK `client.update_prompt(name='day13-chat', version=2, new_labels=['candidate', 'production'])` và gỡ label `production` khỏi Version 1.
  - Rollback: Khi cần quay lại bản ổn định cũ, gọi `client.update_prompt(name='day13-chat', version=1, new_labels=['baseline', 'production'])`. Ứng dụng tự động cập nhật phiên bản prompt mới từ Langfuse Cloud theo nhãn `production` mà không cần khởi động lại server.

## 6. Dashboard, SLO và alerts

- **Dashboard và sáu panel:**
  - Dựng tại endpoint `/dashboard` trực tiếp trên FastAPI, sử dụng dữ liệu từ `data/logs.jsonl` trong cửa sổ 60 phút, tự động làm mới mỗi 30 giây:
    1. `latency`: P50, P95, P99 và TTFT P95 (threshold P95 <= 3000ms).
    2. `traffic`: Số lượng request và tốc độ trung bình theo phút (threshold >= 1 req/min).
    3. `errors`: Tỉ lệ lỗi %, phân loại theo error_type, tỉ lệ retrieval success % (threshold error <= 2%).
    4. `cost`: Tổng chi phí USD và chi phí theo từng phút (threshold total <= $2.50).
    5. `tokens`: Tổng số token in và token out (threshold sum <= 50,000 tokens).
    6. `quality`: Điểm chất lượng trung bình theo heuristic RAG (threshold mean >= 0.75).
- **SLO và lý do chọn:**
  - SLO: `primary_slo.fast_successful_requests` với mục tiêu 99.5% trong cửa sổ 28 ngày.
  - SLI: `(count(event == "response_sent" and latency_ms <= 3000) / count(event == "request_received")) * 100 >= 99.5%`.
  - Lý do: Phản ánh trực tiếp trải nghiệm người dùng thực tế; người dùng yêu cầu câu trả lời vừa chính xác vừa nhanh chóng dưới 3 giây.
- **Cách tính error budget:**
  - Error budget = `100% - 99.5% = 0.5%`.
  - Với lưu lượng 100,000 requests/tháng, chỉ cho phép tối đa 500 requests bị chậm hoặc thất bại. Khi mức tiêu hao vượt quá ngân sách, toàn bộ việc release tính năng mới bị dừng lại để ưu tiên xử lý độ tin cậy.
- **Ba alert và runbook tương ứng:**
  - 1. `HighLatencyP95` (critical, `latency_p95_ms > 3000`, duy trì 5m, owner: `oncall-llmops`, runbook: `docs/alerts.md#alert-1`).
  - 2. `HighErrorRate` (critical, `error_rate_pct > 2.0`, duy trì 3m, owner: `oncall-llmops`, runbook: `docs/alerts.md#alert-2`).
  - 3. `LowRetrievalSuccess` (warning, `retrieval_success_rate_pct < 90.0`, duy trì 5m, owner: `oncall-rag`, runbook: `docs/alerts.md#alert-3`).

## 7. Điều tra challenge

- **Challenge ID:** `day13-k4-l3a-monitoring-llmops-v1`
- **Khoảng thời gian điều tra:** `2026-09-29T09:29:53Z` đến `2026-09-29T09:30:10Z` (UTC; tức `16:29:53` đến `16:30:10` giờ địa phương).
- **Triệu chứng từ metrics:**
  - Độ trễ P50 tăng vọt lên **2652.0ms**, P95 đạt **3581.8ms**, P99 đạt **3767.6ms** (độ trễ lớn nhất ghi nhận là **3814.0ms**). Toàn bộ 5 queries của challenge đều vượt ngưỡng `latency_threshold_ms: 2000` của challenge và vượt ngưỡng SLO `3000ms`.
  - Alert rule `HighLatencyP95` (mức độ Critical) lập tức được kích hoạt do `latency_p95_ms > 3000ms`.
  - Tỷ lệ lỗi HTTP (`error_rate_pct`) vẫn là `0.0%` và `ttft_p95` giữ mức `50.0ms` (bình thường), chứng minh tiến trình sinh văn bản của LLM không bị trễ mà điểm nghẽn xảy ra hoàn toàn ở giai đoạn chuẩn bị trước khi LLM bắt đầu streaming/generate.
  - Tính năng bị ảnh hưởng: `feature: "monitoring"`.
- **Log line và correlation ID liên quan:**
  - Request điều tra tiêu biểu có `correlation_id: "req-37f3fb5c"`:
    - Log `request_received` lúc `2026-09-29T09:30:06.364048Z`: `user_id_hash="ed72e61117f6"`, `session_id="k4-l3a-challenge-s05"`, `feature="monitoring"`, `model="claude-sonnet-4-5"`.
    - Log `response_sent` lúc `2026-09-29T09:30:09.018351Z`: `latency_ms=2652`, `ttft_ms=50`, `tokens_in=35`, `tokens_out=147`, `cost_usd=0.00231`, `tool_name="retrieval"`, `tool_success=true`.
  - Toàn bộ 5 request trong cùng đợt challenge đều có correlation ID ghi nhận độ trễ bất thường: `req-777e84cf` (3814ms), `req-44c808aa` (2653ms), `req-a2f92ad3` (2652ms), `req-80c44ad0` (2652ms), `req-37f3fb5c` (2652ms).
- **Trace ID và span gây ảnh hưởng:**
  - Langfuse Trace ID tương ứng: `840aa1479f7f4f2937ef5b274f7f87af` (truy vết trực tiếp từ `correlation_id: "req-37f3fb5c"`).
  - Phân rã Waterfall Span Tree:
    - Root Span `[AGENT] lab-agent-run`: tổng thời gian **2653.0ms**.
    - Child Span 1 `[RETRIEVER] retrieval`: thời gian **2501.0ms** (chiếm **94.3%** tổng thời gian xử lý request).
    - Child Span 2 `[GENERATION] generation`: thời gian chỉ **151.0ms** (chiếm 5.7%).
  - Span gây ảnh hưởng chính là `retrieval` (RETRIEVER).
- **Root cause:**
  - Sự cố mô phỏng `rag_slow` (Seed: 1311) đã chèn độ trễ nhân tạo 2.5 giây vào hàm tìm kiếm tri thức RAG (`retrieval`) cho tính năng `feature="monitoring"`.
  - Do RAG retrieval bị nghẽn đồng bộ trong luồng xử lý, request bị giữ lại 2.5s khiến tổng thời gian phản hồi tăng vọt từ baseline 670ms lên hơn 2600ms - 3800ms, vi phạm nghiêm trọng SLO P95.
- **Fix action:**
  - Tắt ngay sự cố bằng cách gửi request vô hiệu hóa: `POST /incidents/rag_slow/disable` (hoặc lệnh `python scripts/inject_incident.py --disable`).
  - Thiết lập cơ chế timeout cho Retriever (ví dụ: giới hạn tối đa 1.5s), nếu quá thời gian thì tự động fallback sử dụng tri thức tĩnh có sẵn trong cache thay vì làm nghẽn toàn bộ luồng phản hồi của Agent.
- **Preventive measure:**
  - Tách luồng vector retrieval sang mô hình bất đồng bộ không chặn (async non-blocking) với connection pool riêng biệt.
  - Triển khai Redis Semantic Caching cho các câu hỏi tra cứu phổ biến nhằm giảm áp lực truy vấn trực tiếp vào Vector Database.
  - Áp dụng mẫu Circuit Breaker: nếu tỉ lệ trễ hoặc lỗi của Retriever vượt ngưỡng an toàn trong 1 phút, tự động kích hoạt chế độ degraded fallback để bảo toàn SLO độ trễ cho người dùng cuối.
  - Định tuyến cảnh báo `HighLatencyP95` trực tiếp tới kênh Slack và PagerDuty on-call để đội kỹ thuật can thiệp trong vòng 5 phút trước khi ảnh hưởng đến diện rộng.

## 8. Giải thích và tự đánh giá

- **Một quyết định kỹ thuật quan trọng và lý do:**
  - Tích hợp bộ lọc PII đệ quy ở mức logging processor (`scrub_event`) trong Structlog thay vì chỉ làm sạch ở controller. Quyết định này bảo vệ hệ thống theo nguyên tắc Defense in Depth: bất kể log được gọi từ đâu trong codebase, dữ liệu nhạy cảm của người dùng không bao giờ bị rò rỉ ra log file hoặc third-party telemetry.
- **Một lỗi/blocker đã gặp:**
  - Lệnh redirect output `>` trong shell PowerShell mặc định ghi mã hóa UTF-16LE, gây lỗi không đọc được trên một số công cụ đọc text chuẩn UTF-8.
- **Cách tìm nguyên nhân và xử lý:**
  - Phân tích thông báo lỗi định dạng của parser, viết script helper bằng Python xuất file với tham số `encoding="utf-8"` rõ ràng cho toàn bộ các file bằng chứng text.
- **Cách hiểu luồng Metrics → Logs → Traces:**
  - **Metrics** là còi báo động: cho biết hệ thống đang gặp triệu chứng gì (độ trễ tăng, lỗi nhảy vọt) và mốc thời gian bắt đầu.
  - **Logs** là kính lúp: dùng mốc thời gian từ metric để khoanh vùng và tìm ra chính xác request nào gặp sự cố, trích xuất mã định danh `correlation_id`.
  - **Traces** là dao mổ: lấy `correlation_id` mở span tree chi tiết để thấy chính xác dòng code, câu truy vấn vector DB hay lần gọi LLM nào bị nghẽn/thất bại, từ đó kết luận nguyên nhân gốc rễ.
- **Vai trò của prompt version, token/cost, SLO hoặc rollback trong vận hành LLM:**
  - Giúp quản lý vòng đời ứng dụng AI có kiểm soát. Prompt không phải chỉ là chuỗi string tĩnh mà là cấu hình nghiệp vụ quan trọng. Khả năng truy vết version gắn liền với trace và cơ chế rollback tức thì cho phép nhóm kỹ thuật thử nghiệm cải tiến mà không sợ làm gián đoạn dịch vụ sản xuất nếu prompt mới gây ảo giác, tăng chi phí hoặc vi phạm SLO.
- **Điều quan trọng nhất đã học:**
  - Làm chủ quy trình Observability chuẩn mực cho hệ thống LLMOps hiện đại: Structured Logging, Correlation Tracing, Prompt Management và Symptom-based Alerting.
- **Hạn chế hoặc phần chưa hoàn thành:**
  - Toàn bộ các checkpoint từ CP0 đến CP4 đã được hoàn thành đầy đủ, kiểm thử và xác minh trên repository thực tế; evidence đã được tạo và lưu trữ đầy đủ trong thư mục `submission/evidence/`.

## 9. Checklist trước khi nộp

- [x] Kết quả và evidence thuộc commit SHA cuối.
- [x] Tất cả ảnh/output mở được bằng đường dẫn tương đối.
- [x] Incident evidence nối đúng metric → log → trace (CP3).
- [x] Trace/prompt evidence thuộc project Langfuse cá nhân và ảnh không lộ key/secret.
- [x] Repository chạy lại được theo README.
- [x] Không có secret, API key, PII thô hoặc evidence của người khác/lớp khác.
- [x] URL repo và commit SHA cuối đã được nộp trên LMS/Codelabs.
