/* Modal tambah / tambah massal / ubah memakai <dialog> bawaan. Validasi tetap di server. */

import { RequestError, errorMessage, ensureOk } from "./api.js";

export function createModal({ root, send, ui, onSaved }) {
  const dialog = root.querySelector("#dc-dialog");
  const title = root.querySelector("#dc-dialog-title");
  const body = dialog.querySelector("[data-dc-dialog-body]");
  const supported = typeof dialog.showModal === "function";

  function focusFirstField() {
    const target = body.querySelector('[aria-invalid="true"]') || body.querySelector("input:not([type=hidden]), textarea, select");
    if (target) target.focus();
  }

  async function open(url, heading) {
    title.textContent = heading || "Bahan";
    body.innerHTML = '<p class="py-8 text-center text-sm pn-muted">Memuat…</p>';
    dialog.showModal();
    try {
      body.innerHTML = ensureOk(await send(url), "Bahan tidak ditemukan. Muat ulang halaman.").html;
      focusFirstField();
    } catch (error) {
      dialog.close();
      ui.toast(errorMessage(error), "blood");
    }
  }

  async function submit(form) {
    if (form.dataset.busy) return;
    form.dataset.busy = "1";
    try {
      const { response, data } = await send(form.action, { method: "POST", body: new FormData(form) });
      if (response.ok) {
        dialog.close();
        ui.toast(data.message, data.tone);
        onSaved();
      } else if (data.html) {
        body.innerHTML = data.html; // form beserta pesan galat dari server
        focusFirstField();
      } else {
        throw new RequestError(data.detail || "");
      }
    } catch (error) {
      ui.toast(errorMessage(error), "blood");
    } finally {
      delete form.dataset.busy;
    }
  }

  dialog.addEventListener("click", (event) => {
    if (event.target === dialog) dialog.close(); // klik di luar kotak modal
  });
  dialog.addEventListener("close", () => {
    body.innerHTML = "";
  });

  return {
    supported,
    open,
    submit,
    close: () => dialog.close(),
    contains: (el) => dialog.contains(el),
  };
}
