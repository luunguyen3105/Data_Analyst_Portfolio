# COLUMN DICTIONARY — Shopee Live Analytics demo

File `shopee_live_analytics_demo.xlsx` (multi-sheet) được build từ các file
JSON raw trong cùng thư mục (`live_session.json`, `live_detail.json`,
`live_coordinate.json`, `traffic_source.json`, `product.json`,
`viewer_profile.json`, `buyer_profile.json`).

Tài liệu này mô tả ý nghĩa mọi cột của từng sheet để team Data/BI dùng làm
khung tham chiếu khi:
- nạp raw vào Bronze/Silver,
- vẽ dashboard,
- so sánh tương đương (parity) với schema TikTok MCN/TSP đã làm trước đó.

---

## Quy ước chung

- **Đơn vị tiền tệ**: VND. Không có currency code đi kèm trong JSON.
- **Đơn vị thời gian** trong file Shopee là **mili-giây Unix** (khác TikTok dùng giây).
  Ví dụ `startTime = 1766198025224` → `2025-12-19 14:13:45` (UTC+7).
- **Tỷ lệ** (`*Rate`, `co`, `ctr`, …) là **decimal 0..1** (vd `0.3333` = 33.33%).
  Một vài chỉ số như `viewPercentage` lại là số thập phân kiểu phần (1 = 100%).
- **`session_id`** là khoá nghiệp vụ chính của 1 phiên live, tương đương `live_id`/`room_id` ở TikTok.
- File `live_coordinate.json` không kèm `session_id`. Trong demo workbook, doc[i] được gán theo thứ tự với `live_session.json` (trùng số doc = 23) để dễ dùng. Trong production, **DE phải kèm session_id ngay lúc ingestion**, không thể dựa vào thứ tự.
- File `live_coordinate.json` có vài doc bị cắt giữa do server (xem cuối file). Parser đã repair an toàn: doc bị cắt sẽ giữ phần row hợp lệ trước điểm cắt, bỏ row truncated.

---

## 1) `live_session` (1 row / phiên live)

Nguồn: `live_session.json` (mỗi doc = 1 session).

| # | Cột | Kiểu | Mô tả |
|---|---|---|---|
| 1 | `session_id` | int64 | ID phiên live (PK). |
| 2 | `title` | str | Tiêu đề phiên live. |
| 3 | `status` | int | Trạng thái phiên. Quan sát: `2` = ended. |
| 4 | `start_time_ms` | int (ms) | Thời điểm bắt đầu, Unix milli. |
| 5 | `start_time_vn` | str | `start_time_ms` đã format `YYYY-MM-DD HH:MM:SS` UTC+7. |
| 6 | `duration_ms` | int (ms) | Thời lượng live, mili-giây. |
| 7 | `duration_hms` | str | `duration_ms` format `HH:MM:SS`. |
| 8 | `cover_image` | str | URL/path ảnh cover. |
| 9 | `viewers` | int | Tổng viewer (UV) trong phiên. |
| 10 | `views` | int (nullable) | Tổng view (PV). Trong sample chủ yếu null → bù bằng `live_detail__performance.views`. |
| 11 | `peak_views` | int (nullable) | Peak concurrent views. Trong sample null. |
| 12 | `engaged_uv` | int | Số viewer có tương tác. |
| 13 | `avg_engaged_ccu` | int | Avg concurrent users có tương tác. |
| 14 | `avg_views_duration_ms` | int (ms) | Avg watch time / viewer (mili-giây). |
| 15 | `thirty_mins_count` | int | Số viewer xem ≥ 30 phút. |
| 16 | `comments` | int | Tổng comment. |
| 17 | `likes` | int (nullable) | Tổng like — trong sample null → lấy từ `live_detail__performance.likes`. |
| 18 | `atc` | int | Tổng add-to-cart. |
| 19 | `product_clicks` | int (nullable) | Click vào product. Sample null → lấy từ `keyMetrics.productClicks`. |
| 20 | `conversion_rate` | float (nullable) | Conversion order/viewer. |
| 21 | `followers_growth` | int (nullable) | Follower mới trong phiên. |
| 22 | `paid_orders` | int (nullable) | Số đơn paid (đã thanh toán). |
| 23 | `paid_sales` | float (nullable) | GMV paid (VND). |
| 24 | `placed_orders` | int | Số đơn placed (đã đặt). |
| 25 | `placed_item_sold` | int | Số item từ đơn placed. |
| 26 | `placed_sales` | float | GMV placed (VND). |
| 27 | `confirmed_orders` | int | Đơn confirmed (đã xác nhận). |
| 28 | `confirmed_item_sold` | int | Item từ đơn confirmed. |
| 29 | `confirmed_sales` | float | GMV confirmed (VND). |

**Phân biệt 3 loại đơn**: Shopee có 3 trạng thái doanh thu khác nhau và bạn nên chọn 1 nguồn canonical cho dashboard:
- `placed_*`   → khách bấm đặt hàng (Shopee gọi “order placed”).
- `paid_*`     → khách đã thanh toán.
- `confirmed_*`→ đơn đã xác nhận (qua các bước Shopee xác thực, sau cancel/refund window).

`confirmed_*` thường là số tin cậy nhất về doanh thu thực tế.

---

## 2) `live_detail__liveInfo` (1 row / phiên)

Nguồn: `live_detail.json → data.liveInfo`. Trùng các trường meta của `live_session` nhưng theo source `live_detail` (UI dashboard chi tiết).

| # | Cột | Kiểu | Mô tả |
|---|---|---|---|
| 1 | `session_id` | int64 | PK. |
| 2 | `title` | str | Tiêu đề. |
| 3 | `status` | int | Trạng thái. |
| 4 | `start_time_ms` | int (ms) | Bắt đầu (ms). |
| 5 | `start_time_vn` | str | Bắt đầu (UTC+7). |
| 6 | `duration_ms` | int (ms) | Thời lượng (ms). |
| 7 | `duration_hms` | str | Thời lượng `HH:MM:SS`. |
| 8 | `cover_image` | str | URL cover. |

> Khi join về fact_live_session: `live_session.session_id = live_detail__liveInfo.session_id`. Nếu có lệch, `live_detail__liveInfo` thường là số canonical (nó là endpoint detail).

---

## 3) `live_detail__performance` (1 row / phiên)

Nguồn: `live_detail.json → data.performance`.

| # | Cột | Kiểu | Mô tả |
|---|---|---|---|
| 1 | `session_id` | int64 | PK. |
| 2 | `views` | int | Tổng PV. |
| 3 | `viewers` | int | Tổng UV. |
| 4 | `likes` | int | Tổng like. |
| 5 | `comments` | int | Tổng comment. |
| 6 | `shares` | int | Số share. |
| 7 | `paid_orders` | int | Đơn paid. |
| 8 | `paid_sales` | float | GMV paid. |
| 9 | `placed_orders` | int | Đơn placed. |
| 10 | `placed_sales` | float | GMV placed. |
| 11 | `item_placed_orders` | int | Số item từ đơn placed. |
| 12 | `placed_buyers` | int | Số buyer placed (UV). |
| 13 | `placed_sales_per_buyer` | float | GMV trung bình / buyer placed. |
| 14 | `confirmed_orders` | int | Đơn confirmed. |
| 15 | `confirmed_sales` | float | GMV confirmed. |
| 16 | `item_confirmed_orders` | int | Item từ đơn confirmed. |
| 17 | `confirmed_buyers` | int | Buyer confirmed (UV). |
| 18 | `confirmed_sales_per_buyer` | float | GMV / buyer confirmed. |
| 19 | `comment_rate` | float | Tỷ lệ comment / view (decimal 0..1). |

---

## 4) `live_detail__promotion` (1 row / phiên)

Nguồn: `live_detail.json → data.promotion`. KPI khuyến mãi/tương tác.

| # | Cột | Kiểu | Mô tả |
|---|---|---|---|
| 1 | `session_id` | int64 | PK. |
| 2 | `coins_round` | int | Số vòng tặng xu (Shopee Coins). |
| 3 | `coins_claimed` | int | Số xu đã được claim. |
| 4 | `time_claimed` | int | Số lần claim. |
| 5 | `auction_round` | int | Số vòng đấu giá / flash deal. |
| 6 | `user_claimed` | int | Số user khác nhau đã claim. |
| 7 | `streaming_price_skus` | int | Số SKU có giá flash trong phiên (count `streamingPriceSets`). |

---

## 5) `live_detail__promo_skus` (N rows / phiên)

Nguồn: `live_detail.json → data.promotion.streamingPriceSets[*]`. Mỗi row = 1 item SKU được thiết lập giá streaming/flash.

| # | Cột | Kiểu | Mô tả |
|---|---|---|---|
| 1 | `session_id` | int64 | FK về phiên live. |
| 2 | `item_id` | int64 | ID SKU/sản phẩm áp dụng giá streaming. Join sang sheet `product`. |

---

## 6) `live_detail__keyMetrics` (1 row / phiên)

Nguồn: `live_detail.json → data.keyMetrics`. Đây là tab "Key Metrics" trên UI Shopee Live, gom KPI hiệu suất dạng tỉ lệ.

| # | Cột | Kiểu | Mô tả |
|---|---|---|---|
| 1 | `session_id` | int64 | PK. |
| 2 | `live_cover_clicks_rate` | float | Tỷ lệ click cover live (decimal 0..1). |
| 3 | `ctr` | float | CTR tổng (live cover/feed → vào phòng). |
| 4 | `avg_view_duration_ms` | int (ms) | Avg watch time. |
| 5 | `peak_viewers` | int | Concurrent viewer cao nhất. |
| 6 | `engaged_viewers` | int | Số viewer có tương tác. |
| 7 | `followers_growth` | int | Follower mới. |
| 8 | `product_imp` | int (nullable) | Tổng impression sản phẩm. Sample đa số null. |
| 9 | `product_clicks` | int | Tổng click vào sản phẩm. |
| 10 | `product_click_uv` | int (nullable) | UV click sản phẩm. Sample đa số null. |
| 11 | `product_click_rate` | float | Tỷ lệ click sản phẩm. |
| 12 | `atc` | int | Add-to-cart. |
| 13 | `conversion_rate` | float | Conversion order / viewer. |
| 14 | `sales_per_buyer` | float (nullable) | Sample null. |
| 15 | `sales_per_order` | float | AOV. |
| 16 | `placed_gpm` | float | GMV per ngàn impression — placed (Shopee GPM). |
| 17 | `confirmed_gpm` | float | GPM confirmed. |
| 18 | `placed_cor` | float | Click → order rate (placed). |
| 19 | `confirmed_cor` | float | Click → order rate (confirmed). |
| 20 | `placed_abs` | int | Avg basket size — placed. |
| 21 | `confirmed_abs` | int | Avg basket size — confirmed. |
| 22 | `placed_imp_order_rate` | int | Impression → order rate placed. |
| 23 | `confirmed_imp_order_rate` | int | Impression → order rate confirmed. |

> `placedGPM/confirmedGPM` là GMV per impression × 1000 (parity với "Show GPM" của TikTok). Khi BI làm dashboard, chọn **một** trong (placed | confirmed) để vẽ và stick với nó.

---

## 7) `live_coordinate__minute` (M rows / phiên — bucket theo phút)

Nguồn: `live_coordinate.json`. Mỗi doc trả về list `data[]` các bucket 60 giây (đo bằng diff `time` liên tiếp = 60_000 ms). Tương đương `fact_live_trend_5m` của TikTok nhưng granularity = 1 phút và **phẳng theo metric** (không có `stats_type`).

| # | Cột | Kiểu | Mô tả |
|---|---|---|---|
| 1 | `session_id` | int64 | FK — gán theo thứ tự docs với `live_session`. |
| 2 | `bucket_time_ms` | int (ms) | Mốc thời gian đầu bucket 1 phút. |
| 3 | `bucket_time_vn` | str | Format UTC+7. |
| 4 | `views` | int | View phát sinh trong phút. |
| 5 | `viewers` | int | UV phát sinh trong phút. |
| 6 | `likes` | int | Like trong phút. |
| 7 | `comment` | int | Comment trong phút (lưu ý số ít: `comment`, không phải `comments`). |
| 8 | `atc` | int | Add-to-cart trong phút. |
| 9 | `ccu` | int | Concurrent user (snapshot tại bucket). |
| 10 | `engaged_ccu` | int | Concurrent user có tương tác. |
| 11 | `placed_orders` | int | Đơn placed trong phút. |
| 12 | `placed_sales` | float | GMV placed trong phút. |
| 13 | `confirmed_orders` | int | Đơn confirmed trong phút. |
| 14 | `confirmed_sales` | float | GMV confirmed trong phút. |

> **Lưu ý ingestion**: `live_coordinate.json` raw không có `session_id` ở mỗi doc. Production cần đảm bảo metadata kèm theo file (ví dụ tên file `<session_id>.json` hoặc field bao ngoài) để gán FK chuẩn.

---

## 8) `traffic_source` (S rows / phiên)

Nguồn: `traffic_source.json → data[*]`. Liệt kê nguồn traffic vào live theo `sourceId`.

| # | Cột | Kiểu | Mô tả |
|---|---|---|---|
| 1 | `session_id` | int64 | FK. |
| 2 | `source_id` | int | Mã nguồn traffic Shopee gán nội bộ. Quan sát: `1..9` + `99`. |
| 3 | `source_label` | str | Nhãn suy luận (xem bảng dưới). |
| 4 | `label_confidence` | str | `HIGH/MEDIUM/LOW` — mức độ chắc chắn của mapping. |
| 5 | `view` | int | Số view tới từ nguồn đó. |
| 6 | `view_percentage` | float | Tỷ lệ % view của nguồn (giá trị 0..1, tổng = 1.0). |

### Mapping `source_id` (suy luận, **CHƯA chính thức**)

| `source_id` | `source_label` (suy luận) | Confidence |
|---|---|---|
| 1 | Live tab / Live feed | MEDIUM |
| 2 | Search | MEDIUM |
| 3 | Recommendation / For You | MEDIUM |
| 4 | Shop profile | MEDIUM |
| 5 | Following / Subscribe | MEDIUM |
| 6 | Notifications / Push | LOW |
| 7 | Share / Deeplink | LOW |
| 8 | Category / Mall | LOW |
| 9 | Affiliate / Voucher | LOW |
| 99 | Others / Unknown | HIGH |

> Sample cho thấy mọi phiên trong file đều dồn ~100% vào `source_id = 99` (Others), các source 1..9 đều = 0 → có thể tài khoản này không có traffic phân loại được, hoặc API trong giai đoạn này chưa map. Mapping cần được verify lại bằng cách so với UI Shopee Live Analytics tab "Traffic source" (label hiển thị bằng tiếng Việt/Anh).

---

## 9) `product` (P rows — toàn bộ sản phẩm xuất hiện)

Nguồn: `product.json` (mỗi doc = 1 sản phẩm). File này là **flat list product**, có thể chứa product của nhiều phiên live (không có FK `session_id` trực tiếp). Tham chiếu sản phẩm về phiên thông qua `live_detail__promo_skus.item_id` hoặc các API attribution khác.

| # | Cột | Kiểu | Mô tả |
|---|---|---|---|
| 1 | `item_id` | str | ID sản phẩm (Shopee). |
| 2 | `shop_id` | int64 | ID shop. |
| 3 | `title` | str | Tên sản phẩm. |
| 4 | `cover_image` | str | Path ảnh sản phẩm. |
| 5 | `min_price` | float | Giá thấp nhất (VND). |
| 6 | `max_price` | float | Giá cao nhất (VND). |
| 7 | `viewers` | int | UV xem sản phẩm. |
| 8 | `clicks` | int | Click sản phẩm. |
| 9 | `click_rate` | float | Tỷ lệ click (decimal 0..1). |
| 10 | `atc` | int | Add-to-cart. |
| 11 | `paid_orders` | int (nullable) | Đơn paid. |
| 12 | `paid_sales` | float (nullable) | GMV paid. |
| 13 | `placed_orders` | int | Đơn placed. |
| 14 | `placed_item_sold` | int | Item từ đơn placed. |
| 15 | `placed_sales` | float | GMV placed (VND). |
| 16 | `placed_co_rate` | float | Click → order rate placed. |
| 17 | `confirmed_orders` | int | Đơn confirmed. |
| 18 | `confirmed_item_sold` | int | Item từ đơn confirmed. |
| 19 | `confirmed_sales` | float | GMV confirmed. |
| 20 | `confirmed_co_rate` | float | Click → order rate confirmed. |
| 21 | `conversion_rate` | float | Conversion sản phẩm. |
| 22 | `affiliate_orders` | int (nullable) | Đơn từ affiliate. |
| 23 | `affiliate_item_sold` | int (nullable) | Item từ affiliate. |
| 24 | `affiliate_sales` | float (nullable) | GMV affiliate. |
| 25 | `grass_date` | int (nullable) | Cờ ngày data Shopee, đa số null. |

> **Quan trọng**: file `product.json` không gắn `session_id` cho từng row. Để build `fact_live_product` (per session × product), DE phải:
> 1. Hoặc gọi API có `session_id + item_id` đi kèm.
> 2. Hoặc dùng `live_detail.promotion.streamingPriceSets[*]` để biết phiên nào có item nào, rồi join.

---

## 10) `viewer_profile` (V rows / phiên × dimension)

Nguồn: `viewer_profile.json → data[*]`. Mỗi doc cho 1 phiên trả về list 4 dimension: `identity / gender / age / region` (region không có trong sample đầu, tuỳ tài khoản).

| # | Cột | Kiểu | Mô tả |
|---|---|---|---|
| 1 | `session_id` | int64 | FK — gán theo thứ tự docs với `live_session`. |
| 2 | `kind` | str | Cố định = `viewer`. |
| 3 | `dimension` | str | Tên nhóm: `identity` (follower/non), `gender` (Male/Female/unknown), `age` (`18-24`, `25-34`, `35-44`, `45-54`, `>=55`), … |
| 4 | `item_name` | str | Bucket trong dimension (vd `Male`, `25-34`, `follower`). |
| 5 | `value` | int | Số viewer thuộc bucket. |

> Tương đương `fact_live_portrait` của TikTok nhưng dùng tên dimension/itemName **bằng tiếng Anh đầy đủ** thay vì mã số. Không cần dim mapping code → label.

---

## 11) `buyer_profile` (V rows / phiên × dimension)

Nguồn: `buyer_profile.json → data[*]`. Cấu trúc giống `viewer_profile` nhưng tính trên **buyer** (người đã đặt/đã mua) thay vì viewer.

| # | Cột | Kiểu | Mô tả |
|---|---|---|---|
| 1 | `session_id` | int64 | FK. |
| 2 | `kind` | str | Cố định = `buyer`. |
| 3 | `dimension` | str | `identity / gender / age / region`. |
| 4 | `item_name` | str | Bucket. |
| 5 | `value` | int | Số buyer thuộc bucket. |

> Phần lớn live trong sample có `buyer_profile` toàn 0 vì chưa có đơn → file vẫn trả về structure đầy đủ với value=0. Chỉ một vài phiên (vd có đơn placed) thì mới có distribution thật.

---

## So sánh nhanh với schema TikTok MCN/TSP

| Concept | TikTok MCN/TSP | Shopee Live |
|---|---|---|
| ID phiên live | `live_id` / `room_id` (snowflake string) | `sessionId` (int64) |
| Đơn vị thời gian | unix **seconds** | unix **milliseconds** |
| KPI tổng phiên | `common_stats` + `core_stats` | `live_session` + `live_detail.performance` + `live_detail.keyMetrics` |
| Trend theo thời gian | `response_trend_chart` (granularity 1/5/15 min, hierarchical `stats_type`) | `live_coordinate` (granularity = 1 min, phẳng theo metric) |
| Traffic source | `response_traffic_source` (cluster main/detail; hierarchy `stats_type` 500..560) | `traffic_source` (flat `sourceId` 1..9 + 99) |
| Sản phẩm theo live | `response_product_stats` per live | `product.json` flat + `live_detail.promotion.streamingPriceSets` để liên kết |
| Audience portrait | `age_gender_portrait` (5 dimension, code-based) | `viewer_profile` + `buyer_profile` (label-based) |
| Trạng thái doanh thu | `direct_gmv` (tổng) + `paid_sku_order_cnt` | tách 3: `placed / paid / confirmed` |
| Tiền tệ | có currency_code (`VND/USD`) | mặc định VND, không kèm currency_code |

---

## Lưu ý chất lượng dữ liệu

1. **`live_coordinate.json` bị cắt giữa**: file gốc có chỗ doc trước bị truncate (ví dụ `..., "viewers"{"code":...`). Parser đã repair: doc lỗi giữ phần data hợp lệ tới row gần nhất, các row truncated bị bỏ. Khi production hoá, DE cần fix ở pipeline ingestion để mỗi doc luôn full.
2. **Thiếu `session_id` ở `live_coordinate`, `traffic_source`, `*_profile`**: hiện gán theo thứ tự docs (giả định cùng creator, cùng cursor crawler). DE cần đảm bảo `session_id` được gắn vào từng request/payload.
3. **Một số field null khi 0** (`paid_orders`, `paid_sales`, `productImp`, `productClickUv`): Shopee API trả `null` thay vì `0` khi chưa có dữ liệu. BI dùng `COALESCE(field, 0)` khi tính sum/avg.
4. **3 KPI doanh thu** (`placed/paid/confirmed`) **không nên cộng cùng nhau**. Chọn 1 nguồn canonical (`confirmed_*` thường tin cậy nhất) và document rõ trong dashboard.
5. **Mapping `source_id` trong `traffic_source`** chỉ là suy luận — verify với UI thật trước khi đẩy vào báo cáo cho stakeholder.
