# Pemeriksaan pribadi (Playwright)

Folder ini di-gitignore: hanya untuk mengecek situs (termasuk modul teman) di laptop sendiri.

```bash
pip install -r playwright_checks/requirements.txt
playwright install chromium                                    # sekali saja
python manage.py test playwright_checks -p "check_*.py"        # semua
python manage.py test playwright_checks.check_graveyard -p "check_*.py"   # satu modul
```

PowerShell, untuk melihat browsernya: `$env:PLAYWRIGHT_HEADED=1` lalu jalankan perintah di atas.

| File | Modul |
| :--- | :--- |
| `check_smoke.py` | Semua halaman (desktop, HP 375 & 320 px, tamu & pengguna), akun, Dead Drop |
| `check_death_clock.py` | Death Clock (Evan) |
| `check_recipe_alchemist.py` | Recipe Alchemist (Nuno), Spoonacular di-mock |
| `check_graveyard.py` | Graveyard (Adam) |
| `check_grimoire.py` | Grimoire (Syarif) |

Test yang gagal = temuan. Test bernama `test_readme_*` / `test_ketentuan_*` mengecek janji README atau
ketentuan midterm.pdf yang belum dikerjakan. Tangkapan layar saat gagal ada di `test-results/`.

Nama file berawalan `check_` supaya `python manage.py test` biasa dan coverage tim tidak ikut menjalankannya.
