/**
 * SHOPEE MALL CRAWLER – DevTools Console Snippet v2
 * ===================================================
 * Cách dùng:
 *   1. Mở https://shopee.vn/mall trong Edge/Chrome (đã đăng nhập)
 *   2. Nhấn F12 → tab Console
 *   3. Paste toàn bộ script này → Enter
 *   4. Script tự điều hướng qua 31 keywords (không reload trang)
 *   5. Cuối cùng tự tải file JSON về máy
 *
 * KHÔNG tự gọi fetch() – để Shopee's own code gọi rồi mình bắt response.
 */

(function () {
    const KEYWORDS = [
        'Dầu gội', 'Dầu gội nam', 'Dầu gội nước hoa', 'Dầu gội trị gàu',
        'Dầu gội thảo dược', 'Dầu gội dược liệu', 'Dầu gội giảm gãy rụng',
        'Sữa tắm', 'Sữa tắm nam', 'Sữa tắm nước hoa', 'Tắm gội cho nam',
        'Nước hoa EDP', 'Tắm gội nước hoa', 'Xịt khử mùi', 'Xịt khử mùi nam',
        'Lăn khử mùi', 'Lăn khử mùi nam', 'Sáp khử mùi', 'Lăn nách',
        'Bộ gội xả', 'Combo gội xả', 'Dầu tắm', 'Sữa rửa mặt',
        'Sữa rửa mặt cho nam', 'Gel vuốt tóc', 'Sáp vuốt tóc',
        'Sáp tạo kiểu tóc', 'Nước hoa nam', 'Dầu xả',
        'Dầu gội phục hồi hư tổn', 'Xịt khử mùi toàn thân',
    ];

    const STORAGE_KEY  = 'shopee_crawl_v2';
    const DATE_STR     = new Date().toISOString().slice(0, 10);
    /** Chờ đến khi có `search_items` trong results (sau khi navigate xong). Lần đầu / mạng chậm cần > 6s. */
    const WAIT_AFTER_NAV  = 20000;
    const WAIT_BETWEEN_KW = () => 3000 + Math.random() * 4000;

    /** Chuẩn hóa keyword làm key object (tránh lệch NFC/NFD với URL). */
    function keyFor(k) {
        return String(k).normalize('NFC');
    }

    // ── Load cache ──────────────────────────────────────────────
    let results = {};
    try {
        const raw = JSON.parse(localStorage.getItem(STORAGE_KEY) || '{}');
        results = {};
        for (const [k, v] of Object.entries(raw)) {
            results[keyFor(k)] = v;
        }
    } catch (_) {}
    const cached = Object.keys(results).length;
    if (cached) console.log(`%c[CACHE] Tiếp tục: đã có ${cached}/${KEYWORDS.length} keywords`, 'color:#0a0');

    // ── Ngăn chạy 2 lần cùng lúc ───────────────────────────────
    if (window.__shopee_crawl_running) {
        console.warn('[WARN] Snippet đang chạy rồi! Không paste lại.');
        return;
    }
    window.__shopee_crawl_running = true;

    // ── Override XMLHttpRequest để bắt response ─────────────────
    // Shopee dùng XHR để gọi search_items API
    const _origOpen = XMLHttpRequest.prototype.open;
    const _origSend = XMLHttpRequest.prototype.send;

    XMLHttpRequest.prototype.open = function (method, url, ...rest) {
        this.__url = url;
        return _origOpen.call(this, method, url, ...rest);
    };

    XMLHttpRequest.prototype.send = function (...args) {
        this.addEventListener('load', function () {
            if (!this.__url || !this.__url.includes('search_items')) return;
            try {
                const data = JSON.parse(this.responseText);
                if (!data || !data.items) return;

                const urlObj  = new URL(this.__url, location.origin);
                const keyword = urlObj.searchParams.get('keyword');
                if (!keyword) return;

                const k = keyFor(keyword);
                results[k] = data;
                localStorage.setItem(STORAGE_KEY, JSON.stringify(results));

                const done = Object.keys(results).length;
                console.log(
                    `%c[${done}/${KEYWORDS.length}] ✓ "${k}" → ${data.items.length} items`,
                    'color:#0a0; font-weight:bold'
                );

                window.__shopee_last_captured = k;
            } catch (_) {}
        });
        return _origSend.call(this, ...args);
    };

    // ── Override fetch() để bắt cả fetch-based requests ─────────
    const _origFetch = window.fetch;
    window.fetch = function (input, init) {
        const url = typeof input === 'string' ? input : (input && input.url) || '';
        return _origFetch.call(this, input, init).then(resp => {
            if (!url.includes('search_items')) return resp;
            resp.clone().json().then(data => {
                if (!data || !data.items) return;
                const urlObj  = new URL(url, location.origin);
                const keyword = urlObj.searchParams.get('keyword');
                if (!keyword) return;

                const k = keyFor(keyword);
                results[k] = data;
                localStorage.setItem(STORAGE_KEY, JSON.stringify(results));

                const done = Object.keys(results).length;
                console.log(
                    `%c[${done}/${KEYWORDS.length}] ✓ "${k}" → ${data.items.length} items`,
                    'color:#0a0; font-weight:bold'
                );
                window.__shopee_last_captured = k;
            }).catch(() => {});
            return resp;
        });
    };

    // ── Navigate không reload (SPA routing) ─────────────────────
    async function navigateTo(keyword) {
        const bust = Date.now();
        const url = `/mall/search?keyword=${encodeURIComponent(keyword)}&_t=${bust}`;
        history.pushState({ keyword, bust }, '', url);
        window.dispatchEvent(new PopStateEvent('popstate', { state: { keyword } }));
        window.dispatchEvent(new Event('locationchange'));
        await sleep(100);
    }

    // ── Download JSON ────────────────────────────────────────────
    function downloadData() {
        const total = Object.keys(results).length;
        if (total === 0) { console.warn('[WARN] Không có data để download.'); return; }

        const blob = new Blob([JSON.stringify(results, null, 2)], { type: 'application/json' });
        const a    = document.createElement('a');
        a.href     = URL.createObjectURL(blob);
        a.download = `shopee_mall_all_keywords_${DATE_STR}.json`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(a.href);

        console.log(`%c[DONE] Đã tải file: shopee_mall_all_keywords_${DATE_STR}.json (${total} keywords)`, 'color:#08f;font-weight:bold');
        console.log('%c→ Chạy Python: python shopee_mall_import_from_json.py', 'color:#08f');

        localStorage.removeItem(STORAGE_KEY);
        window.__shopee_crawl_running = false;
    }

    // ── Vòng lặp chính ──────────────────────────────────────────
    async function sleep(ms) { return new Promise(r => setTimeout(r, ms)); }

    async function waitUntilKeywordInResults(kw) {
        const kNorm = keyFor(kw);
        const deadline = Date.now() + WAIT_AFTER_NAV;
        while (Date.now() < deadline && !results[kNorm]) {
            await sleep(500);
        }
        return !!results[kNorm];
    }

    async function run() {
        const pending = KEYWORDS.filter(k => !results[keyFor(k)]);
        console.log(`%c[START] ${pending.length} keywords còn lại`, 'color:#08f;font-weight:bold');

        if (pending.length === 0) {
            console.log('[INFO] Tất cả đã có trong cache → Đang download...');
            downloadData();
            return;
        }

        for (let i = 0; i < pending.length; i++) {
            const kw = pending[i];
            console.log(`%c→ [${i+1}/${pending.length}] Navigate: "${kw}"`, 'color:#888');

            await navigateTo(kw);

            let ok = await waitUntilKeywordInResults(kw);
            if (!ok) {
                console.warn(`%c  [RETRY] Thử lại navigate cho "${kw}"...`, 'color:orange');
                await navigateTo(kw);
                ok = await waitUntilKeywordInResults(kw);
            }

            if (!ok) {
                console.warn(`%c  [!] Vẫn chưa có data cho "${kw}" (bỏ qua, có thể chạy lại snippet)`, 'color:orange');
            }

            if (i < pending.length - 1) {
                const delay = WAIT_BETWEEN_KW();
                console.log(`   ... chờ ${(delay/1000).toFixed(1)}s`);
                await sleep(delay);
            }
        }

        console.log('\n%c═══ XONG ═══', 'color:#08f;font-weight:bold');
        downloadData();
    }

    run();
    console.log('%c[INFO] Để download thủ công bất cứ lúc nào: downloadData()', 'color:#888');
    window.downloadData = downloadData;

})();
