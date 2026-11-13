# Báo cáo cá nhân — Day 6

Họ tên: Nguyễn Đình Quang · MSSV: 2A202603620

## Dữ liệu và pipeline
- **Chủ đề, nguồn/quyền, số trang và quy tắc tính trang:** Hướng dẫn sản phẩm: tài liệu Godot Engine (repo `godotengine/godot-docs`, file `.rst`, commit `c5b3485cb4`). Giấy phép CC BY 3.0, ghi công "Juan Linietsky, Ariel Manzur and the Godot community" (data/ATTRIBUTION.md); không dùng thư mục `classes/` (MIT). Lấy dữ liệu bằng clone từng phần (`--filter=blob:none --sparse`) chỉ gồm file `.rst` của 6 thư mục. Corpus gồm **36 đơn vị nguồn, 317.150 ký tự**, 6 file mỗi topic (2d, 3d, physics, scripting, inputs, step_by_step). Quy tắc tính: file `.rst` không phân trang nên 1 file hợp lệ = 1 đơn vị độc lập (page = source_id), ≥1.500 ký tự sau chuẩn hóa. Chọn theo quy tắc xác định: trong mỗi thư mục sắp xếp theo đường dẫn, lấy tối đa 6 file đầu tiên hợp lệ; loại `index.rst` và file bắt đầu bằng `_`. Không nhân bản dữ liệu. Ngày lấy: 2026-11-13. File bị loại và lý do: results/corpus_log.csv.
- **Chuẩn hóa, lỗi và giới hạn:** Unicode NFC, thống nhất xuống dòng và khoảng trắng; bỏ directive (toctree, image, comment, anchor), đổi role `:ref:` thành văn bản, đổi heading RST thành `#`; giữ đoạn văn, code, admonition (Note:, Warning:) và bảng đơn giản. Bộ chuyển dùng regex tự viết, không dùng docutils. Giới hạn: một số câu chứa liên kết bị rút ngắn (ví dụ "This is covered on the"), tên lớp còn dạng `class_Xxx`, bảng bị đơn giản hóa, code mất nhãn ngôn ngữ. Evidence kiểm chứng trên chính văn bản đã chuẩn hóa này.
- **Embedding, vector store, lệnh chạy, chi phí:** `google/embeddinggemma-2`, chạy local qua sentence-transformers 6.3.0 (torch 2.15.0, transformers 5.22.2, Python 3.13.2, Windows 11), CPU, tải ở dạng `bfloat16`, **768 chiều**, chuẩn hóa L2, không cắt MRL. Prompt lấy từ `model.prompts`: query `task: search result | query: `, document `title: none | text: `. Vector store: Chroma 1.5.9 `PersistentClient` (data/chroma), metric **cosine**, HNSW (tìm kiếm xấp xỉ), 2 collection `godot_A`, `godot_B`. Lệnh: `python -m src.run info | ingest | evaluate --split dev|test | audit | report` (README.md). Chi phí: **$0** (local).
- **Metadata và trường lọc:** Bắt buộc: `document_id`, `source` (đường dẫn file gốc), `page` (= source_id vì không phân trang). Bổ sung: `category` (thư mục cấp 1), **`topic` (thư mục cấp 2, trường lọc)**, `section` (heading gần nhất), `section_path`, `char_start/char_end`, `content_hash`, `chunk_index`. Giá trị `category` và `topic` lấy từ đường dẫn thư mục, kiểm chứng được qua manifest, không đoán. Chọn `topic` làm filter vì có 6 giá trị phân biệt được và nhiều tài liệu 2D/3D có nội dung song song. Hạn chế: `topic` thô (topic `physics` gồm cả 2D lẫn 3D), `category` gần như hằng số (30 file `tutorials`, 6 file `getting_started`).

## Cấu hình và benchmark
- **A / B / C:** A: chunk cố định 500 ký tự, overlap 50, không lọc. B: chia theo heading rồi gom đoạn tối đa 1.200 ký tự (section thân <150 ký tự gộp sang section sau), không lọc. C: dùng **chính index của B**, thêm filter `topic` chỉ cho câu hỏi có filter; câu không có filter chạy không lọc. A–B chỉ khác chunking; B–C chỉ khác filter. Cùng corpus, model, metric, vector query và top-3.
- **20 câu:** 15 dev (q01–q15) / 5 test (q16–q20), chia theo tài liệu (dev dùng 9 tài liệu, test dùng 5 tài liệu khác, không trùng). Câu filter: dev q01–q03, test q16–q17. Loại câu: 4 trực tiếp, 6 diễn đạt lại, 5 điều kiện/ngoại lệ, 5 filter. Kiểm chứng evidence: `scripts/validate_benchmark.py` xác nhận từng `evidence_quote` nằm nguyên văn trong file nguồn đã chuẩn hóa, filter khớp `topic` của nguồn gold, không rò rỉ source id vào câu hỏi; <<tác giả điền: số câu và tên các nguồn bạn đã tự mở đọc lại>>. Câu hỏi được soạn có hỗ trợ AI, tác giả đối chiếu với nguồn.
- **Tiêu chí chọn chiến lược (chốt trước khi xem test, benchmark/PROTOCOL.md):** (1) Evidence Hit@3 dev cao nhất, chênh ≤1 câu coi là hòa; (2) Hit@1 dev; (3) coherence và grounding; (4) ít chunk và ingest nhanh hơn.

## Kết quả
<<Dán bảng từ results/report_tables.md sau khi chạy evaluate dev, test, audit và report. Không điền số chưa chạy.>>

| Strategy | Split | Hit@1 (n/N) | Evidence Hit@3 (n/N) | Chunk count | Thời gian | Chi phí |
|---|---|---|---|---|---|---|
| A | dev | <<>> | <<>> | 716 | <<>> | $0 |
| B | dev | <<>> | <<>> | <<>> | <<>> | $0 |
| C | dev | <<>> | <<>> | <<>> (dùng index B) | <<>> | $0 |
| A / B / C | test | <<>> | <<>> | | | $0 |

| Strategy | Coherence trung bình /2 (n) | Metadata đủ và đúng (n/N) | Filter tuân thủ (n/N hoặc N/A) | Grounding 0/1/2 (số câu) và trung bình /2 |
|---|---|---|---|---|
| A | <<>> | <<>> | <<>> | <<>> |
| B | <<>> | <<>> | <<>> | <<>> |
| C | <<>> (= B, cùng chunk) | <<>> | <<>> | <<>> |

Đường dẫn trace: `results/traces/trace_<A|B|C>_<dev|test>.jsonl`. Nhãn thủ công: `results/audit/*.csv`. Cách chọn mẫu: coherence lấy 10 đơn vị đầu theo thứ tự tên, vị trí giữa văn bản, dòng xáo thứ tự (seed 42); metadata và grounding chấm trên 5 câu test × top-3.

## Phân tích và kết luận
- **So sánh A–B và B–C; 2 ví dụ sai:** <<viết sau khi có kết quả: A–B đổi chunking thì Hit và coherence đổi thế nào; B–C chỉ so trên câu có filter (dev: q01–q03, test: q16–q17); nêu 2 câu sai có ID và nguồn gold, đọc từ trace>>
- **Chiến lược chọn, đánh đổi, điều kiện áp dụng:** <<chọn theo đúng tiêu chí đã chốt; nêu đánh đổi giữa số chunk, độ trọn ý và thời gian>>
- **Hạn chế:** Test chỉ 5 câu (2 câu filter), dev chỉ 3 câu filter và đều dùng cặp tài liệu antialiasing 2D/3D, nên chỉ mang tính minh họa, không suy rộng ngoài corpus. Nhãn thủ công do tác giả chấm (biết gold và chiến lược, có thiên lệch). Câu hỏi soạn có hỗ trợ AI. `topic` thô. Thời gian đo một lần trên CPU, model chạy `bfloat16`, nên chỉ so được tương đối. Bộ chuyển RST tự viết nên văn bản có thể khác bản HTML gốc.
- **Nếu làm lại hoặc mở rộng:** <<ví dụ: thêm hybrid BM25, dùng docutils, thêm filter mịn hơn (2D/3D), mở rộng test>>

## Công cụ AI đã dùng
Dùng Claude để giải thích, viết khung code pipeline và soạn 20 câu benchmark. Tác giả kiểm tra bằng cách chạy code, `validate_benchmark.py`, và <<điền: những gì bạn tự mở đọc/đối chiếu>>. Nhãn coherence, metadata, grounding do tác giả chấm thủ công, không dùng LLM chấm.