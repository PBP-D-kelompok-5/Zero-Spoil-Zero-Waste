/* =========================================================
   Pantry Death Clock: interaksi AJAX (fetch) tanpa memuat ulang halaman.
   Progressive enhancement: tanpa JavaScript, semua form tetap jalan lewat
   redirect biasa. Server mengirim HTML yang sudah di-escape Django, jadi
   aman dimasukkan dengan innerHTML; pesan teks memakai textContent.
   ========================================================= */
(function () {
  "use strict";

  const root = document.querySelector("[data-dc-root]");
  if (!root) return;

  const list = document.getElementById("dc-list");
  const filterForm = root.querySelector("[data-dc-filter]");
  const dialog = document.getElementById("dc-dialog");
  const dialogTitle = document.getElementById("dc-dialog-title");
  const dialogBody = dialog.querySelector("[data-dc-dialog-body]");
  const toasts = document.getElementById("dc-toasts");
  const csrfToken = root.querySelector('input[name="csrfmiddlewaretoken"]').value;
  const supportsDialog = typeof dialog.showModal === "function";

  // ---------- Utilitas ----------
  class RequestError extends Error {}
  class Redirecting extends Error {}

  async function send(url, { method = "GET", body, signal } = {}) {
    const headers = { "X-Requested-With": "XMLHttpRequest", Accept: "application/json" };
    if (method !== "GET") headers["X-CSRFToken"] = csrfToken;
    const response = await fetch(url, { method, body, signal, headers, credentials: "same-origin" });
    let data = {};
    try {
      data = await response.json();
    } catch (_) {
      /* respons bukan JSON (mis. halaman error) */
    }
    if (response.status === 401) {
      // Sesi habis: arahkan ke halaman masuk lalu kembali ke sini.
      window.location.href = `${data.login_url || "/login/"}?next=${encodeURIComponent(location.pathname)}`;
      throw new Redirecting();
    }
    return { response, data };
  }

  function toast(message, tone = "ecto") {
    if (!message) return;
    const el = document.createElement("div");
    el.className = `pn-alert dc-toast pn-tone-${tone}`;
    el.setAttribute("role", "status");
    el.textContent = message;
    toasts.appendChild(el);
    setTimeout(() => {
      el.classList.add("is-leaving");
      setTimeout(() => el.remove(), 220);
    }, 3600);
  }

  function showError(error, data) {
    if (error && (error.name === "AbortError" || error instanceof Redirecting)) return;
    const message = (data && data.detail) || (error instanceof RequestError && error.message) || "Gagal terhubung ke server. Coba lagi sebentar.";
    toast(message, "blood");
  }

  function updateCounts(counts) {
    if (!counts) return;
    root.querySelectorAll("[data-dc-count]").forEach((el) => {
      if (el.dataset.dcCount in counts) el.textContent = counts[el.dataset.dcCount];
    });
  }

  function syncTiles() {
    const status = filterForm.elements.status.value;
    root.querySelectorAll("[data-dc-status]").forEach((tile) => {
      const active = tile.dataset.dcStatus === status;
      tile.classList.toggle("is-active", active);
      tile.setAttribute("aria-pressed", String(active));
    });
  }

  function htmlToElement(html) {
    const template = document.createElement("template");
    template.innerHTML = html.trim();
    return template.content.firstElementChild;
  }

  // ---------- Daftar & filter ----------
  let listController = null;

  async function refreshList() {
    const params = new URLSearchParams();
    new FormData(filterForm).forEach((value, key) => {
      if (String(value).trim()) params.append(key, value);
    });
    const query = params.toString() ? `?${params}` : "";

    if (listController) listController.abort();
    const controller = new AbortController();
    listController = controller;
    list.setAttribute("aria-busy", "true");
    try {
      const { response, data } = await send(filterForm.action + query, { signal: controller.signal });
      if (!response.ok) throw new RequestError();
      list.innerHTML = data.html;
      updateCounts(data.counts);
      syncTiles();
      history.replaceState(null, "", location.pathname + query);
    } catch (error) {
      showError(error);
    } finally {
      if (listController === controller) list.removeAttribute("aria-busy");
    }
  }

  function clearFilters() {
    Array.from(filterForm.elements).forEach((field) => {
      if (field.name) field.value = "";
    });
  }

  let searchTimer;
  filterForm.addEventListener("input", (event) => {
    if (event.target.name !== "q") return;
    clearTimeout(searchTimer);
    searchTimer = setTimeout(refreshList, 300);
  });
  filterForm.addEventListener("change", (event) => {
    if (event.target.name !== "q") refreshList();
  });
  filterForm.addEventListener("submit", (event) => {
    event.preventDefault();
    clearTimeout(searchTimer);
    refreshList();
  });

  // ---------- Modal tambah / ubah ----------
  function focusFirstField() {
    const target = dialogBody.querySelector('[aria-invalid="true"]') || dialogBody.querySelector("input:not([type=hidden]), textarea, select");
    if (target) target.focus();
  }

  async function openModal(url, title) {
    dialogTitle.textContent = title || "Bahan";
    dialogBody.innerHTML = '<p class="py-8 text-center text-sm pn-muted">Memuat…</p>';
    dialog.showModal();
    try {
      const { response, data } = await send(url);
      if (!response.ok) throw new RequestError(data.detail || "Bahan tidak ditemukan. Muat ulang halaman.");
      dialogBody.innerHTML = data.html;
      focusFirstField();
    } catch (error) {
      dialog.close();
      showError(error);
    }
  }

  dialog.addEventListener("click", (event) => {
    if (event.target === dialog) dialog.close(); // klik di luar kotak modal
  });
  dialog.addEventListener("close", () => {
    dialogBody.innerHTML = "";
  });

  // ---------- Hapus dua langkah ----------
  function armDelete(form) {
    const button = form.querySelector("button");
    form.dataset.armed = "1";
    button.dataset.label = button.textContent;
    button.textContent = "Yakin hapus?";
    button.classList.add("is-armed");
    setTimeout(() => {
      if (!form.isConnected) return;
      delete form.dataset.armed;
      button.textContent = button.dataset.label;
      button.classList.remove("is-armed");
    }, 3000);
  }

  // ---------- Klik: kotak status, reset, buka/tutup modal ----------
  root.addEventListener("click", (event) => {
    const tile = event.target.closest("[data-dc-status]");
    if (tile) {
      event.preventDefault();
      const select = filterForm.elements.status;
      select.value = select.value === tile.dataset.dcStatus ? "" : tile.dataset.dcStatus;
      refreshList();
      return;
    }

    const reset = event.target.closest("[data-dc-reset]");
    if (reset) {
      event.preventDefault();
      clearFilters();
      refreshList();
      return;
    }

    const closer = event.target.closest("[data-dc-close]");
    if (closer && dialog.contains(closer)) {
      event.preventDefault();
      dialog.close();
      return;
    }

    const opener = event.target.closest("[data-dc-modal]");
    if (opener && supportsDialog) {
      event.preventDefault();
      openModal(opener.href, opener.dataset.dcModal);
    }
  });

  // ---------- Submit: form di modal & aksi cepat di kartu ----------
  root.addEventListener("submit", async (event) => {
    const form = event.target;
    const action = form.dataset.dcAction;
    const inModal = form.hasAttribute("data-dc-form") && dialog.contains(form);
    if (!action && !inModal) return;
    event.preventDefault();
    if (form.dataset.busy) return;
    if (action === "delete" && !form.dataset.armed) {
      armDelete(form);
      return;
    }

    const body = new FormData(form);
    const submitter = event.submitter;
    if (submitter && submitter.name) body.append(submitter.name, submitter.value);

    form.dataset.busy = "1";
    let data = {};
    try {
      const result = await send(form.action, { method: "POST", body });
      data = result.data;

      if (inModal) {
        if (result.response.ok) {
          dialog.close();
          toast(data.message, data.tone);
          refreshList();
        } else if (data.html) {
          dialogBody.innerHTML = data.html; // form dengan pesan error
          focusFirstField();
        } else {
          throw new RequestError();
        }
        return;
      }

      if (!result.response.ok) throw new RequestError();
      if (action === "quantity") {
        const card = htmlToElement(data.html);
        const old = document.getElementById(card.id);
        if (old) old.replaceWith(card);
        updateCounts(data.counts);
        // Pertahankan fokus keyboard pada tombol yang sama.
        const same = submitter && card.querySelector(`button[name="delta"][value="${submitter.value}"]`);
        if (same && !same.disabled) same.focus();
      } else {
        toast(data.message, data.tone);
        refreshList();
      }
    } catch (error) {
      showError(error, data);
    } finally {
      delete form.dataset.busy;
    }
  });
})();
