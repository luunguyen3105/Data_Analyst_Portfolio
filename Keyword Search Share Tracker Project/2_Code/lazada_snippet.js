/**
 * LAZADA SEARCH – DevTools Console Snippet
 * ==========================================
 * Cách dùng:
 *   1. Mở https://www.lazada.vn trong Chrome/Edge (đã đăng nhập)
 *   2. F12 → tab Console → Paste script này → Enter
 *   3. Script tự gọi API cho 31 keywords (không cần navigate trang)
 *   4. Tự tải file JSON về khi xong
 *
 * Sau khi có file JSON:
 *   python lazada_import_from_json.py
 */

(async () => {
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

    const STORAGE_KEY  = 'lazada_crawl_v1';
    const DATE_STR     = new Date().toISOString().slice(0, 10);
    const DELAY_MS     = () => 3000 + Math.random() * 4000;  // 3–7 giây/keyword

    // ── Load cache ──────────────────────────────────────────────
    let results = {};
    try { results = JSON.parse(localStorage.getItem(STORAGE_KEY) || '{}'); } catch (_) {}
    const cached = Object.keys(results).length;
    if (cached) console.log(`%c[CACHE] Tiếp tục: đã có ${cached}/${KEYWORDS.length} keywords`, 'color:#0a0');

    // ── Lấy CSRF token từ cookie ─────────────────────────────────
    function getCsrfToken() {
        return document.cookie
            .split('; ')
            .find(r => r.startsWith('_tb_token_='))
            ?.split('=')[1] || '';
    }

    // ── Tạo slug từ keyword: "dầu gội" → "dầu-gội" ──────────────
    function toSlug(keyword) {
        return keyword.replace(/\s+/g, '-');
    }

    // ── Gọi Lazada Ajax API ──────────────────────────────────────
    async function fetchKeyword(keyword) {
        const slug = toSlug(keyword);
        const url  = `https://www.lazada.vn/tag/${encodeURIComponent(slug)}/`
                   + `?ajax=true&catalog_redirect_tag=true&isFirstRequest=true&page=1`
                   + `&q=${encodeURIComponent(keyword)}`;

        const resp = await fetch(url, {
            credentials: 'include',         // dùng đúng cookies của browser
            headers: {
                'accept': 'application/json, text/plain, */*',
                'x-csrf-token': getCsrfToken(),
                'referer': 'https://www.lazada.vn/',
            },
        });

        if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
        const data = await resp.json();

        const items = data?.mods?.listItems;
        if (!items) throw new Error(`Không có listItems (keys: ${Object.keys(data?.mods || {}).join(', ')})`);

        return data;
    }

    // ── Download JSON ────────────────────────────────────────────
    function downloadJSON() {
        const total = Object.keys(results).length;
        if (total === 0) { console.warn('[WARN] Không có data.'); return; }

        const blob = new Blob([JSON.stringify(results, null, 2)], { type: 'application/json' });
        const a    = document.createElement('a');
        a.href     = URL.createObjectURL(blob);
        a.download = `lazada_all_keywords_${DATE_STR}.json`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(a.href);

        console.log(`%c[DONE] Đã tải: lazada_all_keywords_${DATE_STR}.json (${total} keywords)`, 'color:#08f;font-weight:bold');
        console.log('%c→ Chạy Python: python lazada_import_from_json.py', 'color:#08f');
        localStorage.removeItem(STORAGE_KEY);
    }

    // ── Vòng lặp chính ──────────────────────────────────────────
    const pending = KEYWORDS.filter(k => !results[k]);
    console.log(`%c[START] ${pending.length} keywords còn lại / ${KEYWORDS.length} tổng`, 'color:#08f;font-weight:bold');

    if (pending.length === 0) {
        downloadJSON();
        return;
    }

    let successCount = 0;
    let failCount    = 0;

    for (let i = 0; i < pending.length; i++) {
        const kw    = pending[i];
        const label = `[${i + 1}/${pending.length}]`;

        try {
            const data      = await fetchKeyword(kw);
            const items     = data.mods.listItems || [];
            results[kw]     = data;
            localStorage.setItem(STORAGE_KEY, JSON.stringify(results));

            successCount++;
            console.log(`%c${label} ✓ "${kw}" → ${items.length} items`, 'color:#0a0;font-weight:bold');

        } catch (err) {
            failCount++;
            console.warn(`%c${label} ✗ "${kw}" → ${err.message}`, 'color:orange');
        }

        if (i < pending.length - 1) {
            const ms = DELAY_MS();
            console.log(`   ... chờ ${(ms / 1000).toFixed(1)}s`);
            await new Promise(r => setTimeout(r, ms));
        }
    }

    console.log(`\n%c═══ XONG: ${successCount} thành công | ${failCount} thất bại ═══`, 'color:#08f;font-weight:bold');
    downloadJSON();
    window.lazadaDownload = downloadJSON;

})();
