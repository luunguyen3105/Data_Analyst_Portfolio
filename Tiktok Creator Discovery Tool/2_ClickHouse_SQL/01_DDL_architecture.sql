- video.video__analytics source

CREATE VIEW video.video__analytics
(

    `channel_id` Nullable(String),

    `video_id` String,

    `updated_at` DateTime,

    `hashtags` Array(String),

    `search_keywords` Array(String),

    `description` String,

    `created_at` DateTime,

    `viewed` UInt32,

    `liked` UInt32,

    `shared` UInt32,

    `collected` UInt32,

    `commented` UInt32,

    `video_attributes` Map(String,
 String),

    `tiktok_url` String,

    `channel_name` String,

    `viewed__data` Array(Tuple(
        Date,

        Int64,

        UInt64)),

    `liked__data` Array(Tuple(
        Date,

        Int64,

        UInt64)),

    `shared__data` Array(Tuple(
        Date,

        Int64,

        UInt64)),

    `collected__data` Array(Tuple(
        Date,

        Int64,

        UInt64)),

    `commented__data` Array(Tuple(
        Date,

        Int64,

        UInt64)),

    `source__arr` Array(UInt8),

    `channel__channel_name` Nullable(String),

    `channel__followers` Nullable(UInt32),

    `channel__likes` Nullable(UInt32),

    `channel__followings` Nullable(UInt32),

    `channel__description` Nullable(String),

    `channel__updated_at` Nullable(DateTime),

    `duration` UInt32,

    `platform_created_at` DateTime
)
AS SELECT
    *,

    created_at AS platform_created_at
FROM video.video__analytics_v2 AS va;




-- raw_transform.channel_base DDL definition: Table creator metadata

CREATE TABLE raw_transform.channel_base
(

    `channel_base_id` String,

    `platform_id` UInt8,

    `platform` LowCardinality(String),

    `updated_at` DateTime,

    `country` LowCardinality(Nullable(String)),

    `is_vietnamese` Nullable(UInt8),

    `created_at_platform` Nullable(DateTime),

    `channel_id` String,

    `user_id` Nullable(String),

    `channel_name` Nullable(String),

    `sec_user_id` Nullable(String),

    `bio` Nullable(String),

    `bio_link` Nullable(String),

    `language` Nullable(String),

    `avatar_url` Nullable(String),

    `avatar_url_list` Array(String) DEFAULT [],

    `cover_url` Nullable(String),

    `cover_url_list` Array(String) DEFAULT [],

    `is_seller` Nullable(UInt8),

    `is_organization` Nullable(UInt8),

    `is_private` Nullable(UInt8),

    `is_verified` Nullable(UInt8),

    `is_commerce_user` Nullable(UInt8),

    `category` Nullable(String),

    `status` Nullable(UInt8),

    `unique_id_modify_time` Nullable(String),

    `nick_name_modify_time` Nullable(String),

    `is_ad_virtual` Nullable(UInt8),

    `phone_number` Nullable(String),

    `email` Nullable(String),

    `youtube_url` Nullable(String),

    `facebook_url` Nullable(String),

    `twitter_url` Nullable(String),

    `follower_count` Nullable(UInt32),

    `following_count` Nullable(UInt32),

    `video_count` Nullable(UInt32),

    `reaction_count` Nullable(UInt32),

    `outbound_reaction_count` Nullable(UInt32),

    `friend_count` Nullable(UInt32),

    `event_list` Array(String) DEFAULT [],

    `first_time_crawled_at` DateTime,

    `last_time_crawled_at` DateTime
)
ENGINE = MergeTree
ORDER BY (channel_base_id,
 updated_at)
SETTINGS index_granularity = 8192,
 enable_block_number_column = 1,
 enable_block_offset_column = 1;


-- raw_transform.post_base DDL definition: Video infomation

CREATE TABLE raw_transform.post_base
(

    `post_base_id` String,

    `platform_id` UInt8,

    `platform` LowCardinality(String),

    `channel_base_id` Nullable(String),

    `updated_at` DateTime,

    `country` LowCardinality(Nullable(String)),

    `is_vietnamese` Nullable(UInt8),

    `post_id_platform` String,

    `post_type` LowCardinality(Nullable(String)),

    `created_at_platform` Nullable(DateTime),

    `title` Nullable(String),

    `description` Nullable(String),

    `transcript_url` Nullable(String),

    `transcript` Nullable(String),

    `post_url` String,

    `thumbnail_url` Nullable(String),

    `media_url` Nullable(String),

    `media_urls` Array(String) DEFAULT [],

    `duration_in_second` Nullable(UInt32),

    `hashtags` Array(String) DEFAULT [],

    `is_ads` Nullable(UInt8),

    `is_commerce_video` Nullable(UInt8),

    `has_affiliate` Nullable(UInt8),

    `search_keywords` Array(String) DEFAULT [],

    `product_urls` Array(String) DEFAULT [],

    `list_product_base_id` Array(String) DEFAULT [],

    `list_shop_base_id` Array(String) DEFAULT [],

    `location` Nullable(String),

    `category` LowCardinality(Nullable(String)),

    `category_id` LowCardinality(Nullable(String)),

    `categories` Array(String) DEFAULT [],

    `is_ai_generated` Nullable(Int8),

    `status` Nullable(Int8),

    `updated_at_platform` Nullable(DateTime),

    `view_count` Nullable(UInt64),

    `reaction_count` Nullable(UInt32),

    `reaction_detail` Nullable(String),

    `comment_count` Nullable(UInt32),

    `share_count` Nullable(UInt32),

    `repost_count` Nullable(UInt32),

    `forward_count` Nullable(UInt32),

    `collect_count` Nullable(UInt32),

    `download_count` Nullable(UInt32),

    `user_id` Nullable(String),

    `user_name` Nullable(String),

    `sec_uid` Nullable(String),

    `channel_id` Nullable(String),

    `channel_name` Nullable(String),

    `is_verified` Nullable(UInt8),

    `metric_downloaded_thumbnail_url` Nullable(String),

    `metric_downloaded_media_urls` Array(String) DEFAULT [],

    `products_metadata` Nullable(String),

    `album_metadata` Nullable(String),

    `post_metadata` Nullable(String),

    `first_time_crawled_at` DateTime,

    `last_time_crawled_at` DateTime
)
ENGINE = MergeTree
ORDER BY (post_base_id,
 updated_at)
SETTINGS index_granularity = 8192,
 enable_block_number_column = 1,
 enable_block_offset_column = 1;