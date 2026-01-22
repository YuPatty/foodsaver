// static/js/sale-popup.js
// 管理「喜好項目特價」彈窗

window.SalePopup = (function(){
  const root = () => document.getElementById('sale-popup');
  const el = {
    name: () => document.getElementById('sale-popup-item-name'),
    discount: () => document.getElementById('sale-popup-discount'),
    btnDetail: () => document.getElementById('sale-popup-detail'),
    btnNav: () => document.getElementById('sale-popup-nav')
  };

  function mapsUrl({ lat, lng, address }) {
    if (typeof lat === 'number' && typeof lng === 'number') {
      return `https://www.google.com/maps/dir/?api=1&destination=${lat},${lng}`;
    }
    if (address) {
      return `https://www.google.com/maps/dir/?api=1&destination=${encodeURIComponent(address)}`;
    }
    return 'https://www.google.com/maps';
  }

  function formatDiscount({ discount_pct, sale_price, price }) {
    if (typeof discount_pct === 'number') return `${Math.round(discount_pct)}% OFF`;
    if (typeof sale_price === 'number' && typeof price === 'number' && price > 0) {
      const pct = Math.round((1 - sale_price/price) * 100);
      return `${pct}% OFF`;
    }
    if (typeof sale_price === 'number') return `特價 $${sale_price}`;
    return '特價中';
  }

  function show(data) {
    const r = root();
    if (!r) return;

    el.name().textContent = data?.name ?? '此商品';
    el.discount().textContent = formatDiscount({
      discount_pct: data?.discount_pct,
      sale_price: data?.sale_price,
      price: data?.price
    });

    el.btnDetail().setAttribute('href', data?.url ?? `/items/${data?.id ?? ''}`);

    const { lat, lng, address } = (data?.store ?? {});
    el.btnNav().setAttribute('href', mapsUrl({ lat, lng, address }));

    r.classList.remove('hidden');
    const onKey = (e) => { if (e.key === 'Escape') hide(); };
    document.addEventListener('keydown', onKey, { once: true });
  }

  function hide() {
    const r = root();
    if (r) r.classList.add('hidden');
  }

  return { show, hide };
})();

// 讓點「X」或點背景遮罩都能關閉
document.addEventListener('DOMContentLoaded', () => {
  const root = document.getElementById('sale-popup');
  if (!root) return;

  root.addEventListener('click', (e) => {
    // 點 X 關閉
    if (e.target.closest('.sale-popup__close')) {
      e.preventDefault();
      if (window.SalePopup) SalePopup.hide();
      return;
    }
    // 點背景遮罩（不是卡片）也關閉
    if (e.target === root) {
      if (window.SalePopup) SalePopup.hide();
    }
  });
});

