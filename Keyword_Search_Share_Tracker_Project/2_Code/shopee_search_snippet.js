/**
 * SHOPEE SEARCH (toàn sàn) – DevTools Console Snippet
 * =====================================================
 * Cách dùng:
 *   1. Mở https://shopee.vn trong Edge/Chrome (đã đăng nhập)
 *   2. Nhấn F12 → tab Console
 *   3. Paste toàn bộ script này → Enter
 *   4. Script tự điều hướng qua tất cả keywords (không reload trang)
 *   5. Cuối cùng tự tải file JSON về máy
 *
 * Sau khi có file JSON, chạy Python:
 *   python shopee_import_from_json.py
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
        'Dầu gội phục hồi hư tổn', 'Xịt khử mùi toàn thân'
    ];

    const STORAGE_KEY     = 'shopee_search_v2';
    const DATE_STR        = new Date().toISOString().slice(0, 10);
    /** Chờ đến khi có `search_items` trong results (sau khi navigate xong). Lần đầu / mạng chậm cần cao hơn 6s. */
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
    if (cached) console.log(`%c[CACHE] Tiep tuc: da co ${cached}/${KEYWORDS.length} keywords`, 'color:#0a0');

    if (window.__shopee_search_running) {
        console.warn('[WARN] Snippet dang chay roi!');
        return;
    }
    window.__shopee_search_running = true;

    // ── Override XMLHttpRequest ──────────────────────────────────
    const _origOpen = XMLHttpRequest.prototype.open;
    const _origSend = XMLHttpRequest.prototype.send;

    XMLHttpRequest.prototype.open = function (method, url, ...rest) {
        this.__url = url;
        return _origOpen.call(this, method, url, ...rest);
    };

    XMLHttpRequest.prototype.send = function (...args) {
        this.addEventListener('load', function () {
            // Debug: log tất cả XHR để tìm đúng endpoint
            if (this.__url && this.__url.includes('shopee.vn/api')) {
                console.log('%c[XHR] ' + this.__url.split('?')[0], 'color:#aaa;font-size:10px');
            }
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
                console.log(`%c[${done}/${KEYWORDS.length}] ✓ "${k}" → ${data.items.length} items`, 'color:#0a0;font-weight:bold');
                window.__shopee_search_last = k;
            } catch (_) {}
        });
        return _origSend.call(this, ...args);
    };

    // ── Override fetch ───────────────────────────────────────────
    const _origFetch = window.fetch;
    window.fetch = function (input, init) {
        const url = typeof input === 'string' ? input : (input && input.url) || '';
        return _origFetch.call(this, input, init).then(resp => {
            // Debug: log tất cả fetch để tìm đúng endpoint
            if (url.includes('shopee.vn/api')) {
                console.log('%c[FETCH] ' + url.split('?')[0], 'color:#aaa;font-size:10px');
            }
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
                console.log(`%c[${done}/${KEYWORDS.length}] ✓ "${k}" → ${data.items.length} items`, 'color:#0a0;font-weight:bold');
                window.__shopee_search_last = k;
            }).catch(() => {});
            return resp;
        });
    };

    // ── Navigate SPA (không reload) ──────────────────────────────
    async function navigateTo(keyword) {
        // Bước 1: về trang chủ → force unmount search component
        history.pushState({}, '', '/');
        window.dispatchEvent(new PopStateEvent('popstate', { state: {} }));
        await new Promise(r => setTimeout(r, 1000));

        // Bước 2: navigate đến keyword với timestamp → bypass Shopee internal cache
        const bust = Date.now();
        const url = `/search?keyword=${encodeURIComponent(keyword)}&_t=${bust}`;
        history.pushState({ keyword, bust }, '', url);
        window.dispatchEvent(new PopStateEvent('popstate', { state: { keyword } }));
        window.dispatchEvent(new Event('locationchange'));
    }

    // ── Download JSON ────────────────────────────────────────────
    function downloadData() {
        const total = Object.keys(results).length;
        if (total === 0) { console.warn('[WARN] Khong co data.'); return; }

        const blob = new Blob([JSON.stringify(results, null, 2)], { type: 'application/json' });
        const a    = document.createElement('a');
        a.href     = URL.createObjectURL(blob);
        a.download = `shopee_search_all_keywords_${DATE_STR}.json`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(a.href);

        console.log(`%c[DONE] Da tai: shopee_search_all_keywords_${DATE_STR}.json (${total} keywords)`, 'color:#08f;font-weight:bold');
        console.log('%c→ Chay Python: python shopee_import_from_json.py', 'color:#08f');
        localStorage.removeItem(STORAGE_KEY);
        window.__shopee_search_running = false;
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
        console.log(`%c[START] ${pending.length} keywords con lai`, 'color:#08f;font-weight:bold');

        if (pending.length === 0) {
            downloadData();
            return;
        }

        for (let i = 0; i < pending.length; i++) {
            const kw = pending[i];
            console.log(`%c→ [${i+1}/${pending.length}] "${kw}"`, 'color:#888');

            await navigateTo(kw);

            let ok = await waitUntilKeywordInResults(kw);
            if (!ok) {
                console.warn(`%c  [RETRY] Thu lai navigate cho "${kw}"...`, 'color:orange');
                await navigateTo(kw);
                ok = await waitUntilKeywordInResults(kw);
            }

            if (!ok) {
                console.warn(`%c  [!] Van chua co data cho "${kw}" (bo qua, co the chay lai snippet)`, 'color:orange');
            }

            if (i < pending.length - 1) {
                const delay = WAIT_BETWEEN_KW();
                console.log(`   ... cho ${(delay/1000).toFixed(1)}s`);
                await sleep(delay);
            }
        }

        console.log('\n%c=== XONG ===', 'color:#08f;font-weight:bold');
        downloadData();
    }

    run();
    window.downloadData = downloadData;
    console.log('%c[INFO] De download thu cong bat cu luc nao: downloadData()', 'color:#888');

})();
