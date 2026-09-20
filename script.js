/* ============================================================
   Nik Harun — portfolio
   Three small jobs: keep the local clock honest, draw the
   highlighter once when the page settles, and let people take
   the email address without selecting it by hand.
   No scroll hijacking. No libraries.
   ============================================================ */

const reducedMotion = matchMedia("(prefers-reduced-motion: reduce)").matches;

/* ---------- local time in Kuala Lumpur ---------- */
(function clock() {
  const el = document.getElementById("clock");
  if (!el) return;

  const tick = () => {
    el.textContent = new Date().toLocaleTimeString("en-GB", {
      timeZone: "Asia/Kuala_Lumpur",
      hour: "2-digit",
      minute: "2-digit",
    }) + " GMT+8";
  };

  tick();
  setInterval(tick, 20000);
})();

/* ---------- the one orchestrated moment: the marker swipe ----------
   Waits for the webfont so the swipe matches the settled text width. */
(function marker() {
  const el = document.getElementById("mark");
  if (!el) return;

  const draw = () => requestAnimationFrame(() => el.classList.add("is-marked"));

  if (reducedMotion) { el.classList.add("is-marked"); return; }

  const ready = document.fonts ? document.fonts.ready : Promise.resolve();
  ready.then(() => setTimeout(draw, 260)).catch(draw);
})();

/* ---------- copy the email address ---------- */
(function copyEmail() {
  const btn = document.getElementById("copyEmail");
  const label = document.getElementById("copyLabel");
  const status = document.getElementById("copyStatus");
  if (!btn || !label || !status) return;

  let restore;

  btn.addEventListener("click", async () => {
    const email = btn.dataset.email;

    try {
      await navigator.clipboard.writeText(email);
      label.textContent = "Copied";
      status.textContent = email + " is on your clipboard.";
    } catch {
      // Clipboard blocked (insecure context, or the user said no).
      // Select the address so it can be copied the usual way.
      const target = document.querySelector(".contact__addr");
      if (target) {
        const range = document.createRange();
        range.selectNodeContents(target);
        const sel = getSelection();
        sel.removeAllRanges();
        sel.addRange(range);
      }
      label.textContent = "Copy address";
      status.textContent = "Could not reach the clipboard. The address is selected below — copy it from there.";
    }

    clearTimeout(restore);
    restore = setTimeout(() => {
      label.textContent = "Copy address";
      status.textContent = "";
    }, 4000);
  });
})();
