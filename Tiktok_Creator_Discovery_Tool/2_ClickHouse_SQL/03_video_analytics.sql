/* ============================================================================
 * SCRIPT 2: VIDEO ANALYTICS & DISCOVERY
 * Mục đích: Khám phá video thịnh hành, phân tích hashtag, đếm tần suất xuất hiện
 *           của thương hiệu (Brand) và các chỉ số lượng tương tác của Video.
 * ============================================================================ */

/* ----------------------------------------------------------------------------
 * 1. DATA QUALITY: KIỂM TRA VIDEO XUẤT HIỆN 2 LẦN (DUPLICATE CHECK)
 * - Đảm bảo dữ liệu crawl không bị trùng lặp dựa trên post_id_platform
 * ---------------------------------------------------------------------------- */
SELECT * FROM bee_transform.post_base
WHERE updated_at > toDateTime('2026-06-12 00:00:00')
  AND length(list_product_base_id) > 0
  AND post_id_platform IN (
    SELECT post_id_platform
    FROM bee_transform.post_base
    WHERE updated_at > toDateTime('2026-06-12 00:00:00')
      AND length(list_product_base_id) > 0
      AND post_id_platform IS NOT NULL AND post_id_platform != ''
    GROUP BY post_id_platform HAVING count() > 0
  )
ORDER BY post_id_platform, updated_at DESC;

/* ----------------------------------------------------------------------------
 * 2. PHÂN TÍCH HASHTAG THEO CATEGORY
 * - Tính toán xem trong mỗi Category, hashtag nào xuất hiện nhiều nhất
 * - Sử dụng arrayJoin() để bung mảng (unnest) hashtags
 * ---------------------------------------------------------------------------- */
WITH params AS (
    SELECT toDate('2026-06-11') AS target_day
),
base_dedup AS (
    SELECT *
    FROM (
        SELECT *, row_number() OVER (PARTITION BY post_id_platform ORDER BY updated_at DESC) AS rn
        FROM bee_transform.post_base pb 
        WHERE toDate(updated_at) = (SELECT target_day FROM params)
          AND post_id_platform IS NOT NULL AND post_id_platform != ''
    ) WHERE rn = 1
),
video_link AS (
    SELECT post_id_platform AS video_id, hashtags, list_product_base_id
    FROM base_dedup WHERE length(list_product_base_id) > 0 AND length(hashtags) > 0
),
video_cat_count AS (
    SELECT e.video_id, ifNull(c.category_name, 'Unknown') AS category_name, count() AS product_cnt
    FROM (
        SELECT video_id, arrayJoin(list_product_base_id) AS product_base_id FROM video_link
    ) e
    LEFT JOIN analytics.products p ON e.product_base_id = p.product_base_id
    LEFT JOIN mapping.backup__20260106__categories c ON toString(p.categories__id_1) = c.category_id
    GROUP BY e.video_id, category_name
),
video_dom_cat AS (
    SELECT video_id, argMax(category_name, product_cnt) AS category
    FROM video_cat_count GROUP BY video_id
)
SELECT d.category AS category, lower(arrayJoin(v.hashtags)) AS hashtag, countDistinct(v.video_id) AS count_unique_video
FROM video_link v
INNER JOIN video_dom_cat d ON v.video_id = d.video_id
GROUP BY category, hashtag ORDER BY category, count_unique_video DESC;

/* ----------------------------------------------------------------------------
 * 3. RANKING NÂNG CAO: TOP CATEGORY -> TOP BRAND -> TOP HASHTAG
 * - Tìm ra Top 5 Category nhiều views nhất
 * - Trong mỗi Category, tìm Top 10 Thương hiệu (Brand) mạnh nhất
 * - Trong mỗi Brand, tìm Top 20 Hashtag được dùng nhiều nhất
 * ---------------------------------------------------------------------------- */
WITH params AS (
    SELECT toDate('2026-06-11') AS target_day
),
base_dedup AS (
    SELECT * FROM (
        SELECT *, row_number() OVER (PARTITION BY post_id_platform ORDER BY updated_at DESC, last_time_crawled_at DESC) AS rn
        FROM bee_transform.post_base pb 
        WHERE toDate(updated_at) = (SELECT target_day FROM params)
          AND post_id_platform IS NOT NULL AND post_id_platform != ''
    ) WHERE rn = 1
),
video_link AS (
    SELECT post_id_platform AS video_id, hashtags, list_product_base_id
    FROM base_dedup WHERE length(list_product_base_id) > 0 AND length(hashtags) > 0
),
video_product_info AS (
    SELECT e.video_id, ifNull(c.category_name, 'Unknown') AS category, ifNull(nullIf(p.brand, ''), 'Unknown') AS brand
    FROM (
        SELECT video_id, arrayJoin(list_product_base_id) AS product_base_id FROM video_link
    ) e
    LEFT JOIN analytics.products p ON e.product_base_id = p.product_base_id
    LEFT JOIN mapping.backup__20260106__categories c ON toString(p.categories__id_1) = c.category_id
),
video_dom AS (
    SELECT video_id, argMax(category, cnt) AS category, argMax(brand, cnt) AS brand
    FROM (
        SELECT video_id, category, brand, count() AS cnt FROM video_product_info GROUP BY video_id, category, brand
    ) GROUP BY video_id
),
cat_brand_hashtag AS (
    SELECT d.category, d.brand, lower(arrayJoin(v.hashtags)) AS hashtag, countDistinct(v.video_id) AS count_unique_video
    FROM video_link v
    INNER JOIN video_dom d ON v.video_id = d.video_id
    GROUP BY d.category, d.brand, hashtag
),
cat_rank AS (
    SELECT category, dense_rank() OVER (ORDER BY sum(count_unique_video) DESC) AS cat_rk
    FROM cat_brand_hashtag GROUP BY category
),
brand_rank AS (
    SELECT category, brand, row_number() OVER (PARTITION BY category ORDER BY sum(count_unique_video) DESC) AS brand_rk
    FROM cat_brand_hashtag GROUP BY category, brand
),
hashtag_rank AS (
    SELECT category, brand, hashtag, count_unique_video,
           row_number() OVER (PARTITION BY category, brand ORDER BY count_unique_video DESC) AS hashtag_rk
    FROM cat_brand_hashtag
)
SELECT h.category, h.brand, h.hashtag, h.count_unique_video
FROM hashtag_rank h
INNER JOIN cat_rank cr ON h.category = cr.category
INNER JOIN brand_rank br ON h.category = br.category AND h.brand = br.brand
WHERE cr.cat_rk <= 5 AND br.brand_rk <= 10 AND h.hashtag_rk <= 20
ORDER BY cr.cat_rk, br.brand_rk, h.hashtag_rk;

/* ----------------------------------------------------------------------------
 * 4. DISCOVERY: TÌM KIẾM VIDEO THEO HASHTAG CỤ THỂ (Ví dụ: #fyp)
 * - Truy vấn các video thịnh hành nhất có chứa hashtag 'fyp'
 * ---------------------------------------------------------------------------- */
WITH base_dedup AS (
    SELECT *
    FROM (
        SELECT *, row_number() OVER (PARTITION BY video_id ORDER BY updated_at DESC) AS rn
        FROM video.video__analytics_v2
        WHERE updated_at >= now() - INTERVAL 7 DAY AND length(hashtags) > 0
    ) WHERE rn = 1
)
SELECT video_id, channel_id, channel_name, description, hashtags, viewed, liked, tiktok_url, updated_at
FROM base_dedup
WHERE arrayExists(h -> lower(h) = 'fyp', hashtags) -- Điều kiện match hashtag
ORDER BY viewed DESC;

/* ----------------------------------------------------------------------------
 * 5. DISCOVERY: TÌM KIẾM VIDEO ĐƯỢC GẮN VỚI MỘT THƯƠNG HIỆU (BRAND) CỤ THỂ
 * ---------------------------------------------------------------------------- */
WITH params AS (
    SELECT 'Unknown' AS target_brand, toDate('2026-06-11') AS target_day
),
base_dedup AS (
    SELECT * FROM (
        SELECT *, row_number() OVER (PARTITION BY post_id_platform ORDER BY updated_at DESC, last_time_crawled_at DESC) AS rn
        FROM bee_transform.post_base
        WHERE toDate(updated_at) = (SELECT target_day FROM params)
          AND post_id_platform IS NOT NULL AND post_id_platform != ''
          AND length(list_product_base_id) > 0
    ) WHERE rn = 1
),
video_brand AS (
    SELECT DISTINCT b.post_id_platform AS video_id, b.channel_id, b.channel_name, b.title, b.description, b.hashtags,
           b.view_count, b.reaction_count, b.comment_count, b.share_count, b.post_url, b.updated_at,
           ifNull(nullIf(p.brand, ''), 'Unknown') AS brand, p.product_base_id AS product_base_id
    FROM base_dedup b
    ARRAY JOIN b.list_product_base_id AS product_base_id
    INNER JOIN analytics.products p ON product_base_id = p.product_base_id
    WHERE lowerUTF8(ifNull(nullIf(p.brand, ''), '')) = lowerUTF8((SELECT target_brand FROM params))
)
SELECT video_id, any(channel_id) AS channel_id, any(channel_name) AS channel_name, any(title) AS title,
       any(description) AS description, any(hashtags) AS hashtags, any(view_count) AS view_count,
       any(reaction_count) AS reaction_count, any(comment_count) AS comment_count, any(share_count) AS share_count,
       any(post_url) AS post_url, any(updated_at) AS updated_at, any(brand) AS brand,
       groupUniqArray(product_base_id) AS product_base_ids, countDistinct(product_base_id) AS product_count
FROM video_brand
GROUP BY video_id ORDER BY view_count DESC;

/* ----------------------------------------------------------------------------
 * 6. TAGGING NÂNG CAO: PHÂN LOẠI VIDEO DỰA TRÊN TẬP HASHTAG (CATEGORY DICTIONARY)
 * - Tự động đếm số lượng hashtag khớp với bộ từ điển của từng ngành hàng
 * - Dùng arrayFilter và in để lọc các hashtag thỏa mãn
 * ---------------------------------------------------------------------------- */
WITH cat_tags AS (
    SELECT ['aosominam', 'quanshortnam', 'quansipnam', 'quantaynam', 'quanjeannam', 'sominam', 'quanaunam', 'quanlotnam', 'sipnam', 'quanduinam', 'polo', 'quansip', 'aonamdep', 'quankakinam', 'quanau', 'polonam', 'quannamdep', 'aopolonamdep', 'quandaikaki', 'boxer', 'quanaunamcaocap', 'somi', 'thoitrangnamcaocap', 'quansipam', 'quanshortkaki', 'aophongnam', 'dolotnam', 'donam', 'quanaobaoholaodong', 'aopolodep', 'sominamcaocap', 'bigsizenam', 'aokhoacnamnu', 'sipduinam', 'quanjeannamcaocap', 'donamdep', 'quanjeannamdep', 'aotangbo', 'papazi', 'quandainam', 'aothunpolo', 'jeannam', 'aothunpolonam', 'boxernam', 'quanboxer', 'reviewdonam', 'aopolocotui', 'quanshortjeannam', 'sipdui', 'quansotnam', 'aokhoacgio', 'aosomingantay', 'aothunnamdep', 'thaophan92e1q', 'aopolocaocap', 'aosominamdep', 'quansipdui', 'setdonam', 'quanauhanquoc', 'thờitrangnam', 'boquanaonam', 'dobonam', 'torano', 'dinhgiahao', 'quanjeannamongsuong', 'aopolonamcaocap', 'aophaonam', 'bodonam', 'menswear', 'aosomicaocap', 'aosominamcaocap', 'aothunnamcaocap', 'quanboxernam', 'karants', 'papago', 'aosomidaitay', 'aobalonam', 'sominamdep', 'quannamcaocap', 'sip', 'aonamcaocap', 'sweater', 'troitrangnam', 'quanaolaodong', 'vestnam', 'quânshortnam', 'duchangnguyen91', 'quandaikakinam', 'tatnam', 'quanshortkakituihopnam', 'quanlaodong', 'quanshortnamdep', 'mensfashion', 'quansipboxer', 'aokhoacjeannam', 'aosweater', 'sipboxer', 'aonamnu', 'shortkaki', 'aosominamnu', 'quangionam', 'aosominamdaitay', 'lunacy', 'pnstore1993', 'aokhoacdu', 'jeannamcaocap', 'sevenboxer', 'davuba', 'cleanfit', 'sonomen', 'thoitrangnam9595', 'aolennam', 'sandodep90', 'amanlab', 'poloshirt', 'streetwear', 'amanstore', 'aosomitrungnien', 'quanngunam', 'quanjeanquangchau', 'lienday86', 'liendongtien86', 'kitjs', 'menshopvn', 'xhtaynam', 'quanhoathinh', 'aopolonamnu', 'thenice07', 'thientrendy03', 'mrv', 'coolmate', 'quansoocnam', 'whose', 'dtshop', 'fboyluxury', 'aokhoacjean', 'godmother', 'quanbonam', 'donghomeshop', 'ngoclendo65', 'quanaonamnu', 'sauthoitrang96', 'xuhuongaokhoac', 'quanthunnam', 'hoclendonhe', 'ptmt38', 'dyminic', 'quankakiongsuong', 'ptmt💚', 'trnhphm', 'outfithe2026', 'quanshortkakituihop', 'r1997', 'boduinam', 'ptmt', 'duybuonhtmen', 'banquanao', 'katino', 'quầnlotnam', 'sontocbac', 'quangthinh352', 'aokhoacbomber', 'aothuntaylo', 'tthao1505', 'aokhoackakinam', 'suit', 'lanthoitrang6', 'insidemen', 'setnam', 'morpheus_sofy', 'ngarubydayne', 'aokhoacgionamnu', 'zonef', 'hitam', 'quansipluabang', 'julido', 'bonam', 'deptrai', 'taphoabichlai', 'bumstore', 'baohominhanh', 'shortnam', 'mkclever', 'aotangba', 'evenwear', 'moivaoshop', '🛍️✨🎀🐬🛍️', 'tamhoang_91', 'aothunnamboypho', 'setbonam', 'somihoatiet', 'aosomiformrong', 'tamtrieu', 'baohohanxi', 'aoduidaitaycaocap', 'daujulidoshop', 'k3store', 'nhuxinhdonam', 'quanshortkakinam', 'bovestnamcaocap'] AS tags
),
dedup AS (
    SELECT post_base_id, post_id_platform AS video_id, channel_base_id, channel_id, channel_name,
           description, hashtags, view_count, reaction_count, comment_count, share_count,
           post_url, created_at_platform, list_product_base_id
    FROM bee_transform.post_base
    WHERE created_at_platform >= subtractDays(now(), 90)
      AND length(hashtags) > 0
    ORDER BY updated_at DESC
    LIMIT 1 BY post_base_id
)
SELECT
    video_id,
    channel_base_id,
    channel_id,
    channel_name,
    view_count,
    reaction_count,
    comment_count,
    share_count,
    length(list_product_base_id) > 0                                              AS has_product_link,
    arrayFilter(h -> lower(h) IN (SELECT arrayJoin(tags) FROM cat_tags), hashtags) AS matched_tags,
    length(matched_tags)                                                          AS match_count,
    post_url,
    created_at_platform
FROM dedup
WHERE arrayExists(h -> lower(h) IN (SELECT arrayJoin(tags) FROM cat_tags), hashtags)
ORDER BY view_count DESC;
