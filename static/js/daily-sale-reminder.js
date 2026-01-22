// static/js/daily-sale-reminder.js
// 每天晚上 20:00 彈出提醒：「打折提醒：友善時光開始」
// 不依賴後端，使用瀏覽器本地時間（使用者所在時區）。

(function(){
  const TARGET_HOUR = 20, TARGET_MINUTE = 0, TARGET_SECOND = 0;
  const STORAGE_KEY = 'friendlyHourShownDate'; // 記錄今天是否已彈出

  function ymd(d){
    // 產生 YYYY-MM-DD（以瀏覽器本地時區）
    const y = d.getFullYear();
    const m = String(d.getMonth()+1).padStart(2,'0');
    const dd = String(d.getDate()).padStart(2,'0');
    return `${y}-${m}-${dd}`;
  }

  function ensurePopupDom(){
    if (document.getElementById('friendly-hour-popup')) return;
    const html = `
<div id="friendly-hour-popup" role="dialog" aria-modal="true" aria-labelledby="friendly-hour-title" style="position:fixed;inset:0;display:none;align-items:center;justify-content:center;background:rgba(0,0,0,.45);z-index:10000;">
  <div class="fh-card" style="width:min(92vw,480px);background:#fff;border-radius:16px;padding:20px 20px 16px;box-shadow:0 10px 30px rgba(0,0,0,.25);position:relative;font-family:system-ui,sans-serif;">
    <button type="button" class="fh-close" aria-label="關閉" style="position:absolute;top:10px;right:12px;border:0;background:transparent;font-size:18px;cursor:pointer;">✕</button>
    <h3 id="friendly-hour-title" style="margin:0 0 8px 0;">打折提醒</h3>
    <p class="fh-desc" style="margin:8px 0 16px;line-height:1.5;">友善時光開始</p>
    <div class="fh-actions" style="display:flex;gap:10px;justify-content:flex-end;">
      <button type="button" class="fh-ok" style="padding:10px 14px;border-radius:10px;background:#1f6feb;color:#fff;border:0;cursor:pointer;">知道了</button>
    </div>
  </div>
</div>`;
    document.addEventListener('DOMContentLoaded', () => {
      document.body.insertAdjacentHTML('beforeend', html);
      const root = document.getElementById('friendly-hour-popup');
      root.addEventListener('click', (e) => {
        if (e.target === root || e.target.closest('.fh-close') || e.target.closest('.fh-ok')) {
          hide();
        }
      });
      document.addEventListener('keydown', (e) => { if (e.key === 'Escape') hide(); });
    });
  }

  function show(){
    ensurePopupDom();
    const root = document.getElementById('friendly-hour-popup');
    if (!root) return;
    root.style.display = 'flex';
    // 紀錄今天已彈出
    localStorage.setItem(STORAGE_KEY, ymd(new Date()));
  }

  function hide(){
    const root = document.getElementById('friendly-hour-popup');
    if (!root) return;
    root.style.display = 'none';
  }

  function msUntilNext20(){
    const now = new Date();
    const target = new Date(now);
    target.setHours(TARGET_HOUR, TARGET_MINUTE, TARGET_SECOND, 0);
    if (now >= target) {
      // 已過今天 20:00，排到明天 20:00
      target.setDate(target.getDate() + 1);
    }
    return target - now;
  }

  function schedule(){
    // 排下一次觸發
    const delay = msUntilNext20();
    setTimeout(() => {
      // 到點時如果今天尚未彈出，才顯示
      const today = ymd(new Date());
      if (localStorage.getItem(STORAGE_KEY) !== today) {
        show();
      }
      // 設定明天
      schedule();
    }, delay);
  }

  function maybeShowImmediatelyIfAfter20(){
    // 使用者是 20:00 之後才打開頁面 → 若今天還沒彈過，就延遲 3 秒彈出一次
    const now = new Date();
    const after20 = now.getHours() > TARGET_HOUR || (now.getHours() === TARGET_HOUR && (now.getMinutes() > 0 || now.getSeconds() >= 0));
    const today = ymd(now);
    if (after20 && localStorage.getItem(STORAGE_KEY) !== today) {
      setTimeout(show, 3000);
    }
  }

  // 啟動
  ensurePopupDom();
  document.addEventListener('DOMContentLoaded', () => {
    schedule();
    maybeShowImmediatelyIfAfter20();
  });
})();