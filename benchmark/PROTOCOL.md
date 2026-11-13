# Giao thức đánh giá

Chốt trước khi chạy `evaluate --split test`. Commit file này trước khi xem kết quả test.

## Thời điểm chốt
- Thời điểm (UTC+7): 2026-11-13 ..:..   <- điền giờ thực tế lúc bạn lưu file
- Commit hash lúc chốt: ........        <- điền sau khi commit (git log -1 --format=%h)

## Cách chia dev/test
- Chia theo tài liệu nguồn: 15 câu dev dùng 9 tài liệu gold, 5 câu test dùng 5 tài liệu gold khác. Không tài liệu gold nào xuất hiện ở cả hai tập.
- Dev: q01-q15. Test: q16-q20.
- Bộ câu hỏi được viết và kiểm chứng evidence trước khi chạy thử pipeline. Mỗi `evidence_quote` đã được kiểm tra nằm nguyên văn trong file nguồn đã chuẩn hóa (scripts/validate_benchmark.py báo HỢP LỆ).

## Câu có filter
- Dev: q01, q02, q03 (filter topic = 2d hoặc 3d).
- Test: q16 (topic = scripting), q17 (topic = inputs).
- Giá trị filter là input giả định do người dùng hoặc ngữ cảnh cung cấp trước khi truy xuất; không lấy từ đáp án hay nguồn gold. Giá trị lấy từ tên thư mục của file nguồn (có trong manifest).
- Với câu không có filter, cấu hình C chạy không filter và ghi rõ trong trace.

## Nguy cơ rò rỉ giữa dev và test
- q01-q03 (dev, filter) cùng dùng cặp tài liệu antialiasing 2D/3D, còn các câu filter test dùng tài liệu khác, nên kết luận về filter trên dev không suy rộng được.
- q16 (test, cross_language_scripting) cùng chủ đề ngôn ngữ lập trình với q08, q09 (dev, scripting_languages).
- q18 (test) có alt_evidence: đoạn giống hệt có ở collision_shapes_2d và collision_shapes_3d, chấp nhận một trong hai.
- Các câu hỏi do tác giả soạn (có hỗ trợ AI), nên có thể mang thiên lệch về cách diễn đạt.

## Tiêu chí chọn chiến lược (chốt trước khi xem test)
Chọn theo thứ tự ưu tiên, chỉ dùng kết quả dev:
1. Evidence Hit@3 trên dev cao nhất. Nếu chênh không quá 1 câu thì coi là hòa.
2. Nếu hòa: Hit@1 trên dev cao hơn.
3. Nếu vẫn hòa: coherence và grounding (nhãn thủ công) cao hơn.
4. Nếu vẫn hòa: ít chunk hơn và thời gian ingest ngắn hơn.
- So sánh B với C chỉ dựa trên tập câu có filter (3 câu dev). Kết quả này chỉ minh họa vì mẫu rất nhỏ.

## Chấm thủ công
- Người chấm: tác giả bài làm. Nguy cơ thiên lệch: biết gold và biết chiến lược, nên có xu hướng chấm nghiêng về kết quả mong đợi.
- Giảm thiểu: dòng coherence đã xáo thứ tự (seed 42) và chấm trước khi xem số Hit; dùng cùng tiêu chí cho mọi chiến lược.
- Không dùng LLM để chấm nhãn.

## Ghi chú trung thực
- Có xem kết quả test để chỉnh bài không: chưa. (Nếu có, sửa dòng này, ghi rõ chỉnh gì và không coi test là holdout độc lập.)
- Test chỉ có 5 câu nên chỉ mang tính minh họa; không kết luận chiến lược nào tốt nhất tổng quát.