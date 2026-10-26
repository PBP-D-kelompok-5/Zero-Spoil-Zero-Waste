/* Daftar bahan & filter: memuat ulang fragmen daftar lewat AJAX tanpa memuat ulang halaman. */

import { errorMessage, ensureOk } from "./api.js";

export function createList({ root, send, ui }) {
  const list = root.querySelector("#dc-list");
  const form = root.querySelector("[data-dc-filter]");
  let controller = null;
  let searchTimer;

  function syncTiles() {
    const status = form.elements.status.value;
    root.querySelectorAll("[data-dc-status]").forEach((tile) => {
      const active = tile.dataset.dcStatus === status;
      tile.classList.toggle("is-active", active);
      tile.setAttribute("aria-pressed", String(active));
    });
  }

  function query() {
    const params = new URLSearchParams();
    new FormData(form).forEach((value, key) => {
      if (String(value).trim()) params.append(key, value);
    });
    return params.toString() ? `?${params}` : "";
  }

  /** Ambil ulang daftar sesuai filter. Dipakai juga sebagai "sumber kebenaran" setelah aksi gagal. */
  async function refresh() {
    const search = query();
    if (controller) controller.abort();
    const current = new AbortController();
    controller = current;
    list.setAttribute("aria-busy", "true");
    try {
      const data = ensureOk(await send(form.action + search, { signal: current.signal }));
      list.innerHTML = data.html;
      ui.setCounts(data.counts);
      syncTiles();
      history.replaceState(null, "", location.pathname + search);
    } catch (error) {
      ui.toast(errorMessage(error), "blood");
    } finally {
      if (controller === current) list.removeAttribute("aria-busy");
    }
  }

  function clearFilters() {
    Array.from(form.elements).forEach((field) => {
      if (field.name) field.value = "";
    });
  }

  function toggleStatus(status) {
    const select = form.elements.status;
    select.value = select.value === status ? "" : status;
    refresh();
  }

  form.addEventListener("input", (event) => {
    if (event.target.name !== "q") return;
    clearTimeout(searchTimer);
    searchTimer = setTimeout(refresh, 300);
  });
  form.addEventListener("change", (event) => {
    if (event.target.name !== "q") refresh();
  });
  form.addEventListener("submit", (event) => {
    event.preventDefault();
    clearTimeout(searchTimer);
    refresh();
  });

  return { refresh, clearFilters, toggleStatus };
}
