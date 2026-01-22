function disposeTooltips(root){
  // 關掉元件實例
  (root || document).querySelectorAll('[data-bs-toggle="tooltip"]')
    .forEach(el => window.bootstrap?.Tooltip?.getInstance(el)?.dispose());
  // 保險：把已經插入 DOM 的 tooltip 節點清掉
  document.querySelectorAll('#spotlight .tooltip, body > .tooltip').forEach(t => t.remove());
}

(function(){
  const AUTOPLAY_MS = 3500;     // 自動輪播間隔
  const GAP_PX = 5;            // 卡片間距，需和 CSS 的 gap 一致
  const MAX_ITEMS = 10;         // 取 10 個

  function stars(avg){ const a = Math.floor(avg || 0); return "★".repeat(a) + "☆".repeat(5 - a); }

  // **** 以下是 buildCard(p) 的修改 ****
  function buildCard(p){
  const IS_AUTH = window.IS_AUTH_SPOTLIGHT === true; 
  const priceNow = (p.final_price ?? p.price ?? 0).toFixed(0);
  const priceOld = (p.price ?? 0).toFixed(0);
  const hasDiscount = p.discount_rate && p.discount_rate < 1.0;
  
  const hasDist = typeof p.distance_km === "number";
  const distText = hasDist ? `${(+p.distance_km).toFixed(2)} km` : "";

  const navUrl = `/go/store/${p.store_id || p.product_id}`; 
  
  const tipHtml = `
    <div><strong>${p.name || ""}</strong></div>
    <div>${p.store_name || ""}</div>
    <div>${p.address || ""}</div>
    <div>評分：${(p.avg_rating || 0).toFixed(1)} / 5（${p.rating_count || 0}）</div>
    ${hasDist ? `<div>距離：約 ${distText}</div>` : ""}
  `;

  // 登入狀態下的按鈕群 (與 recommend.html 一致)
  const whenAuthed = `
    <div class="d-flex gap-2 mb-2">
      <a class="btn btn-outline-secondary btn-sm w-50" href="/product/${p.product_id}">詳情/評價</a>
      <button class="btn btn-primary btn-sm w-50" onclick="addFavWithConfirm(${p.product_id})">加入喜愛</button>
    </div>
    <a class="btn btn-outline-dark btn-sm w-100" target="_blank" rel="noopener" href="${navUrl}">導航至商店</a>
  `;

  // 未登入狀態下的按鈕群 (與 recommend.html 一致)
  const whenGuest = `
    <div class="d-flex gap-2">
      <a class="btn btn-outline-secondary btn-sm w-50" href="/product/${p.product_id}">詳情/評價</a>
      <a class="btn btn-outline-dark btn-sm w-50" target="_blank" rel="noopener" href="${navUrl}">導航至商店</a>
    </div>
  `;

  const el = document.createElement("div"); 
  el.className = "card-wrap"; 
  
  el.innerHTML = `
    <div class="card h-100 position-relative d-flex flex-column">
      <div data-bs-toggle="tooltip" 
         data-bs-title="${tipHtml.replace(/"/g, '&quot;')}" 
         data-bs-html="true" 
         data-bs-placement="bottom"
         class="d-block text-decoration-none text-dark flex-grow-1 card-info-hover-area"> <a href="/product/${p.product_id}" class="d-block">
          <img src="${p.image_url || ""}" alt="${p.name || ""}" class="card-img-top">
        </a>
        <div class="card-body py-2 d-flex flex-column">
          <a href="/product/${p.product_id}" class="d-block text-decoration-none text-dark">
              <div class="d-flex align-items-center justify-content-between">
                <div class="fw-semibold text-truncate" style="max-width:160px;">
                  ${p.name || ""}
                </div>
                <span class="badge bg-secondary flex-shrink-0">${p.brand || ""}</span>
              </div>
              <div class="small text-muted text-truncate">
                ${p.store_name || ""}${hasDist ? ` · ${distText}` : ""}
              </div>
              <div class="text-warning">
                ${stars(p.avg_rating)} <span class="small text-muted ms-1">${(p.avg_rating || 0).toFixed(1)}/5</span>
              </div>
              <div class="mt-1">
                <span class="fw-bold text-danger">$${priceNow}</span>
                ${hasDiscount ? `<span class="text-muted text-decoration-line-through ms-1">$${priceOld}</span>` : ""}
              </div>
          </a>
        </div>
      </div>
      <div class="p-2 pt-1 mt-auto"> 
        ${IS_AUTH ? whenAuthed : whenGuest}
      </div>
    </div>
  `;

  return el;
}
//*******

  async function fetchItems(){
    // ... (此函式內容保持不變) ...
    // 從地圖全域拿位置/品牌
    const lat = (window.currentCenter && window.currentCenter.lat) ? window.currentCenter.lat : 25.033968;
    const lng = (window.currentCenter && window.currentCenter.lng) ? window.currentCenter.lng : 121.564468;
    const brand = (typeof window.currentBrand !== "undefined" && window.currentBrand) ? window.currentBrand : "";
    const radius = window.currentRadius || 3; 
    const qs = new URLSearchParams({ lat, lng, radius, limit: MAX_ITEMS });
    if (brand) qs.set("brand", brand);
    const res = await fetch(`/api/spotlight_products?${qs.toString()}`, { credentials:"same-origin" });
    if (!res.ok) return [];
    return await res.json();
  }

  function getVisibleCount(){
    // 根據第一張卡片的 width 推估同時可見數
    // 注意：這裡可能需要調整選擇器，從 .card 改為 .card-wrap 或實際卡片寬度
    const first = document.querySelector("#spotlight .card-wrap");
    if (!first) return 3;
    const cardW = first.clientWidth;
    const boxW = document.getElementById("spotlight").clientWidth;
    return Math.max(1, Math.min(4, Math.floor((boxW + GAP_PX) / (cardW + GAP_PX))));
  }

  function mount(items){
    const host = document.getElementById("spotlight");
    if (!host) return;
    disposeTooltips(host);

    const seen = new Set();
    const uniq = [];
    for (const p of items) {
      const key = p.product_id ?? p.id;
      if (!seen.has(key)) { seen.add(key); uniq.push(p); }
    }
    items = uniq;

    // 確保只剩 track
    host.innerHTML = `<div class="spotlight-track"></div>`; 
    const track = host.querySelector(".spotlight-track");

    // 放入商品卡片
    items.forEach(p => track.appendChild(buildCard(p)));

    // 啟用 tooltip
    if (window.bootstrap && bootstrap.Tooltip) {
      // 針對所有帶有 data-bs-toggle="tooltip" 的元素啟用 Tooltip
      Array.from(track.querySelectorAll('[data-bs-toggle="tooltip"]')).forEach(el => {
        // 防止殘留
        window.bootstrap.Tooltip.getInstance(el)?.dispose();

        new bootstrap.Tooltip(el, {
          trigger: "hover",
          placement: "bottom",
          container: host,      
          boundary: "window",
          html: true,           // 允許 HTML
          sanitize: false,      // 不要把 <div> 當成文字逃脫
          // title 已經在 HTML 中設定 data-bs-title
        });
      });
    }

    // 無限輪播：複製前 visibleCount 張到尾端
    let visibleCount = getVisibleCount();
    const cloneHead = () => {
      // 先移除舊複製
      track.querySelectorAll(".clone").forEach(n => n.remove());
      if (items.length <= visibleCount) return;
      const cards = track.children; // 現在 track 的 children 是 .card-wrap
      for (let i = 0; i < visibleCount && i < items.length; i++) {
        const c = cards[i].cloneNode(true);
        c.classList.add("clone");
        track.appendChild(c);
      }
    };

    // 位移控制
    let idx = 0, timer=null;
    // 找到正確的卡片寬度
    const cardWidth = () => (track.querySelector(".card-wrap")?.clientWidth || 260);
    const stepTo = (i, withAnim=true) => {
      disposeTooltips(document.getElementById("spotlight"));

      idx = i;
      track.style.transition = withAnim ? "transform .5s ease" : "none";
      const x = - (cardWidth() + GAP_PX) * idx;
      track.style.transform = `translateX(${x}px)`;
    };

    const play = ()=>{
      timer = setInterval(()=>{
        const total = items.length;
        // 若已到複製區（=最後一個可見的起點），下一步先動畫到 idx+1，再立刻無動畫歸零
        if (idx >= total){
          // 正在非動畫狀態時，先歸零
          stepTo(0, false);
        }
        stepTo(idx+1, true);
        // 當我們剛好移動到「複製的第1張」(idx === total) → 0.5s 後無動畫歸零
        if (idx+1 === total){
          setTimeout(()=> stepTo(0, false), 520);
        }
      }, AUTOPLAY_MS);
    };
    const stop = ()=> { if (timer) { clearInterval(timer); timer=null; } };

    // 初始化
    cloneHead();
    stepTo(0, false);
    play();

    // 事件：滑鼠暫停、視窗縮放重新計算
    host.addEventListener("mouseenter", stop);
    host.addEventListener("mouseleave", play);
    window.addEventListener("resize", ()=>{
      const old = visibleCount;
      visibleCount = getVisibleCount();
      if (visibleCount !== old){
        stop(); cloneHead(); stepTo(0,false); play();
      }
    });
  }

  async function init(){
    const host = document.getElementById("spotlight");
    if (!host) return;
    const items = await fetchItems();
    if (!items.length){ host.style.display="none"; return; }
    host.style.display = "";
    mount(items);
  }

  // 初載 & 品牌/定位變更時重載
  window.addEventListener("DOMContentLoaded", init);
  document.addEventListener("brand-or-location-changed", init);
})();