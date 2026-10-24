from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from death_clock.models import PantryItem, Storage
from graveyard.models import (
    CARBON_FACTORS_PER_KG, Category, DisposalReason, GraveyardItem, Unit,
)

User = get_user_model()


class GraveyardItemModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='adam_necro',
            password='Password123!',
        )
        self.today = timezone.localdate()

    def test_create_graveyard_item_full(self):
        """Memvalidasi pembuatan GraveyardItem dengan seluruh field terisi."""
        item = GraveyardItem.objects.create(
            user=self.user,
            name='Susu UHT Full Cream',
            category=Category.DAIRY,
            reason=DisposalReason.EXPIRED,
            notes='Terlupa di bagian belakang kulkas bersama',
            expiry_date=self.today - timedelta(days=2),
            disposed_at=self.today,
            quantity=2,
            unit=Unit.LITER,
            weight_g=Decimal('2000.00'),
            estimated_loss=Decimal('42000.00'),
        )

        self.assertEqual(GraveyardItem.objects.count(), 1)
        self.assertEqual(item.user, self.user)
        self.assertEqual(item.name, 'Susu UHT Full Cream')
        self.assertEqual(item.category, Category.DAIRY)
        self.assertEqual(item.reason, DisposalReason.EXPIRED)
        self.assertEqual(item.quantity, 2)
        self.assertEqual(item.unit, Unit.LITER)
        self.assertEqual(item.weight_g, Decimal('2000.00'))
        self.assertEqual(item.estimated_loss, Decimal('42000.00'))
        self.assertEqual(item.disposed_at, self.today)
        self.assertEqual(item.expiry_date, self.today - timedelta(days=2))

    def test_default_values(self):
        """Memvalidasi nilai default field saat dibuat hanya dengan field wajib."""
        item = GraveyardItem.objects.create(
            user=self.user,
            name='Bayam Layu',
        )

        self.assertEqual(item.category, Category.OTHER)
        self.assertEqual(item.reason, DisposalReason.EXPIRED)
        self.assertEqual(item.quantity, 1)
        self.assertEqual(item.unit, Unit.PIECE)
        self.assertEqual(item.weight_g, Decimal('0.00'))
        self.assertEqual(item.estimated_loss, Decimal('0.00'))
        self.assertEqual(item.notes, '')
        self.assertIsNone(item.expiry_date)
        self.assertEqual(item.disposed_at, self.today)

    def test_str_representation(self):
        """Memvalidasi method __str__ GraveyardItem."""
        item = GraveyardItem.objects.create(
            user=self.user,
            name='Daging Ayam',
            category=Category.MEAT,
            reason=DisposalReason.SPOILED_EARLY,
        )
        self.assertIn('Daging Ayam', str(item))
        self.assertIn('Daging & Protein', str(item))
        self.assertIn('Membusuk sebelum tanggal kedaluwarsa', str(item))

    def test_effective_weight_and_carbon_calculations(self):
        """Memvalidasi kalkulasi berat efektif dan estimasi emisi karbon (CO2e)."""
        # Kasus 1: Berat manual diisi (1500 gram daging sapi)
        meat_item = GraveyardItem.objects.create(
            user=self.user,
            name='Daging Cincang',
            category=Category.MEAT,
            weight_g=Decimal('1500.00'),
        )
        self.assertEqual(meat_item.effective_weight_grams, Decimal('1500.00'))
        self.assertEqual(meat_item.effective_weight_kg, Decimal('1.50'))
        expected_meat_carbon = (Decimal('1.50') * CARBON_FACTORS_PER_KG[Category.MEAT]).quantize(Decimal('0.01'))
        self.assertEqual(meat_item.estimated_carbon_kg, expected_meat_carbon)

        # Kasus 2: Berat manual tidak diisi (menggunakan perkiraan unit default)
        veg_item = GraveyardItem.objects.create(
            user=self.user,
            name='Wortel',
            category=Category.VEG,
            quantity=2,
            unit=Unit.PIECE,
            weight_g=Decimal('0.00'),
        )
        self.assertEqual(veg_item.effective_weight_grams, Decimal('300.00'))
        self.assertEqual(veg_item.effective_weight_kg, Decimal('0.30'))
        expected_veg_carbon = (Decimal('0.30') * CARBON_FACTORS_PER_KG[Category.VEG]).quantize(Decimal('0.01'))
        self.assertEqual(veg_item.estimated_carbon_kg, expected_veg_carbon)

    def test_queryset_analytics_aggregations(self):
        """Memvalidasi method agregasi analitik total_loss dan total_weight_kg pada QuerySet."""
        other_user = User.objects.create_user(username='other_user', password='Password123!')

        GraveyardItem.objects.create(
            user=self.user,
            name='Susu',
            category=Category.DAIRY,
            weight_g=Decimal('1000.00'),
            estimated_loss=Decimal('25000.00'),
        )
        GraveyardItem.objects.create(
            user=self.user,
            name='Tempe',
            category=Category.MEAT,
            weight_g=Decimal('500.00'),
            estimated_loss=Decimal('8000.00'),
        )
        GraveyardItem.objects.create(
            user=other_user,
            name='Beras',
            category=Category.GRAIN,
            weight_g=Decimal('5000.00'),
            estimated_loss=Decimal('75000.00'),
        )

        user_items = GraveyardItem.objects.for_user(self.user)
        self.assertEqual(user_items.count(), 2)
        self.assertEqual(user_items.total_loss(), Decimal('33000.00'))
        self.assertEqual(user_items.total_weight_kg(), Decimal('1.50'))

    def test_to_dict_method(self):
        """Memvalidasi fungsi to_dict untuk respon API / JSON serialisasi."""
        item = GraveyardItem.objects.create(
            user=self.user,
            name='Roti Tawar',
            category=Category.GRAIN,
            reason=DisposalReason.MOLD,
            expiry_date=date(2026, 10, 15),
            disposed_at=date(2026, 10, 18),
            quantity=1,
            unit=Unit.PACK,
            weight_g=Decimal('250.00'),
            estimated_loss=Decimal('16000.00'),
            notes='Tumbuh jamur hijau di beberapa helai roti',
        )

        data = item.to_dict()
        self.assertEqual(data['id'], item.pk)
        self.assertEqual(data['name'], 'Roti Tawar')
        self.assertEqual(data['category'], 'GRAIN')
        self.assertEqual(data['category_label'], 'Biji-bijian & Makanan Kering')
        self.assertEqual(data['reason'], 'MOLD')
        self.assertEqual(data['reason_label'], 'Berjamur / terkontaminasi')
        self.assertEqual(data['expiry_date'], '2026-10-15')
        self.assertEqual(data['disposed_at'], '2026-10-18')
        self.assertEqual(data['estimated_loss'], 16000.0)
        self.assertEqual(data['weight_g'], 250.0)
        self.assertIn('estimated_carbon_kg', data)

    def test_cascade_delete_user(self):
        """Memvalidasi penghapusan user akan menghapus data graveyard miliknya."""
        GraveyardItem.objects.create(
            user=self.user,
            name='Ikan Tongkol',
            category=Category.MEAT,
        )
        self.assertEqual(GraveyardItem.objects.filter(user=self.user).count(), 1)
        self.user.delete()
        self.assertEqual(GraveyardItem.objects.count(), 0)


class GraveyardViewTest(TestCase):
    def setUp(self):
        self.password = 'Password123!'
        self.user = User.objects.create_user(
            username='adam_necro',
            password=self.password,
        )
        self.other_user = User.objects.create_user(
            username='zombie_rival',
            password=self.password,
        )
        self.today = timezone.localdate()
        self.list_url = reverse('graveyard:graveyard_list')
        self.json_url = reverse('graveyard:graveyard_json')

    # ---------- Autentikasi ----------
    def test_views_require_authentication(self):
        """Alur autentikasi sama dengan Death Clock: halaman tamu, redirect login, atau 401 JSON."""
        # Tamu membuka daftar -> halaman pengenalan modul + tombol masuk dengan ?next=
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'graveyard/guest.html')
        self.assertContains(response, f"{reverse('main:login')}?next={self.list_url}")

        # ?format=json tanpa login -> 401 JSON
        self.assertEqual(self.client.get(self.list_url, {'format': 'json'}).status_code, 401)

        # Akses AJAX -> 401 JSON
        ajax_resp = self.client.get(self.list_url, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(ajax_resp.status_code, 401)
        self.assertFalse(ajax_resp.json()['ok'])

        # Akses JSON endpoint -> 401 JSON
        json_resp = self.client.get(self.json_url)
        self.assertEqual(json_resp.status_code, 401)
        self.assertFalse(json_resp.json()['ok'])

        # Move endpoint tanpa login -> 302 ke halaman masuk, lalu kembali ke halaman asal
        move_url = reverse('graveyard:move_from_death_clock', args=[999])
        self.assertRedirects(
            self.client.get(move_url), f"{reverse('main:login')}?next={move_url}", fetch_redirect_response=False
        )
        self.assertEqual(self.client.post(move_url).status_code, 302)

        # Delete endpoint tanpa login -> 302
        del_url = reverse('graveyard:graveyard_delete', args=[999])
        self.assertEqual(self.client.post(del_url).status_code, 302)

    # ---------- Endpoint 1: List & Agregasi Analitik ----------
    def test_graveyard_list_and_analytics_aggregation(self):
        """Memvalidasi query daftar item dan akurasi agregasi analitik limbah pengguna."""
        self.client.login(username='adam_necro', password=self.password)

        # 1. Buat 2 item bulan ini
        GraveyardItem.objects.create(
            user=self.user,
            name='Susu UHT Basi',
            category=Category.DAIRY,
            reason=DisposalReason.EXPIRED,
            estimated_loss=Decimal('25000.00'),
            weight_g=Decimal('1000.00'),
            disposed_at=self.today,
        )
        GraveyardItem.objects.create(
            user=self.user,
            name='Keju Berjamur',
            category=Category.DAIRY,
            reason=DisposalReason.MOLD,
            estimated_loss=Decimal('30000.00'),
            weight_g=Decimal('250.00'),
            disposed_at=self.today,
        )

        # 2. Buat 1 item bulan lalu (tidak masuk hitungan bulan ini)
        past_date = self.today.replace(day=1) - timedelta(days=5)
        GraveyardItem.objects.create(
            user=self.user,
            name='Kangkung Layu',
            category=Category.VEG,
            reason=DisposalReason.FORGOTTEN,
            estimated_loss=Decimal('5000.00'),
            weight_g=Decimal('200.00'),
            disposed_at=past_date,
        )

        # 3. Item milik pengguna lain (harus terisolasi, tidak boleh ikut terhitung)
        GraveyardItem.objects.create(
            user=self.other_user,
            name='Daging Busuk Rival',
            category=Category.MEAT,
            estimated_loss=Decimal('999999.00'),
            weight_g=Decimal('10000.00'),
            disposed_at=self.today,
        )

        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'graveyard/graveyard_list.html')
        self.assertTemplateUsed(response, 'base.html')

        analytics = response.context['analytics']
        # Validasi total item busuk bulan ini (hanya 2 item)
        self.assertEqual(analytics['total_this_month'], 2)
        self.assertEqual(analytics['loss_this_month'], 55000.0)

        # Validasi kategori paling sering terbuang (DAIRY dengan 2 item vs VEG 1 item)
        self.assertIsNotNone(analytics['top_category'])
        self.assertEqual(analytics['top_category']['code'], 'DAIRY')
        self.assertEqual(analytics['top_category']['label'], 'Produk Olahan Susu')
        self.assertEqual(analytics['top_category']['count'], 2)

        # Validasi total akumulasi
        self.assertEqual(analytics['total_items'], 3)
        self.assertEqual(analytics['total_loss'], 60000.0)

        # Validasi isolasi data: item pengguna lain tidak muncul di context atau html
        items = response.context['items']
        self.assertEqual(items.count(), 3)
        self.assertNotContains(response, 'Daging Busuk Rival')

    def test_graveyard_list_empty_state_analytics(self):
        """Memvalidasi agregasi analitik saat pengguna belum memiliki riwayat pembuangan."""
        self.client.login(username='adam_necro', password=self.password)

        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, 200)
        analytics = response.context['analytics']
        self.assertEqual(analytics['total_this_month'], 0)
        self.assertEqual(analytics['total_items'], 0)
        self.assertIsNone(analytics['top_category'])
        self.assertContains(response, 'Graveyard Masih Kosong!')

    def test_graveyard_list_search_and_filter(self):
        """Memvalidasi query penyaringan berdasarkan kategori, alasan, dan kata kunci."""
        self.client.login(username='adam_necro', password=self.password)

        GraveyardItem.objects.create(
            user=self.user,
            name='Bayam Hijau',
            category=Category.VEG,
            reason=DisposalReason.EXPIRED,
        )
        GraveyardItem.objects.create(
            user=self.user,
            name='Susu UHT',
            category=Category.DAIRY,
            reason=DisposalReason.MOLD,
        )

        # Saring kategori VEG
        resp_veg = self.client.get(self.list_url, {'category': 'VEG'})
        self.assertEqual(resp_veg.context['items'].count(), 1)
        veg_item_names = [item.name for item in resp_veg.context['items']]
        self.assertIn('Bayam Hijau', veg_item_names)
        self.assertNotIn('Susu UHT', veg_item_names)

        # Saring kata kunci 'Susu'
        resp_q = self.client.get(self.list_url, {'q': 'Susu'})
        self.assertEqual(resp_q.context['items'].count(), 1)
        q_item_names = [item.name for item in resp_q.context['items']]
        self.assertIn('Susu UHT', q_item_names)
        self.assertNotIn('Bayam Hijau', q_item_names)

    def test_graveyard_json_endpoint(self):
        """Memvalidasi endpoint API JSON mengembalikan data analitik dan items yang valid."""
        self.client.login(username='adam_necro', password=self.password)

        GraveyardItem.objects.create(
            user=self.user,
            name='Apel Busuk',
            category=Category.VEG,
            reason=DisposalReason.EXPIRED,
            estimated_loss=Decimal('10000.00'),
            disposed_at=self.today,
        )

        response = self.client.get(self.json_url)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['ok'])
        self.assertEqual(data['count'], 1)
        self.assertEqual(data['analytics']['total_this_month'], 1)
        self.assertEqual(len(data['items']), 1)
        self.assertEqual(data['items'][0]['name'], 'Apel Busuk')

    # ---------- Endpoint 2: Move from Death Clock to Graveyard ----------
    def test_move_from_death_clock_get_form(self):
        """Memvalidasi GET ke endpoint pemindahan menampilkan halaman konfirmasi."""
        self.client.login(username='adam_necro', password=self.password)

        pantry_item = PantryItem.objects.create(
            user=self.user,
            name='Tahu Putih',
            category=Category.MEAT,
            quantity=2,
            unit=Unit.PIECE,
            storage=Storage.FRIDGE,
            purchase_date=self.today - timedelta(days=5),
            expiry_date=self.today - timedelta(days=1),
        )

        url = reverse('graveyard:move_from_death_clock', args=[pantry_item.pk])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'graveyard/move_form.html')
        self.assertEqual(response.context['pantry_item'], pantry_item)
        self.assertContains(response, 'Tahu Putih')

    def test_move_from_death_clock_post_standard(self):
        """Memvalidasi POST memindahkan item dari Death Clock ke Graveyard secara penuh."""
        self.client.login(username='adam_necro', password=self.password)

        pantry_item = PantryItem.objects.create(
            user=self.user,
            name='Yogurt Basi',
            category=Category.DAIRY,
            quantity=2,
            unit=Unit.PACK,
            storage=Storage.FRIDGE,
            purchase_date=self.today - timedelta(days=10),
            expiry_date=self.today - timedelta(days=2),
            notes='Lupa diminum',
        )

        url = reverse('graveyard:move_from_death_clock', args=[pantry_item.pk])
        post_data = {
            'reason': DisposalReason.EXPIRED,
            'estimated_loss': '24000.00',
            'weight_g': '300.00',
            'notes': 'Sudah mengental aneh dan berbau kecut',
            'disposed_at': str(self.today),
        }

        response = self.client.post(url, post_data)
        # Harus redirect ke daftar graveyard
        self.assertRedirects(response, self.list_url)

        # Bahan di death_clock harus TERHAPUS
        self.assertFalse(PantryItem.objects.filter(pk=pantry_item.pk).exists())

        # Bahan di graveyard harus TERCIPTA dengan data yang sesuai
        graveyard_item = GraveyardItem.objects.filter(user=self.user, name='Yogurt Basi').first()
        self.assertIsNotNone(graveyard_item)
        self.assertEqual(graveyard_item.category, Category.DAIRY)
        self.assertEqual(graveyard_item.reason, DisposalReason.EXPIRED)
        self.assertEqual(graveyard_item.quantity, 2)
        self.assertEqual(graveyard_item.unit, Unit.PACK)
        self.assertEqual(graveyard_item.estimated_loss, Decimal('24000.00'))
        self.assertEqual(graveyard_item.weight_g, Decimal('300.00'))
        self.assertEqual(graveyard_item.notes, 'Sudah mengental aneh dan berbau kecut')
        self.assertEqual(graveyard_item.disposed_at, self.today)

    def test_move_from_death_clock_post_ajax(self):
        """Memvalidasi pemindahan bahan via AJAX merespons 201 JSON."""
        self.client.login(username='adam_necro', password=self.password)

        pantry_item = PantryItem.objects.create(
            user=self.user,
            name='Bayam Busuk',
            category=Category.VEG,
            quantity=1,
            unit=Unit.BUNCH,
            storage=Storage.FRIDGE,
            purchase_date=self.today - timedelta(days=6),
            expiry_date=self.today - timedelta(days=3),
        )

        url = reverse('graveyard:move_from_death_clock', args=[pantry_item.pk])
        response = self.client.post(
            url,
            {'reason': DisposalReason.SPOILED_EARLY, 'estimated_loss': '6000'},
            HTTP_X_REQUESTED_WITH='XMLHttpRequest',
        )

        self.assertEqual(response.status_code, 201)
        data = response.json()
        self.assertTrue(data['ok'])
        self.assertIn('Bayam Busuk', data['message'])
        self.assertEqual(data['graveyard_item']['name'], 'Bayam Busuk')
        self.assertEqual(data['graveyard_item']['estimated_loss'], 6000.0)

        # Terhapus dari Pantry
        self.assertFalse(PantryItem.objects.filter(pk=pantry_item.pk).exists())
        # Masuk ke Graveyard
        self.assertTrue(GraveyardItem.objects.filter(user=self.user, name='Bayam Busuk').exists())

    def test_move_ignores_external_next(self):
        """Tujuan redirect dari input pengguna hanya boleh ke situs sendiri."""
        item = PantryItem.objects.create(
            user=self.user,
            name='Tahu',
            category=Category.MEAT,
            quantity=1,
            unit=Unit.PIECE,
            storage=Storage.FRIDGE,
            purchase_date=self.today - timedelta(days=5),
            expiry_date=self.today - timedelta(days=1),
        )
        self.client.login(username='adam_necro', password=self.password)
        response = self.client.post(
            reverse('graveyard:move_from_death_clock', args=[item.pk]),
            {'reason': 'EXPIRED', 'next': 'https://contoh-jahat.com/'},
        )
        self.assertRedirects(response, self.list_url, fetch_redirect_response=False)

    def _fresh_pantry_item(self):
        return PantryItem.objects.create(
            user=self.user,
            name='Tempe',
            category=Category.MEAT,
            quantity=1,
            unit=Unit.PIECE,
            storage=Storage.FRIDGE,
            purchase_date=self.today - timedelta(days=5),
            expiry_date=self.today - timedelta(days=1),
        )

    def test_move_rejects_amount_too_large_for_database(self):
        """Angka melebihi kolom database ditolak dengan pesan, bukan disimpan lalu bikin 500."""
        item = self._fresh_pantry_item()
        url = reverse('graveyard:move_from_death_clock', args=[item.pk])
        self.client.login(username='adam_necro', password=self.password)

        response = self.client.post(url, {'reason': 'EXPIRED', 'estimated_loss': '99999999999999', 'weight_g': '250'})
        self.assertEqual(response.status_code, 400)
        self.assertTemplateUsed(response, 'graveyard/move_form.html')
        self.assertContains(response, 'Estimasi kerugian terlalu besar', status_code=400)
        self.assertContains(response, 'value="250"', status_code=400)  # isian lain tidak hilang

        ajax = self.client.post(url, {'weight_g': '1000000000'}, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(ajax.status_code, 400)
        self.assertIn('Estimasi berat terlalu besar', ajax.json()['detail'])

        self.assertFalse(GraveyardItem.objects.filter(user=self.user).exists())
        self.assertTrue(PantryItem.objects.filter(pk=item.pk).exists())
        self.assertEqual(self.client.get(self.list_url).status_code, 200)

    def test_move_accepts_largest_amount_that_fits(self):
        item = self._fresh_pantry_item()
        self.client.login(username='adam_necro', password=self.password)
        self.client.post(
            reverse('graveyard:move_from_death_clock', args=[item.pk]),
            {'reason': 'EXPIRED', 'estimated_loss': '9999999999.99', 'weight_g': '99999999.99'},
        )
        self.assertEqual(GraveyardItem.objects.get(user=self.user).estimated_loss, Decimal('9999999999.99'))
        self.assertEqual(self.client.get(self.list_url).status_code, 200)

    def test_move_treats_nan_and_infinity_as_empty(self):
        item = self._fresh_pantry_item()
        self.client.login(username='adam_necro', password=self.password)
        self.client.post(
            reverse('graveyard:move_from_death_clock', args=[item.pk]),
            {'reason': 'EXPIRED', 'estimated_loss': 'NaN', 'weight_g': 'Infinity'},
        )
        buried = GraveyardItem.objects.get(user=self.user)
        self.assertEqual((buried.estimated_loss, buried.weight_g), (Decimal('0.00'), Decimal('0.00')))

    def test_move_from_death_clock_other_user_item_404(self):
        """Memastikan pengguna tidak dapat memindahkan bahan milik orang lain (404 isolation)."""
        self.client.login(username='adam_necro', password=self.password)

        other_item = PantryItem.objects.create(
            user=self.other_user,
            name='Keju Mewah Milik Tetangga',
            category=Category.DAIRY,
            quantity=1,
            unit=Unit.PACK,
            storage=Storage.FRIDGE,
            purchase_date=self.today,
            expiry_date=self.today + timedelta(days=5),
        )

        url = reverse('graveyard:move_from_death_clock', args=[other_item.pk])
        response = self.client.post(url, {'reason': DisposalReason.EXPIRED})

        # Harus 404
        self.assertEqual(response.status_code, 404)
        # Item milik pengguna lain TIDAK boleh terhapus
        self.assertTrue(PantryItem.objects.filter(pk=other_item.pk).exists())
        # Tidak boleh ada item tercipta di Graveyard
        self.assertEqual(GraveyardItem.objects.count(), 0)

    # ---------- Endpoint 3: Delete Catatan Graveyard ----------
    def test_graveyard_delete_success_and_isolation(self):
        """Memvalidasi penghapusan catatan graveyard serta isolasi hak aksesnya."""
        self.client.login(username='adam_necro', password=self.password)

        item = GraveyardItem.objects.create(
            user=self.user,
            name='Catatan Salah',
            category=Category.OTHER,
        )
        other_item = GraveyardItem.objects.create(
            user=self.other_user,
            name='Catatan Orang Lain',
            category=Category.OTHER,
        )

        # 1. Hapus item sendiri
        del_url = reverse('graveyard:graveyard_delete', args=[item.pk])
        resp = self.client.post(del_url)
        self.assertRedirects(resp, self.list_url)
        self.assertFalse(GraveyardItem.objects.filter(pk=item.pk).exists())

        # 2. Coba hapus item milik orang lain -> 404
        other_del_url = reverse('graveyard:graveyard_delete', args=[other_item.pk])
        resp_other = self.client.post(other_del_url)
        self.assertEqual(resp_other.status_code, 404)
        self.assertTrue(GraveyardItem.objects.filter(pk=other_item.pk).exists())

    def test_graveyard_delete_ajax(self):
        """Memvalidasi penghapusan catatan graveyard via AJAX merespons 200 JSON."""
        self.client.login(username='adam_necro', password=self.password)

        item = GraveyardItem.objects.create(
            user=self.user,
            name='Catatan Dihapus via AJAX',
            category=Category.OTHER,
        )

        del_url = reverse('graveyard:graveyard_delete', args=[item.pk])
        resp = self.client.post(del_url, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data['ok'])
        self.assertIn('Catatan Dihapus via AJAX', data['message'])
        self.assertFalse(GraveyardItem.objects.filter(pk=item.pk).exists())


class GraveyardTemplateTagTest(TestCase):
    def test_rupiah_filter(self):
        from graveyard.templatetags.graveyard_tags import rupiah

        self.assertEqual(rupiah(12000), 'Rp 12.000')
        self.assertEqual(rupiah(55000.0), 'Rp 55.000')
        self.assertEqual(rupiah(1250000), 'Rp 1.250.000')
        self.assertEqual(rupiah(0), 'Rp 0')
        self.assertEqual(rupiah(''), 'Rp 0')
        self.assertEqual(rupiah(None), 'Rp 0')


class GraveyardWrappedTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='adam_wrapped',
            password='Password123!',
        )
        self.today = timezone.localdate()

    def test_item_epitaph_food_keywords(self):
        """Memvalidasi persona suara arwah (epitaph) untuk berbagai jenis makanan."""
        from graveyard.wrapped import get_item_epitaph

        cases = [
            ('Telur Ayam Negeri', 'sarapan berenergimu', 'Telur'),
            ('Susu UHT Cokelat', 'membuat tulangmu kuat', 'Susu Uht Cokelat'),
            ('Bayam Organik', 'laci bawah kulkas', 'Bayam Organik'),
            ('Daging Sapi Segar', 'Seekor nyawa dikorbankan', 'Daging Sapi Segar'),
            ('Nasi Goreng Sisa', 'Bulir-bulirku ditanam petani', 'Nasi Goreng Sisa'),
            ('Tahu Sutra', 'Sedikit jamur tumbuh', 'Tahu Sutra'),
            ('Apel Merah', 'Kemanisan alaminya kau abaikan', 'Apel Merah'),
        ]

        for name, expected_snippet, expected_author in cases:
            item = GraveyardItem(user=self.user, name=name, quantity=1, unit=Unit.PIECE)
            quote, author = get_item_epitaph(item)
            self.assertIn(expected_snippet, quote)
            self.assertIn(expected_author, author)

    def test_item_epitaph_reason_fallbacks(self):
        """Memvalidasi fallback kutipan arwah berbasis alasan pembuangan."""
        from graveyard.wrapped import get_item_epitaph

        item_forgotten = GraveyardItem(user=self.user, name='Item Misterius', reason=DisposalReason.FORGOTTEN)
        quote_f, _ = get_item_epitaph(item_forgotten)
        self.assertIn('menimbunku di balik tumpukan kulkas', quote_f)

        item_expired = GraveyardItem(user=self.user, name='Item Misterius', reason=DisposalReason.EXPIRED)
        quote_e, _ = get_item_epitaph(item_expired)
        self.assertIn('Tanggal kedaluwarsaku tertera jelas', quote_e)

        item_overcooked = GraveyardItem(user=self.user, name='Item Misterius', reason=DisposalReason.OVERCOOKED)
        quote_o, _ = get_item_epitaph(item_overcooked)
        self.assertIn('Kamu memasakku terlalu banyak', quote_o)

    def test_wrapped_empty_state(self):
        """Memvalidasi slide wrapped saat pengguna sama sekali belum punya item."""
        from graveyard.views import calculate_analytics
        from graveyard.wrapped import generate_haunting_wrapped

        items = GraveyardItem.objects.filter(user=self.user)
        analytics = calculate_analytics(items)
        slides = generate_haunting_wrapped(items, analytics)

        self.assertEqual(len(slides), 1)
        self.assertEqual(slides[0]['tag'], 'RUANG SUCI TANPA KUTUKAN')
        self.assertEqual(slides[0]['headline'], 'Lembah Graveyard Sunyi Senyap')

    def test_wrapped_cold_start_rekor_dosa_perdana(self):
        """Memvalidasi cold-start ketika ada item bulan ini tapi bulan lalu 0."""
        from graveyard.views import calculate_analytics
        from graveyard.wrapped import generate_haunting_wrapped

        GraveyardItem.objects.create(
            user=self.user,
            name='Telur Omega',
            category=Category.MEAT,
            disposed_at=self.today,
            estimated_loss=Decimal('10000.00'),
        )

        items = GraveyardItem.objects.filter(user=self.user)
        analytics = calculate_analytics(items)
        slides = generate_haunting_wrapped(items, analytics)

        tags = [s['tag'] for s in slides]
        self.assertIn('REKOR DOSA PERDANA', tags)
        self.assertIn('BISIKAN ARWAH PANGAN', tags)
        self.assertIn('PENYESALAN DOMPET', tags)

    def test_wrapped_trend_escalation(self):
        """Memvalidasi tren pemburukan limbah: bulan ini lebih banyak dibanding bulan lalu."""
        from graveyard.views import calculate_analytics
        from graveyard.wrapped import generate_haunting_wrapped

        # 1 item bulan lalu
        past_date = self.today.replace(day=1) - timedelta(days=5)
        GraveyardItem.objects.create(
            user=self.user,
            name='Item Lama',
            disposed_at=past_date,
        )
        # 3 item bulan ini
        for i in range(3):
            GraveyardItem.objects.create(
                user=self.user,
                name=f'Item Baru {i}',
                disposed_at=self.today,
            )

        items = GraveyardItem.objects.filter(user=self.user)
        analytics = calculate_analytics(items)
        slides = generate_haunting_wrapped(items, analytics)

        self.assertEqual(slides[0]['tag'], 'ESKALASI KUTUKAN')
        self.assertIn('+2 Lebih Banyak', slides[0]['stat_value'])

    def test_wrapped_trend_improvement(self):
        """Memvalidasi tren perbaikan limbah: bulan ini lebih sedikit dibanding bulan lalu."""
        from graveyard.views import calculate_analytics
        from graveyard.wrapped import generate_haunting_wrapped

        # 3 item bulan lalu
        past_date = self.today.replace(day=1) - timedelta(days=5)
        for i in range(3):
            GraveyardItem.objects.create(
                user=self.user,
                name=f'Item Lama {i}',
                disposed_at=past_date,
            )
        # 1 item bulan ini
        GraveyardItem.objects.create(
            user=self.user,
            name='Item Baru',
            disposed_at=self.today,
        )

        items = GraveyardItem.objects.filter(user=self.user)
        analytics = calculate_analytics(items)
        slides = generate_haunting_wrapped(items, analytics)

        self.assertEqual(slides[0]['tag'], 'ARWAH MULAI TENANG')
        self.assertIn('-2 Bahan', slides[0]['stat_value'])

    def test_wrapped_financial_guilt_analogies(self):
        """Memvalidasi analogi finansial porsi ayam geprek vs es teh."""
        from graveyard.views import calculate_analytics
        from graveyard.wrapped import generate_haunting_wrapped

        # Kasus geprek (>= 15.000)
        GraveyardItem.objects.create(
            user=self.user,
            name='Daging Wagyu Sisa',
            estimated_loss=Decimal('45000.00'),
            disposed_at=self.today,
        )
        items = GraveyardItem.objects.filter(user=self.user)
        analytics = calculate_analytics(items)
        slides = generate_haunting_wrapped(items, analytics)
        fin_slide = next(s for s in slides if s['tag'] == 'PENYESALAN DOMPET')
        self.assertIn('3 porsi nasi ayam geprek', fin_slide['detail'])




from graveyard.forms import GraveyardItemForm, GraveyardMoveForm, LOSS_MAX, WEIGHT_MAX


class GraveyardFormTest(TestCase):
    def setUp(self):
        self.today = timezone.localdate()

    def test_item_form_valid(self):
        form_data = {
            'name': 'Sawi Putih',
            'category': Category.VEG,
            'reason': DisposalReason.SPOILED_EARLY,
            'quantity': 2,
            'unit': Unit.PIECE,
            'weight_g': '400.00',
            'estimated_loss': '10000.00',
            'disposed_at': str(self.today),
            'expiry_date': str(self.today - timedelta(days=1)),
            'notes': 'Layu kecokelatan',
        }
        form = GraveyardItemForm(data=form_data)
        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.cleaned_data['name'], 'Sawi Putih')

    def test_item_form_blank_name_invalid(self):
        form = GraveyardItemForm(data={'name': '   ', 'category': Category.VEG})
        self.assertFalse(form.is_valid())
        self.assertIn('name', form.errors)

    def test_item_form_quantity_min_one(self):
        form = GraveyardItemForm(data={'name': 'Roti', 'quantity': 0})
        self.assertFalse(form.is_valid())
        self.assertIn('quantity', form.errors)

    def test_item_form_negative_numbers(self):
        form = GraveyardItemForm(data={'name': 'Roti', 'quantity': 1, 'estimated_loss': '-500', 'weight_g': '-10'})
        self.assertFalse(form.is_valid())
        self.assertIn('estimated_loss', form.errors)
        self.assertIn('weight_g', form.errors)

    def test_item_form_overflow_limits(self):
        form = GraveyardItemForm(data={
            'name': 'Roti',
            'quantity': 1,
            'estimated_loss': str(LOSS_MAX + 100),
            'weight_g': str(WEIGHT_MAX + 100),
        })
        self.assertFalse(form.is_valid())
        self.assertIn('estimated_loss', form.errors)
        self.assertIn('weight_g', form.errors)

    def test_item_form_disposed_at_future_rejected(self):
        form = GraveyardItemForm(data={
            'name': 'Roti',
            'quantity': 1,
            'disposed_at': str(self.today + timedelta(days=2)),
        })
        self.assertFalse(form.is_valid())
        self.assertIn('disposed_at', form.errors)

    def test_move_form_valid_and_clean(self):
        form_data = {
            'reason': DisposalReason.EXPIRED,
            'estimated_loss': '15000.00',
            'weight_g': '250.00',
            'disposed_at': str(self.today),
            'notes': 'Terlupa',
        }
        form = GraveyardMoveForm(data=form_data)
        self.assertTrue(form.is_valid(), form.errors)


class GraveyardCRUDViewsTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='adam_crud', password='Password123!')
        self.other_user = User.objects.create_user(username='other_crud', password='Password123!')
        self.password = 'Password123!'
        self.today = timezone.localdate()

    def test_create_view_requires_login(self):
        url = reverse('graveyard:graveyard_create')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)

        ajax = self.client.get(url, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(ajax.status_code, 401)

    def test_create_view_get(self):
        self.client.login(username='adam_crud', password=self.password)
        url = reverse('graveyard:graveyard_create')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'graveyard/item_form.html')
        self.assertIn('form', response.context)

    def test_create_view_post_standard(self):
        self.client.login(username='adam_crud', password=self.password)
        url = reverse('graveyard:graveyard_create')
        post_data = {
            'name': 'Alpukat Busuk',
            'category': Category.VEG,
            'reason': DisposalReason.SPOILED_EARLY,
            'quantity': 3,
            'unit': Unit.PIECE,
            'weight_g': '450.00',
            'estimated_loss': '25000.00',
            'disposed_at': str(self.today),
            'notes': 'Menghitam di bagian dalam',
        }
        response = self.client.post(url, post_data)
        self.assertRedirects(response, reverse('graveyard:graveyard_list'))
        created = GraveyardItem.objects.filter(user=self.user, name='Alpukat Busuk').first()
        self.assertIsNotNone(created)
        self.assertEqual(created.quantity, 3)
        self.assertEqual(created.estimated_loss, Decimal('25000.00'))

    def test_create_view_post_ajax(self):
        self.client.login(username='adam_crud', password=self.password)
        url = reverse('graveyard:graveyard_create')
        post_data = {
            'name': 'Keju Berjamur',
            'category': Category.DAIRY,
            'reason': DisposalReason.MOLD,
            'quantity': 1,
            'unit': Unit.PACK,
            'weight_g': '200.00',
            'estimated_loss': '30000.00',
            'disposed_at': str(self.today),
        }
        response = self.client.post(url, post_data, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(response.status_code, 201)
        data = response.json()
        self.assertTrue(data['ok'])
        self.assertEqual(data['graveyard_item']['name'], 'Keju Berjamur')
        self.assertTrue(GraveyardItem.objects.filter(user=self.user, name='Keju Berjamur').exists())

    def test_create_view_post_invalid(self):
        self.client.login(username='adam_crud', password=self.password)
        url = reverse('graveyard:graveyard_create')
        response = self.client.post(url, {'name': ''})
        self.assertEqual(response.status_code, 400)
        self.assertTemplateUsed(response, 'graveyard/item_form.html')

        ajax = self.client.post(url, {'name': ''}, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(ajax.status_code, 400)
        self.assertFalse(ajax.json()['ok'])
        self.assertIn('name', ajax.json()['errors'])

    def test_edit_view_requires_login(self):
        item = GraveyardItem.objects.create(user=self.user, name='Tomat')
        url = reverse('graveyard:graveyard_edit', args=[item.pk])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)

    def test_edit_view_other_user_item_404(self):
        item = GraveyardItem.objects.create(user=self.other_user, name='Daging')
        self.client.login(username='adam_crud', password=self.password)
        url = reverse('graveyard:graveyard_edit', args=[item.pk])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)

        post_resp = self.client.post(url, {'name': 'Hack'})
        self.assertEqual(post_resp.status_code, 404)

    def test_edit_view_get(self):
        item = GraveyardItem.objects.create(
            user=self.user,
            name='Kangkung Layu',
            category=Category.VEG,
            reason=DisposalReason.FORGOTTEN,
            quantity=1,
            unit=Unit.BUNCH,
            estimated_loss=Decimal('5000.00'),
        )
        self.client.login(username='adam_crud', password=self.password)
        url = reverse('graveyard:graveyard_edit', args=[item.pk])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'graveyard/item_form.html')
        self.assertEqual(response.context['item'], item)
        self.assertContains(response, 'Kangkung Layu')

    def test_edit_view_post_standard(self):
        item = GraveyardItem.objects.create(
            user=self.user,
            name='Kangkung Layu',
            category=Category.VEG,
            reason=DisposalReason.FORGOTTEN,
            quantity=1,
            unit=Unit.BUNCH,
            estimated_loss=Decimal('5000.00'),
            disposed_at=self.today,
        )
        self.client.login(username='adam_crud', password=self.password)
        url = reverse('graveyard:graveyard_edit', args=[item.pk])
        post_data = {
            'name': 'Kangkung Sangat Layu',
            'category': Category.VEG,
            'reason': DisposalReason.SMELL_TEXTURE,
            'quantity': 2,
            'unit': Unit.BUNCH,
            'weight_g': '400.00',
            'estimated_loss': '10000.00',
            'disposed_at': str(self.today),
            'notes': 'Koreksi kuantitas dan harga',
        }
        response = self.client.post(url, post_data)
        self.assertRedirects(response, reverse('graveyard:graveyard_list'))

        item.refresh_from_db()
        self.assertEqual(item.name, 'Kangkung Sangat Layu')
        self.assertEqual(item.reason, DisposalReason.SMELL_TEXTURE)
        self.assertEqual(item.quantity, 2)
        self.assertEqual(item.estimated_loss, Decimal('10000.00'))
        self.assertEqual(item.notes, 'Koreksi kuantitas dan harga')

    def test_edit_view_post_ajax(self):
        item = GraveyardItem.objects.create(
            user=self.user,
            name='Kangkung',
            category=Category.VEG,
            reason=DisposalReason.FORGOTTEN,
            quantity=1,
            unit=Unit.BUNCH,
            estimated_loss=Decimal('5000.00'),
            disposed_at=self.today,
        )
        self.client.login(username='adam_crud', password=self.password)
        url = reverse('graveyard:graveyard_edit', args=[item.pk])
        post_data = {
            'name': 'Kangkung Organik',
            'category': Category.VEG,
            'reason': DisposalReason.EXPIRED,
            'quantity': 1,
            'unit': Unit.BUNCH,
            'weight_g': '200.00',
            'estimated_loss': '7000.00',
            'disposed_at': str(self.today),
        }
        response = self.client.post(url, post_data, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['ok'])
        self.assertEqual(data['graveyard_item']['name'], 'Kangkung Organik')
        self.assertEqual(data['graveyard_item']['estimated_loss'], 7000.0)

    def test_edit_view_post_invalid(self):
        item = GraveyardItem.objects.create(user=self.user, name='Kangkung')
        self.client.login(username='adam_crud', password=self.password)
        url = reverse('graveyard:graveyard_edit', args=[item.pk])
        response = self.client.post(url, {'name': ''})
        self.assertEqual(response.status_code, 400)

        ajax = self.client.post(url, {'name': ''}, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(ajax.status_code, 400)
        self.assertFalse(ajax.json()['ok'])
    def test_graveyard_list_ajax_search_and_filter(self):
        """Memvalidasi pemfilteran live AJAX mengembalikan partial html dan count yang terfilter."""
        self.client.login(username='adam_crud', password=self.password)
        GraveyardItem.objects.create(
            user=self.user,
            name='Bayam Layu',
            category=Category.VEG,
            reason=DisposalReason.FORGOTTEN,
            estimated_loss=Decimal('5000.00'),
        )
        GraveyardItem.objects.create(
            user=self.user,
            name='Daging Sapi Busuk',
            category=Category.MEAT,
            reason=DisposalReason.EXPIRED,
            estimated_loss=Decimal('50000.00'),
        )

        # Cari "Bayam" via AJAX
        response = self.client.get(
            reverse('graveyard:graveyard_list'),
            {'q': 'Bayam'},
            HTTP_X_REQUESTED_WITH='XMLHttpRequest',
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['ok'])
        self.assertEqual(data['count'], 1)
        self.assertIn('html', data)
        self.assertIn('Bayam Layu', data['html'])
        self.assertNotIn('Daging Sapi Busuk', data['html'])

        # Filter Kategori "MEAT" via AJAX
        resp_meat = self.client.get(
            reverse('graveyard:graveyard_list'),
            {'category': Category.MEAT},
            HTTP_X_REQUESTED_WITH='XMLHttpRequest',
        )
        self.assertEqual(resp_meat.status_code, 200)
        data_meat = resp_meat.json()
        self.assertEqual(data_meat['count'], 1)
        self.assertIn('Daging Sapi Busuk', data_meat['html'])
        self.assertNotIn('Bayam Layu', data_meat['html'])

