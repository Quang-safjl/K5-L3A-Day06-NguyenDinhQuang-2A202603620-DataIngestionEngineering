# Báo cáo cá nhân — Day 6

Họ tên: Nguyễn Đình Quang · MSSV: 2A202603620

## Dữ liệu và pipeline
- **Chủ đề, nguồn/quyền, số trang và quy tắc tính trang:** Hướng dẫn sản phẩm: tài liệu Godot Engine (repo `godotengine/godot-docs`, file `.rst`, commit `c5b3485cb4`). Giấy phép CC BY 3.0, ghi công "Juan Linietsky, Ariel Manzur and the Godot community" (data/ATTRIBUTION.md); không dùng thư mục `classes/` (MIT). Lấy dữ liệu bằng clone từng phần (`--filter=blob:none --sparse`) chỉ gồm file `.rst` của 6 thư mục. Corpus gồm **36 đơn vị nguồn, 317.150 ký tự**, 6 file mỗi topic (2d, 3d, physics, scripting, inputs, step_by_step). Quy tắc tính: file `.rst` không phân trang nên 1 file hợp lệ = 1 đơn vị độc lập (page = source_id), ≥1.500 ký tự sau chuẩn hóa. Chọn theo quy tắc xác định: trong mỗi thư mục sắp xếp theo đường dẫn, lấy tối đa 6 file đầu tiên hợp lệ; loại `index.rst` và file bắt đầu bằng `_`. Không nhân bản dữ liệu. Ngày lấy: 2026-11-13. File bị loại và lý do: results/corpus_log.csv (41 file vượt giới hạn 6 file mỗi thư mục, 6 file index, 1 file quá ngắn).
- **Chuẩn hóa, lỗi và giới hạn:** Unicode NFC, thống nhất xuống dòng và khoảng trắng; bỏ directive (toctree, image, comment, anchor), đổi role `:ref:` thành văn bản, đổi heading RST thành `#`; giữ đoạn văn, code, admonition (Note:, Warning:) và bảng đơn giản. Bộ chuyển dùng regex tự viết, không dùng docutils. Giới hạn: một số câu chứa liên kết bị rút ngắn (ví dụ "This is covered on the"), tên lớp còn dạng `class_Xxx`, bảng bị đơn giản hóa, code mất nhãn ngôn ngữ. Evidence kiểm chứng trên chính văn bản đã chuẩn hóa này.
- **Embedding, vector store, lệnh chạy, chi phí:** `google/embeddinggemma-2`, chạy local qua sentence-transformers 6.3.0 (torch 2.15.0, transformers 5.22.2, Python 3.13.2, Windows 11), CPU, tải ở dạng `bfloat16`, **768 chiều**, chuẩn hóa L2, không cắt MRL. Prompt lấy từ `model.prompts`: query `task: search result | query: `, document `title: none | text: `. Vector store: Chroma 1.5.9 `PersistentClient` (data/chroma), metric **cosine**, HNSW (tìm kiếm xấp xỉ), 2 collection `godot_A`, `godot_B`. Lệnh: `python -m src.run info | ingest | evaluate --split dev|test | audit | report` (README.md). Chi phí: **$0** (local).
- **Metadata và trường lọc:** Bắt buộc: `document_id`, `source` (đường dẫn file gốc), `page` (= source_id vì không phân trang). Bổ sung: `category` (thư mục cấp 1), **`topic` (thư mục cấp 2, trường lọc)**, `section` (heading gần nhất), `section_path`, `char_start/char_end`, `content_hash`, `chunk_index`. Giá trị `category` và `topic` lấy từ đường dẫn thư mục, kiểm chứng được qua manifest, không đoán. Chọn `topic` làm filter vì có 6 giá trị phân biệt được và nhiều tài liệu 2D/3D có nội dung song song. Hạn chế: `topic` thô (topic `physics` gồm cả 2D lẫn 3D), `category` gần như hằng số (30 file `tutorials`, 6 file `getting_started`).

## Cấu hình và benchmark
- **A / B / C:** A: chunk cố định 500 ký tự, overlap 50, không lọc. B: chia theo heading rồi gom đoạn tối đa 1.200 ký tự (section thân <150 ký tự gộp sang section sau), không lọc. C: dùng **chính index của B**, thêm filter `topic` chỉ cho câu hỏi có filter; câu không có filter chạy không lọc. A–B chỉ khác chunking; B–C chỉ khác filter. Cùng corpus, model, metric, vector query và top-3.
- **20 câu:** 15 dev (q01–q15) / 5 test (q16–q20), chia theo tài liệu (dev dùng 9 tài liệu, test dùng 5 tài liệu khác, không trùng). Câu filter: dev q01–q03, test q16–q17. Loại câu: 4 trực tiếp, 6 diễn đạt lại, 5 điều kiện/ngoại lệ, 5 filter. Kiểm chứng evidence: `scripts/validate_benchmark.py` xác nhận từng `evidence_quote` nằm nguyên văn trong file nguồn đã chuẩn hóa, filter khớp `topic` của nguồn gold, không rò rỉ source id vào câu hỏi; tác giả đã tự mở đọc lại <<số câu>> câu, gồm các nguồn <<tên các nguồn đã mở>>. Câu hỏi được soạn có hỗ trợ AI, tác giả đối chiếu với nguồn.
- **Tiêu chí chọn chiến lược (chốt trước khi xem test, benchmark/PROTOCOL.md, commit `da566f1`):** (1) Evidence Hit@3 dev cao nhất, chênh ≤1 câu coi là hòa; (2) Hit@1 dev; (3) coherence và grounding; (4) ít chunk và ingest nhanh hơn.

## Kết quả

| Strategy | Split | Hit@1 (n/N) | Evidence Hit@3 (n/N) | Chunk count | Thời gian | Chi phí |
|---|---|---|---|---|---|---|
| A | dev | 8/15 | 9/15 | 716 | 1603,3 s | $0 |
| B | dev | 11/15 | 13/15 | 431 | 1541,8 s | $0 |
| C | dev | 11/15 | 14/15 | 431 (dùng index B) | 0 s thêm (dùng lại index B) | $0 |
| A | test | 4/5 | 4/5 | 716 | | $0 |
| B | test | 5/5 | 5/5 | 431 | | $0 |
| C | test | 5/5 | 5/5 | 431 (dùng index B) | | $0 |

Source@3: dev A 14/15, B 14/15, C 15/15; test cả ba 5/5. Riêng các câu có filter: dev (q01–q03) A 2/3 Hit@1 và 2/3 Evidence Hit@3, B 2/3 và 2/3, C 2/3 và 3/3; test (q16–q17) A 1/2 và 1/2, B 2/2 và 2/2, C 2/2 và 2/2. Thời gian là thời gian embed và lưu một lần trên CPU (nguồn: `results/ingest_log.jsonl`).

| Strategy | Coherence trung bình /2 (n) | Metadata đủ và đúng (n/N) | Filter tuân thủ (n/N hoặc N/A) | Grounding 0/1/2 (số câu) và trung bình /2 |
|---|---|---|---|---|
| A | <<từ coherence_labels.csv>> | <<từ metadata_audit.csv>> | N/A | <<từ grounding_labels.csv>> |
| B | <<>> | <<>> | N/A | <<>> |
| C | <<>> (= B, cùng chunk) | <<>> | <<>> | <<>> |

Đường dẫn trace: `results/traces/trace_<A|B|C>_<dev|test>.jsonl`. Nhãn thủ công: `results/audit/*.csv`. Cách chọn mẫu: coherence lấy 10 đơn vị đầu theo thứ tự tên, vị trí giữa văn bản, dòng xáo thứ tự (seed 42); metadata và grounding chấm trên 5 câu test × top-3.

## Phân tích và kết luận
- **So sánh A–B và B–C; 2 ví dụ sai:** Trên dev, đổi từ A sang B (cố định 500 ký tự sang chia theo heading) tăng Hit@1 từ 8/15 lên 11/15 và Evidence Hit@3 từ 9/15 lên 13/15, đồng thời giảm số chunk từ 716 xuống 431. Trên test, B đúng cả 5 câu còn A đúng 4/5 (A trượt q17). Source@3 của A và B đều cao (dev 14/15, test 5/5), nên phần chênh nằm ở việc chunk có chứa bằng chứng hay không, không phải ở việc tìm đúng tài liệu. Trace dev của A đánh dấu nghi ngờ evidence bị cắt ở q07, q08, q13, q14, q15 (5 trong 6 câu A trượt). Phần coherence chấm tay kiểm tra giả thuyết này: <<điền kết quả coherence A so với B>>. B–C chỉ khác nhau ở câu có filter: trên dev, Evidence Hit@3 của 3 câu filter tăng từ 2/3 lên 3/3 (C sửa q01) nhưng Hit@1 vẫn 2/3; trên test, B và C giống nhau (2/2) nên filter không thêm lợi ích. Với 3 và 2 câu, kết quả chỉ mang tính minh họa.
  - **Ví dụ sai 1 – q01 (dev)** ("Which renderers support multisample antialiasing (MSAA)?", gold `tutorials--2d--2d_antialiasing`). A và B trả top-3 toàn chunk của `3d_antialiasing` (source@3 = 0), vì trang 3D cũng có mục MSAA và điểm tương đồng cao (0,86 với A, 0,845 với B). C áp filter `topic=2d` nên top-3 đều thuộc `2d_antialiasing`, chunk có bằng chứng đứng ở rank 2 (Hit@1 vẫn sai). Filter sửa lỗi nhầm tài liệu nhưng không sửa thứ hạng trong tài liệu.
  - **Ví dụ sai 2 – q14 (dev)** ("Can I count on a physics simulation giving identical results when the same situation is repeated?", gold `tutorials--physics--physics_introduction`). Cả A, B và C đều trượt Evidence Hit@3. Ở A, đoạn bằng chứng bắt đầu ở `A-tutorials--physics--physics_introduction-002` nhưng bị cắt ở 500 ký tự, và top-3 không chứa chunk có đủ bằng chứng. Ở B/C, bằng chứng nằm trọn trong chunk mở đầu `B-tutorials--physics--physics_introduction-000` (khoảng 1.160 ký tự), nhưng chunk này không vào top-3; top-3 là các chunk về `_physics_process` và `move_and_collide`. Nguyên nhân có thể là câu hỏi diễn đạt lại, không chứa từ "deterministic", và đoạn cảnh báo chỉ chiếm một phần nhỏ của chunk dài. Cờ evidence-split của B/C ở q14 không có nghĩa bằng chứng bị cắt, mà là nguồn đúng được truy xuất nhưng chunk có bằng chứng không nằm trong top-3.
  - | A | <<từ coherence_labels.csv>> | <<từ metadata_audit.csv>> | N/A (không áp filter) | <<từ grounding_labels.csv>> |
| B | <<>> | <<>> | N/A (không áp filter) | <<>> |
| C | <<>> (= B, cùng chunk) | <<>> | 2/2 (q16, q17 trên test) | <<>> |

Khi không áp filter, trace test ghi top-3 của B lệch topic ở cả hai câu filter: q16 rank 3 là `scripting_first_script` (topic `step_by_step`) và q17 rank 2, 3 thuộc topic `scripting`; top-3 của C cùng cả hai câu đều đúng topic. Hit không đổi vì chunk có bằng chứng đã đứng ở rank 1, nhưng filter loại được nhiễu ngoài chủ đề.
- **Chiến lược chọn, đánh đổi, điều kiện áp dụng:** Chọn chỉ dựa trên dev theo tiêu chí đã chốt, không dựa vào test. B hơn A rõ (Evidence Hit@3 dev chênh 4 câu, vượt ngưỡng hòa ≤1) và ít chunk hơn, ingest nhanh hơn. B và C chênh 1 câu (13 và 14) nên hòa ở tiêu chí 1; Hit@1 dev bằng nhau (11/15), nên quyết định nằm ở coherence và grounding. <<điền chiến lược chọn cuối cùng sau khi có bảng audit; vì C dùng chunk của B nên coherence bằng nhau, chỉ grounding có thể khác>>. Đánh đổi: B cho ít chunk và chunk trọn ý hơn nhưng chunk dài (trung vị 755 ký tự, tối đa 1.236) có thể làm loãng embedding, như ở q14; C chỉ dùng được khi câu hỏi hoặc giao diện cung cấp sẵn `topic`.
- **Tác động của chiến lược dữ liệu:** Thay đổi chunking (A sang B) làm thay đổi kết quả nhiều hơn thay đổi filter (B sang C): chunking tăng Evidence Hit@3 dev 4 câu, trong khi filter chỉ sửa 1 câu dev (q01) và không đổi gì ở test. Filter hữu ích nhất khi hai tài liệu cùng nội dung ở các topic khác nhau (antialiasing 2D và 3D). <<thêm nhận xét từ metadata_audit.csv: metadata nào đủ và đúng, trường nào lỗi>>.
- **Hạn chế:** Test chỉ 5 câu (2 câu filter), dev chỉ 3 câu filter và đều dùng cặp tài liệu antialiasing 2D/3D, nên chỉ mang tính minh họa, không suy rộng ngoài corpus. Corpus chỉ gồm 36 trong 86 file `.rst` của các thư mục đã lấy (giới hạn 6 file mỗi thư mục). Nhãn thủ công do tác giả chấm (biết gold và chiến lược, có thiên lệch). Câu hỏi soạn có hỗ trợ AI. `topic` thô. Thời gian đo một lần trên CPU, model chạy `bfloat16`, nên chỉ so được tương đối và điểm có thể khác nhẹ so với float32. Bộ chuyển RST tự viết nên văn bản có thể khác bản HTML gốc. Kết quả dev được xem trước khi chốt giao thức; test chỉ chạy một lần sau khi commit `da566f1`.
- **Nếu làm lại hoặc mở rộng:** Thêm hybrid BM25 để bắt các từ khóa như "deterministic", dùng docutils thay bộ chuyển regex, tách filter 2D/3D mịn hơn (`topic` hiện gộp 2D và 3D trong `physics`), chia nhỏ chunk mở đầu quá dài, và mở rộng bộ test vượt 5 câu.


## Công cụ AI đã dùng
Dùng Claude để giải thích, viết khung code pipeline . 