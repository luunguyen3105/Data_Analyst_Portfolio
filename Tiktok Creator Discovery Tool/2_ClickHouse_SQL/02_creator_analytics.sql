/* ============================================================================
 * SCRIPT 1: CREATOR ANALYTICS & SCORING
 * Mục đích: Đánh giá hiệu suất của Creator, phân loại (Tier), tìm ngách (Niche),
 *           và xếp hạng (Percentile) dựa trên lịch sử video.
 * ============================================================================ */

/* ----------------------------------------------------------------------------
 * 1. TỔNG HỢP CHỈ SỐ CREATOR (CREATOR AGGREGATION)
 * - Thống kê tổng lượt xem, tổng video, video có gắn link sản phẩm
 * - Tìm ra Category (ngách) mang lại nhiều views nhất cho Creator
 * ---------------------------------------------------------------------------- */
WITH params AS (
    SELECT toDate('2026-06-11') AS target_day
),
-- Lấy bản ghi mới nhất theo từng video_id trong ngày target
base_dedup AS (
    SELECT *
    FROM (
        SELECT *,
               row_number() OVER (
                   PARTITION BY post_id_platform
                   ORDER BY updated_at DESC, last_time_crawled_at DESC
               ) AS rn
        FROM bee_transform.post_base
        WHERE toDate(updated_at) = (SELECT target_day FROM params)
          AND channel_id IS NOT NULL AND channel_id != ''
          AND post_id_platform IS NOT NULL AND post_id_platform != ''
    )
    WHERE rn = 1
),
all_posts AS (
    SELECT channel_id, channel_name, post_id_platform AS video_id, toUInt64(ifNull(view_count, 0)) AS view_count
    FROM base_dedup
),
latest_posts AS (
    SELECT channel_id, channel_name, post_id_platform AS video_id, toUInt64(ifNull(view_count, 0)) AS view_count, list_product_base_id
    FROM base_dedup
    WHERE length(list_product_base_id) > 0
),
video_base AS (
    SELECT channel_id, any(channel_name) AS channel_name, video_id, max(view_count) AS view_count
    FROM latest_posts
    GROUP BY channel_id, video_id
),
creator_video_stats AS (
    SELECT a.channel_id AS cvs_channel_id, any(a.channel_name) AS cvs_channel_name,
           countDistinct(a.video_id) AS total_video, countDistinct(l.video_id) AS video_with_link
    FROM all_posts a
    LEFT JOIN latest_posts l ON a.channel_id = l.channel_id AND a.video_id = l.video_id
    GROUP BY a.channel_id
),
creator_all_view AS (
    SELECT channel_id AS cav_channel_id, sum(view_count) AS total_view_all_video
    FROM all_posts GROUP BY channel_id
),
creator_aff_view AS (
    SELECT channel_id AS cafv_channel_id, sum(view_count) AS total_view_video_aff
    FROM video_base GROUP BY channel_id
),
creator_category_view AS (
    SELECT vb.channel_id AS ccv_channel_id, ifNull(c.category_name, 'Unknown') AS category_name,
           sum(vb.view_count / lp.product_count) AS category_total_view
    FROM video_base vb
    INNER JOIN (
        SELECT channel_id, video_id, arrayJoin(list_product_base_id) AS product_base_id, length(list_product_base_id) AS product_count
        FROM latest_posts
    ) lp ON vb.channel_id = lp.channel_id AND vb.video_id = lp.video_id
    LEFT JOIN analytics.products p ON lp.product_base_id = p.product_base_id
    LEFT JOIN mapping.backup__20260106__categories c ON toString(p.categories__id_1) = c.category_id
    GROUP BY vb.channel_id, category_name
),
category_rank_arr AS (
    SELECT ccv_channel_id AS cr_channel_id,
           arraySort(x -> (-x.2, x.1), groupArray((category_name, category_total_view))) AS cat_arr
    FROM creator_category_view GROUP BY ccv_channel_id
)
SELECT cvs.cvs_channel_name AS channel_name, cvs.cvs_channel_id AS channel_id, cvs.total_video, cvs.video_with_link,
       cav.total_view_all_video, cafv.total_view_video_aff,
       if(length(cr.cat_arr) >= 1, tupleElement(cr.cat_arr[1], 1), NULL) AS top_1_category,
       if(length(cr.cat_arr) >= 1, tupleElement(cr.cat_arr[1], 2), 0)    AS top_1_category_total_view,
       round(if(length(cr.cat_arr) >= 1, tupleElement(cr.cat_arr[1], 2), 0) * 100.0 / nullIf(cafv.total_view_video_aff, 0), 2) AS top_1_category_pct,
       if(length(cr.cat_arr) >= 2, tupleElement(cr.cat_arr[2], 1), NULL) AS top_2_category,
       if(length(cr.cat_arr) >= 2, tupleElement(cr.cat_arr[2], 2), 0)    AS top_2_category_total_view
FROM creator_video_stats cvs
LEFT JOIN creator_all_view cav ON cvs.cvs_channel_id = cav.cav_channel_id
LEFT JOIN creator_aff_view cafv ON cvs.cvs_channel_id = cafv.cafv_channel_id
LEFT JOIN category_rank_arr cr ON cvs.cvs_channel_id = cr.cr_channel_id
ORDER BY cafv.total_view_video_aff DESC, cav.total_view_all_video DESC;

/* ----------------------------------------------------------------------------
 * 2. ĐẾM SỐ LƯỢNG CREATOR ACTIVE (VN, Follower > 1000)
 * ---------------------------------------------------------------------------- */
SELECT countDistinct(pb.channel_base_id) as total_channel
FROM (
    SELECT post_base_id, channel_base_id FROM bee_transform.post_base
    WHERE created_at_platform >= toDateTime('2026-03-01 00:00:00')
    ORDER BY updated_at DESC LIMIT 1 BY post_base_id
) AS pb
INNER JOIN (
    SELECT channel_base_id
    FROM (
        SELECT channel_base_id, country FROM bee_transform.channel_base
        WHERE follower_count > 1000
        ORDER BY updated_at DESC LIMIT 1 BY channel_base_id
    )
    WHERE lowerUTF8(country) = 'vn'
) AS cb ON pb.channel_base_id = cb.channel_base_id;

/* ----------------------------------------------------------------------------
 * 3. PHÂN LOẠI CREATOR TIER (Dựa trên Follower)
 * ---------------------------------------------------------------------------- */
SELECT
    multiIf(follower_count < 10000, '1K-10K',
            follower_count < 100000, '10K-100K',
            follower_count < 1000000, '100K-1M', '1M+') AS tier,
    countDistinct(channel_base_id) AS creators
FROM (
    SELECT channel_base_id, follower_count, country FROM bee_transform.channel_base
    WHERE follower_count > 1000 ORDER BY updated_at DESC LIMIT 1 BY channel_base_id
)
WHERE lowerUTF8(country) = 'vn'
  AND channel_base_id IN (
      SELECT channel_base_id FROM bee_transform.post_base
      WHERE created_at_platform >= toDateTime('2026-03-01 00:00:00')
  )
GROUP BY tier ORDER BY creators DESC;

/* ----------------------------------------------------------------------------
 * 4. TÍNH TOÁN ENGAGEMENT RATE & PERCENTILE (120 Days / 90 Days)
 * - Sử dụng Median để loại bỏ Outlier
 * - Tính Percentile xếp hạng (Ranking) để tìm ra Top Creator trong mỗi Tier/Niche
 * ---------------------------------------------------------------------------- */
WITH
allowed_niche AS (
    SELECT arrayJoin([
        'Chăm sóc sắc đẹp & Chăm sóc cá nhân', 'Trang phục nữ & Đồ lót', 'Trang phục nam & Đồ lót',
        'Đồ ăn & Đồ uống', 'Trẻ sơ sinh & thai sản', 'Đồ gia dụng', 'Phụ kiện thời trang'
    ]) AS niche
),
dedup AS (
    SELECT post_base_id, channel_base_id, channel_name, created_at_platform,
           view_count, reaction_count, comment_count, share_count, collect_count,
           list_product_base_id, length(list_product_base_id) AS n_prod
    FROM bee_transform.post_base
    WHERE created_at_platform >= subtractDays(now(), 90)
    ORDER BY updated_at DESC LIMIT 1 BY post_base_id
),
scoped AS (
    SELECT d.*, w.window_days FROM dedup d
    CROSS JOIN (SELECT arrayJoin([14, 30, 90]) AS window_days) w
    WHERE d.created_at_platform >= subtractDays(now(), w.window_days)
),
ch AS (
    SELECT channel_base_id, follower_count FROM bee_transform.channel_base
    WHERE follower_count > 1000 AND lowerUTF8(country) = 'vn'
    ORDER BY updated_at DESC LIMIT 1 BY channel_base_id
),
vid_prod AS (
    SELECT e.window_days, e.channel_base_id, e.post_base_id, any(e.view_count) AS view_count,
           ifNull(c.category_name, 'Unknown') AS category, count() AS prod_cnt
    FROM (
        SELECT window_days, channel_base_id, post_base_id, view_count, arrayJoin(list_product_base_id) AS product_base_id
        FROM scoped WHERE n_prod > 0
    ) e
    LEFT JOIN analytics.products p ON e.product_base_id = p.product_base_id
    LEFT JOIN mapping.categories c ON toString(p.categories__id_1) = c.category_id
    GROUP BY e.window_days, e.channel_base_id, e.post_base_id, category
),
vid_dom AS (
    SELECT window_days, channel_base_id, post_base_id, any(view_count) AS view_count, argMax(category, prod_cnt) AS category
    FROM vid_prod GROUP BY window_days, channel_base_id, post_base_id
),
creator_niche AS (
    SELECT window_days, channel_base_id AS channel_id, argMax(category, cat_view) AS primary_niche
    FROM (
        SELECT window_days, channel_base_id, category, sum(view_count) AS cat_view
        FROM vid_dom GROUP BY window_days, channel_base_id, category
    ) GROUP BY window_days, channel_base_id
),
creator AS (
    SELECT s.window_days, s.channel_base_id AS channel_id, any(s.channel_name) AS channel_name,
           any(c.follower_count) AS followers, count() AS video_count,
           medianIf(s.view_count / c.follower_count, c.follower_count > 0) AS view_rate,
           medianIf(s.reaction_count/ s.view_count, s.view_count > 0) AS like_rate,
           medianIf(s.comment_count / s.view_count, s.view_count > 0) AS comment_rate,
           medianIf(s.share_count   / s.view_count, s.view_count > 0) AS share_rate,
           countIf(s.n_prod > 0) / count() AS shoppable_rate,
           countIf(s.n_prod > 0) AS shoppable_video_count,
           medianIf(s.view_count, s.n_prod > 0 AND s.view_count > 0) AS shoppable_med_view,
           medianIf((s.collect_count + s.share_count) / s.view_count, s.n_prod > 0 AND s.view_count > 0) AS purchase_intent
    FROM scoped s
    INNER JOIN ch c ON s.channel_base_id = c.channel_base_id
    GROUP BY s.window_days, s.channel_base_id
    HAVING video_count >= 3 AND comment_rate IS NOT NULL
),
feat AS (
    SELECT cr.*, cn.primary_niche,
           multiIf(followers < 10000, '1K-10K', followers < 100000, '10K-100K', followers < 1000000, '100K-1M', '1M+') AS tier
    FROM creator cr
    INNER JOIN creator_niche cn ON cr.channel_id = cn.channel_id AND cr.window_days = cn.window_days
    WHERE cn.primary_niche IN (SELECT niche FROM allowed_niche)
)
SELECT window_days, channel_id, channel_name, followers, tier, primary_niche, video_count, view_rate, like_rate, comment_rate, share_rate,
       shoppable_rate, shoppable_video_count, shoppable_med_view, purchase_intent,
       toUInt8(round(100.0*(rank() OVER (PARTITION BY window_days, tier, primary_niche ORDER BY view_rate)   -1)/nullIf(count() OVER (PARTITION BY window_days, tier, primary_niche)-1,0))) AS view_pctile,
       toUInt8(round(100.0*(rank() OVER (PARTITION BY window_days, tier, primary_niche ORDER BY like_rate)   -1)/nullIf(count() OVER (PARTITION BY window_days, tier, primary_niche)-1,0))) AS like_pctile,
       toUInt8(round(100.0*(rank() OVER (PARTITION BY window_days, tier, primary_niche ORDER BY comment_rate)-1)/nullIf(count() OVER (PARTITION BY window_days, tier, primary_niche)-1,0))) AS comment_pctile,
       toUInt8(round(100.0*(rank() OVER (PARTITION BY window_days, tier, primary_niche ORDER BY share_rate)  -1)/nullIf(count() OVER (PARTITION BY window_days, tier, primary_niche)-1,0))) AS share_pctile
FROM feat ORDER BY window_days, tier, primary_niche, comment_pctile DESC;
