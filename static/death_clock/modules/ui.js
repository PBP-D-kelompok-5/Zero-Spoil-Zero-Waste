/* Bagian tampilan bersama: toast, angka ringkasan status, dan kartu yang keluar/masuk daftar. */

const STATUSES = ["FLATLINING", "CRITICAL", "STABLE", "RESURRECTED"];

export function htmlToElement(html) {
  const template = document.createElement("template");
  template.innerHTML = html.trim();
  return template.content.firstElementChild;
}

export function createUi(root) {
  const toasts = root.querySelector("#dc-toasts");

  function toast(message, tone = "ecto") {
    if (!message) return;
    const el = document.createElement("div");
    el.className = `pn-alert dc-toast pn-tone-${tone}`;
    el.setAttribute("role", "status");
    el.textContent = message; // teks, bukan HTML
    toasts.appendChild(el);
    setTimeout(() => {
      el.classList.add("is-leaving");
      setTimeout(() => el.remove(), 220);
    }, 3600);
  }

  function readCounts() {
    const counts = {};
    STATUSES.forEach((status) => {
      const tile = root.querySelector(`[data-dc-count="${status}"]`);
      counts[status] = tile ? Number(tile.textContent) || 0 : 0;
    });
    return counts;
  }

  /** Tulis angka ringkasan (kotak status + peringatan flatlining) dari objek counts. */
  function setCounts(counts) {
    if (!counts) return;
    STATUSES.forEach((status) => {
      const tile = root.querySelector(`[data-dc-count="${status}"]`);
      if (tile && status in counts) tile.textContent = Math.max(0, counts[status]);
    });
    const alert = root.querySelector("[data-dc-alert]");
    if (alert && "FLATLINING" in counts) {
      alert.querySelector("[data-dc-alert-count]").textContent = counts.FLATLINING;
      alert.hidden = counts.FLATLINING <= 0;
    }
  }

  /** Ubah angka secara optimistis, mis. { CRITICAL: -1, RESURRECTED: +1 }. */
  function bumpCounts(changes) {
    const counts = readCounts();
    Object.entries(changes).forEach(([status, delta]) => {
      if (status in counts) counts[status] += delta;
    });
    setCounts(counts);
  }

  function updateVisibleCount() {
    const label = root.querySelector("[data-dc-visible-count]");
    if (label) label.textContent = root.querySelectorAll("[data-dc-item]:not(.is-leaving)").length;
  }

  /**
   * Keluarkan kartu dari daftar sekarang juga (dengan animasi singkat).
   * Mengembalikan fungsi ``restore()`` untuk memasang kartu kembali di posisi semula bila server gagal.
   */
  function removeCard(card) {
    const parent = card.parentNode;
    const next = card.nextElementSibling;
    const focusTarget = (next || card.previousElementSibling)?.querySelector("button:not([disabled]), a");
    card.classList.add("is-leaving");
    card.setAttribute("aria-hidden", "true");
    const timer = setTimeout(() => card.remove(), 180);
    updateVisibleCount();
    if (card.contains(document.activeElement) && focusTarget) focusTarget.focus();
    return function restore() {
      clearTimeout(timer);
      card.classList.remove("is-leaving");
      card.removeAttribute("aria-hidden");
      if (!card.isConnected) parent.insertBefore(card, next && next.isConnected ? next : null);
      updateVisibleCount();
    };
  }

  function cardsLeft() {
    return root.querySelectorAll("[data-dc-item]:not(.is-leaving)").length;
  }

  return { toast, setCounts, bumpCounts, removeCard, cardsLeft, updateVisibleCount };
}
