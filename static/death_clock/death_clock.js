/* =========================================================
   Pantry Death Clock: titik masuk JavaScript (ES module).

   modules/api.js      fetch + CSRF + jenis galat
   modules/ui.js       toast, angka ringkasan, kartu keluar/masuk
   modules/list.js     daftar & filter (AJAX)
   modules/modal.js    modal tambah / tambah massal / ubah
   modules/actions.js  aksi cepat dengan optimistic UI (jumlah, sudah diolah, hapus, data contoh)

   Progressive enhancement: tanpa JavaScript semua form tetap jalan lewat redirect biasa.
   HTML dari server sudah di-escape Django, jadi aman dimasukkan dengan innerHTML;
   pesan teks memakai textContent.
   ========================================================= */
import { createActions } from "./modules/actions.js";
import { createClient } from "./modules/api.js";
import { createList } from "./modules/list.js";
import { createModal } from "./modules/modal.js";
import { createUi } from "./modules/ui.js";

const root = document.querySelector("[data-dc-root]");

if (root) {
  const send = createClient(root.querySelector('input[name="csrfmiddlewaretoken"]').value);
  const ui = createUi(root);
  const list = createList({ root, send, ui });
  const modal = createModal({ root, send, ui, onSaved: list.refresh });
  const actions = createActions({ send, ui, list });

  root.addEventListener("click", (event) => {
    const tile = event.target.closest("[data-dc-status]");
    if (tile) {
      event.preventDefault();
      list.toggleStatus(tile.dataset.dcStatus);
      return;
    }
    if (event.target.closest("[data-dc-reset]")) {
      event.preventDefault();
      list.clearFilters();
      list.refresh();
      return;
    }
    const closer = event.target.closest("[data-dc-close]");
    if (closer && modal.contains(closer)) {
      event.preventDefault();
      modal.close();
      return;
    }
    const opener = event.target.closest("[data-dc-modal]");
    if (opener && modal.supported) {
      event.preventDefault();
      modal.open(opener.href, opener.dataset.dcModal);
    }
  });

  root.addEventListener("submit", (event) => {
    const form = event.target;
    if (form.hasAttribute("data-dc-form") && modal.contains(form)) {
      event.preventDefault();
      modal.submit(form);
      return;
    }
    const action = actions[form.dataset.dcAction];
    if (!action) return; // form filter ditangani list.js
    event.preventDefault();
    action(form, event.submitter);
  });
}
