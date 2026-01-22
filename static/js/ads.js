// 即時品展示欄（取代廣告）：抓 /api/spotlight_products，顯示 2~3 個商品卡，hover 顯示完整資訊
(async function(){
  const wrap = document.getElementById("adsCarousel");
  if (!wrap) return;

  // 從地圖全域拿目前位置 & 品牌（若沒有就省略）
  const lat = (window.currentCenter && window.currentCenter.lat) ? window.currentCenter.lat : 25.033968;
  const lng = (window.currentCenter && window.currentCenter.lng) ? window.currentCenter.lng : 121.564468;
  const brand = (typeof window.currentBrand !== "undefined" && window.currentBrand) ? window.currentBrand : "";
  const qs = new URLSearchParams({ lat, lng, limit: 3 });
  if (brand) qs.set("brand", brand);

  let products = [];
  try{
    const res = await fetch(`/api/spotlight_products?${qs.toString()}`, { credentials: "same-origin" });
    if (!res.ok) { console.warn("spotlight api status", res.status); return; }
    products = await res.json();
  }catch(e){
    console.error("spotlight fetch error", e);
    return;
  }
  if (!products.length){ wrap.innerHTML = ""; return; }

  // UI：水平滾動的卡片列
  wrap.innerHTML = `
    <div class="d-flex gap-2 overflow-auto" id="spotlightRow" style="scroll-snap-type:x mandatory;">
    </div>
  `;
  const row = document.getElementById("spotlightRow");

  // 產卡片（使用高解析圖片避免糊）
  products.forEach(p=>{
    const priceStr = (p.final_price ?? p.price ?? 0).toFixed(0);
    const oldStr = (p.discount_rate && p.discount_rate < 1.0) ? `<span class="text-decoration-line-through text-muted ms-1">${(p.price||0).toFixed(0)}</span>` : "";
    const stars = "★".repeat(Math.floor(p.avg_rating||0)) + "☆".repeat(5 - Math.floor(p.avg_rating||0));

    const card = document.createElement("a");
    card.href = `/product/${p.product_id}`; // 點擊導到商品評價頁（可改為店家頁）
    card.className = "card text-decoration-none";
    card.style.cssText = "min-width: 240px; max-width: 240px; scroll-snap-align:center;";
    card.innerHTML = `
      <img src="${p.image_url || ""}" srcset="${p.image_url || ""} 1x, ${p.image_url || ""} 2x"
           class="card-img-top" alt="${p.name || ""}"
           style="height:120px; object-fit:cover;">
      <div class="card-body py-2">
        <div class="d-flex align-items-center justify-content-between">
          <strong class="text-dark" style="white-space:nowrap; overflow:hidden; text-overflow:ellipsis; max-width:160px;">${p.name || ""}</strong>
          <span class="badge bg-secondary">${(p.brand || "").toString()}</span>
        </div>
        <div class="small text-muted" style="white-space:nowrap; overflow:hidden; text-overflow:ellipsis;">
          ${p.store_name || ""} · ${(p.distance_km!==undefined)?`${p.distance_km} km`:""}
        </div>
        <div class="text-warning">${stars}</div>
        <div class="mt-1">
          <span class="fw-bold text-danger">$${priceStr}</span>${oldStr}
          ${ (p.discount_rate && p.discount_rate < 1.0) ? `<span class="badge bg-danger ms-1">特價</span>` : "" }
        </div>
      </div>
    `;
    // Bootstrap Tooltip（滑鼠移過去顯示完整內容）
    card.setAttribute("data-bs-toggle", "tooltip");
    card.setAttribute("data-bs-html", "true");
    card.setAttribute("title", `
      <div><strong>${p.name || ""}</strong></div>
      <div>${p.store_name || ""}</div>
      <div>${p.address || ""}</div>
      <div>評分：${(p.avg_rating||0).toFixed(1)} / 5（${p.rating_count||0}）</div>
      <div>價格：$${priceStr}</div>
      ${(p.discount_rate && p.discount_rate < 1.0) ? `<div>原價：$${(p.price||0).toFixed(0)}</div>` : ""}
      ${(p.distance_km!==undefined)?`<div>距離：約 ${p.distance_km} km</div>`:""}
    `);
    row.appendChild(card);
  });

  // 啟用 Tooltip
  if (window.bootstrap && bootstrap.Tooltip) {
    const opts = { trigger: "hover", placement: "bottom", container: "body" };
    Array.from(row.querySelectorAll('[data-bs-toggle="tooltip"]')).forEach(el => new bootstrap.Tooltip(el, opts));
  }

  // 當使用者改變品牌或位置時，重新載入 spotlight
  document.addEventListener("brand-or-location-changed", () => {
    // 簡單做法：整頁 reload，或你也可以改成抽換 cards
    window.location.reload();
  });
})();
