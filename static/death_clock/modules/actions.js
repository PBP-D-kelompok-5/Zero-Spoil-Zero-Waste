/* Aksi cepat di kartu dengan optimistic UI: tampilan berubah SEKETIKA, request dikirim di belakang,
   dan bila server menolak (galat jaringan, 429, 404...) tampilan dikembalikan seperti semula. */

import { errorMessage, ensureOk } from "./api.js";
import { htmlToElement } from "./ui.js";

export function createActions({ send, ui, list }) {
  const quantityQueues = new Map(); // per bahan: request jumlah dikirim berurutan

  function fail(error) {
    ui.toast(errorMessage(error), "blood");
  }

  // ---------- Jumlah (+ / −) ----------
  function changeQuantity(form, submitter) {
    const card = form.closest("[data-dc-item]");
    const pk = card.dataset.dcItem;
    const qty = card.querySelector("[data-dc-qty]");
    const before = Number(qty.textContent);
    const after = Math.min(9999, Math.max(1, before + Number(submitter.value)));
    if (after === before) return;

    qty.textContent = after; // seketika
    form.querySelector('button[value="-1"]').disabled = after <= 1;

    const body = new FormData(form);
    body.append("delta", submitter.value);
    let state = quantityQueues.get(pk);
    if (!state) {
      state = { chain: Promise.resolve(), pending: 0, failed: false };
      quantityQueues.set(pk, state);
    }
    state.pending += 1;
    state.chain = state.chain
      .then(async () => (state.failed ? null : ensureOk(await send(form.action, { method: "POST", body }))))
      .then(
        (data) => {
          state.pending -= 1;
          if (state.pending === 0 && !state.failed) {
            quantityQueues.delete(pk);
            syncCard(pk, data.html, submitter.value); // samakan dengan data server
          }
        },
        (error) => {
          state.pending -= 1;
          state.failed = true; // klik yang masih antre tidak dikirim lagi
          quantityQueues.delete(pk);
          fail(error);
          list.refresh(); // kembalikan ke jumlah yang tersimpan di server
        },
      );
  }

  function syncCard(pk, html, focusValue) {
    const old = document.getElementById(`dc-item-${pk}`);
    if (!old || !html) return;
    const hadFocus = old.contains(document.activeElement);
    const card = htmlToElement(html);
    old.replaceWith(card);
    if (hadFocus) {
      const same = card.querySelector(`button[name="delta"][value="${focusValue}"]`);
      if (same && !same.disabled) same.focus();
    }
  }

  // ---------- Sudah diolah / Kembalikan, dan Hapus: kartu langsung keluar dari daftar ----------
  async function removeOptimistically(form, { countChanges }) {
    const card = form.closest("[data-dc-item]");
    const restore = ui.removeCard(card);
    ui.bumpCounts(countChanges);
    try {
      const data = ensureOk(await send(form.action, { method: "POST", body: new FormData(form) }));
      ui.setCounts(data.counts); // angka pasti dari server
      ui.toast(data.message, data.tone);
      if (ui.cardsLeft() === 0) list.refresh(); // tampilkan keadaan kosong yang sesuai
    } catch (error) {
      restore();
      ui.bumpCounts(Object.fromEntries(Object.entries(countChanges).map(([k, v]) => [k, -v])));
      fail(error);
    }
  }

  function toggleResurrect(form) {
    const status = form.closest("[data-dc-item]").dataset.dcStatusKey;
    const countChanges = status === "RESURRECTED" ? { RESURRECTED: -1 } : { [status]: -1, RESURRECTED: +1 };
    return removeOptimistically(form, { countChanges });
  }

  function armDelete(form) {
    const button = form.querySelector("button");
    form.dataset.armed = "1";
    button.dataset.label = button.textContent;
    button.textContent = "Yakin hapus?";
    button.classList.add("is-armed");
    setTimeout(() => {
      if (!form.isConnected || !form.dataset.armed) return;
      delete form.dataset.armed;
      button.textContent = button.dataset.label;
      button.classList.remove("is-armed");
    }, 3000);
  }

  function remove(form) {
    if (!form.dataset.armed) return armDelete(form); // klik pertama hanya mengonfirmasi
    delete form.dataset.armed;
    const status = form.closest("[data-dc-item]").dataset.dcStatusKey;
    return removeOptimistically(form, { countChanges: { [status]: -1 } });
  }

  // ---------- Isi data contoh (dibuat server, jadi tidak optimistis) ----------
  async function seed(form) {
    if (form.dataset.busy) return;
    form.dataset.busy = "1";
    try {
      const data = ensureOk(await send(form.action, { method: "POST", body: new FormData(form) }));
      ui.toast(data.message, data.tone);
      await list.refresh();
    } catch (error) {
      fail(error);
    } finally {
      delete form.dataset.busy;
    }
  }

  return {
    quantity: changeQuantity,
    resurrect: toggleResurrect,
    delete: remove,
    seed,
  };
}
