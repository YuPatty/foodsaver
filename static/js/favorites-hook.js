// static/js/favorites-hook.js
// 攔截「加入喜好 / 購物車」請求，若商品為特價則觸發 /api/favorites/add_notify
// 並可選擇顯示客製的 SalePopup。
// 支援路由：/api/favorites/add、/favorites/add、/cart/add、/api/add_to_cart

(function () {
  if (!window.fetch) return;

  const _origFetch = window.fetch.bind(window);

  function looksLikeFavoritesAdd(url) {
    try {
      const u = typeof url === "string" ? url : (url && url.url) || "";
      return /\/api\/favorites\/add\b/.test(u)
        || /\/favorites\/add\b/.test(u)
        || /\/cart\/add\b/.test(u)
        || /\/api\/add_to_cart\b/.test(u);
    } catch (e) {
      return false;
    }
  }

  async function parseItemIdFromBody(body) {
    try {
      if (!body) return null;

      if (typeof body === "string") {
        // JSON
        try {
          const obj = JSON.parse(body);
          return obj.item_id || obj.product_id || obj.id || null;
        } catch (_) { /* 不是 JSON，往下試 URLSearchParams */ }

        // x-www-form-urlencoded
        const sp = new URLSearchParams(body);
        return sp.get("item_id") || sp.get("product_id") || sp.get("id");
      }

      if (body instanceof FormData) {
        return body.get("item_id") || body.get("product_id") || body.get("id");
      }
      if (body instanceof URLSearchParams) {
        return body.get("item_id") || body.get("product_id") || body.get("id");
      }
    } catch (e) { /* 忽略解析錯誤 */ }
    return null;
  }

  // （可選）拿 spotlight / recommend 的商品資料做彈窗
  async function fetchSpotlightItem(pid) {
    try {
      const res = await _origFetch(`/api/spotlight_products?limit=200`, { credentials: "same-origin" });
      if (!res.ok) return null;
      const arr = await res.json();
      return Array.isArray(arr) ? arr.find(x => String(x.product_id) === String(pid)) : null;
    } catch (_) { return null; }
  }

  async function fetchRecommendItem(pid) {
    try {
      const res = await _origFetch(`/api/recommendations`, { credentials: "same-origin" });
      if (!res.ok) return null;
      const arr = await res.json();
      return Array.isArray(arr) ? arr.find(x => String(x.product_id) === String(pid)) : null;
    } catch (_) { return null; }
  }

  function toPopupItem(rec) {
    if (!rec) return null;

    const discount_pct =
      typeof rec.discount_rate === "number"
        ? Math.round((1 - rec.discount_rate) * 100)
        : (rec.discount_pct ?? null);

    const is_on_sale =
      (typeof rec.discount_rate === "number" && rec.discount_rate < 1) ||
      (typeof discount_pct === "number" && discount_pct > 0);

    const sale_price = is_on_sale
      ? (rec.final_price ?? rec.sale_price ?? null)
      : null;

    return {
      id: rec.product_id ?? rec.id,
      name: rec.name || rec.product_name || "此商品",
      url: `/product/${rec.product_id ?? rec.id}`,
      is_on_sale,
      discount_pct,
      sale_price,
      price: rec.price ?? null,
      store: {
        lat: rec.latitude ?? rec.store_latitude ?? null,
        lng: rec.longitude ?? rec.store_longitude ?? null,
        address: rec.address ?? rec.store_address ?? null
      }
    };
  }

  // 包裝 addToCart（若頁面使用 onclick="addToCart(id)"）
  function wrapAddToCartIfExists() {
    if (typeof window.addToCart !== "function") return;
    const _orig = window.addToCart;
    window.addToCart = async function (pid) {
      const ret = await _orig.apply(this, arguments);
      // 這塊純示範：不依賴通知訊息內容，避免誤判
      try {
        const s1 = await fetchSpotlightItem(pid);
        const s2 = s1 || await fetchRecommendItem(pid);
        const popupItem = toPopupItem(s2);
        if (popupItem && popupItem.is_on_sale && window.SalePopup) {
          window.SalePopup.show(popupItem);
        }
      } catch (_) { /* 忽略錯誤 */ }
      return ret;
    };
  }

  // 輕量等待 addToCart 定義後再 wrap（最多等 3 秒）
  (function waitWrap(t0) {
    if (typeof window.addToCart === "function") { wrapAddToCartIfExists(); return; }
    if ((performance.now() - t0) > 3000) return;
    setTimeout(() => waitWrap(t0), 150);
  })(performance.now());

  // 覆蓋 window.fetch：加入最愛成功後，自動觸發 /api/favorites/add_notify
  window.fetch = async function (url, options = {}) {
    const isFavAdd = looksLikeFavoritesAdd(url);
    const method = (options.method ? String(options.method).toUpperCase() : "GET");

    // 先照原本送出
    const res = await _origFetch(url, options);

    // 只有在「加入最愛」且成功時才打 add_notify
    if (isFavAdd && method === "POST" && res && res.ok) {
      try {
        const pid = await parseItemIdFromBody(options.body);
        if (pid) {
          const r = await _origFetch('/api/favorites/add_notify', {
            method: 'POST',
            credentials: 'include', // 一定帶 cookie，避免被轉到 /login
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ product_id: Number(pid) })
          });

          // 可能回 HTML（未登入或 500），先拿文字再試 JSON
          const text = await r.text();
          let data;
          try {
            data = JSON.parse(text);
          } catch {
            console.warn('add_notify 非 JSON 回應：', r.status, text.slice(0, 200));
            // 不阻斷原始流程
          }

          if (data && (data.ok === false || !r.ok)) {
            console.warn('add_notify 失敗：', r.status, data?.error || data);
          } else if (data && data.ok) {
            // （可選）顯示特價彈窗：用 /api/recommendations 或 /api/spotlight_products 的資料
            try {
              const rec = (await fetchSpotlightItem(pid)) || (await fetchRecommendItem(pid));
              const popupItem = toPopupItem(rec);
              if (popupItem && popupItem.is_on_sale && window.SalePopup) {
                window.SalePopup.show(popupItem);
              }
            } catch (_) { /* 忽略 */ }
          }
        }
      } catch (err) {
        console.warn('add_notify 例外：', err);
      }
    }

    // 一定回傳原始回應，避免呼叫端拿到 undefined
    return res;
  };
})();
