"""Logika analitik naratif 'The Haunting Wrapped: Bisikan Arwah Pangan'.

Menghasilkan wawasan personal ala Spotify Wrapped berbasis data riil limbah pengguna:
- Komparasi tren bulan ini vs bulan lalu (lengkap dengan penanganan cold-start).
- Monolog arwah makanan ('The Voice of the Dead') berbasis nama/kategori bahan.
- Konversi kerugian uang ke padanan realitas anak kost (porsi ayam geprek / es teh).
- Peringatan emisi gas metana (CO₂e) dan kategori paling rentan busuk.
"""
from decimal import Decimal

from django.utils import timezone


def format_rupiah_short(amount):
    """Format angka ke format mata uang Rupiah ringkas."""
    try:
        num = int(round(Decimal(str(amount))))
        return f"Rp {num:,}".replace(',', '.')
    except Exception:
        return f"Rp {amount}"


def get_item_epitaph(item):
    """Menghasilkan kutipan personal dari bahan makanan berdasarkan nama, kategori, dan alasan pembuangan."""
    name_lower = (item.name or '').lower()
    qty_str = f"{item.quantity} {item.get_unit_display()}"

    # Lapis 1: Pencocokan kata kunci bahan pangan umum
    if any(k in name_lower for k in ['telur', 'egg']):
        quote = "Seharusnya aku menjadi sarapan berenergimu sebelum kuliah, tapi kamu membiarkanku membusuk di sudut kulkas."
        author = f"Arwah {qty_str} Telur"
    elif any(k in name_lower for k in ['susu', 'milk', 'uht', 'keju', 'cheese', 'yogurt']):
        quote = "Seharusnya aku membuat tulangmu kuat, tapi kamu memilih melupakanku hingga aku mengental dan berbau masam."
        author = f"Arwah {item.name.title()}"
    elif any(k in name_lower for k in ['bayam', 'kangkung', 'sawi', 'wortel', 'tomat', 'brokoli', 'sayur', 'selada']):
        quote = "Aku datang segar dari pasar untuk kesehatanmu, namun kau biarkan aku menghitam layu di laci bawah kulkas."
        author = f"Roh {item.name.title()}"
    elif any(k in name_lower for k in ['ayam', 'daging', 'sapi', 'ikan', 'udang', 'meat', 'beef', 'chicken', 'fish']):
        quote = "Seekor nyawa dikorbankan untuk hidangan ini, dan kamu mengakhiri pengorbanannya di tempat sampah."
        author = f"Arwah Penyesalan {item.name.title()}"
    elif any(k in name_lower for k in ['nasi', 'beras', 'roti', 'mie', 'pasta', 'bread', 'rice']) or 'mi' in name_lower.split():
        quote = "Bulir-bulirku ditanam petani dengan peluh jerih payah, tapi kamu membuang sisa porsiku tanpa penyesalan."
        author = f"Arwah Karbohidrat {item.name.title()}"
    elif any(k in name_lower for k in ['tahu', 'tempe', 'tofu']):
        quote = "Sedikit jamur tumbuh dan kamu langsung mencampakkanku ke tong sampah tanpa sempat kuolah."
        author = f"Roh {item.name.title()}"
    elif any(k in name_lower for k in ['pisang', 'apel', 'jeruk', 'buah', 'fruit']):
        quote = "Kemanisan alaminya kau abaikan sampai kulitku menghitam dan lalat mulai berdatangan."
        author = f"Arwah Buah {item.name.title()}"

    # Lapis 2: Fallback berbasis alasan pembuangan
    elif item.reason == 'FORGOTTEN':
        quote = "Kamu membeliku dengan antusias, lalu menimbunku di balik tumpukan kulkas sampai aku mati terlupakan."
        author = f"Arwah {item.name.title()}"
    elif item.reason == 'EXPIRED':
        quote = "Tanggal kedaluwarsaku tertera jelas di kemasan, namun kamu pura-pura tidak melihat hingga ajalku tiba."
        author = f"Arwah {item.name.title()}"
    elif item.reason == 'OVERCOOKED':
        quote = "Kamu memasakku terlalu banyak dan tak sanggup menghabiskanku. Kini aku mati kedinginan di tempat sampah."
        author = f"Arwah {item.name.title()}"
    elif item.reason in ['MOLD', 'SMELL_TEXTURE']:
        quote = "Sedikit tanda penurunan mutu kau jadikan alasan untuk mengakhiri hidupku ke tong sampah."
        author = f"Arwah {item.name.title()}"
    else:
        quote = "Seharusnya aku mengenyangkan perutmu, namun kelalaianmu mengantarku ke liang kubur limbah."
        author = f"Arwah {item.name.title()}"

    return quote, author


def generate_haunting_wrapped(user_items, analytics):
    """Menyusun daftar slide carousel 'Haunting Wrapped' dari data pengguna."""
    today = timezone.localdate()
    slides = []

    # Filter item bulan berjalan
    this_month_items = user_items.filter(
        disposed_at__year=today.year,
        disposed_at__month=today.month,
    )
    this_count = this_month_items.count()

    # Hitung bulan lalu
    if today.month == 1:
        last_year = today.year - 1
        last_month = 12
    else:
        last_year = today.year
        last_month = today.month - 1

    last_month_items = user_items.filter(
        disposed_at__year=last_year,
        disposed_at__month=last_month,
    )
    last_count = last_month_items.count()

    # -------------------------------------------------------------
    # SLIDE 1: TREN KOMPARASI BULANAN (Handling Cold Start & Trends)
    # -------------------------------------------------------------
    total_all = user_items.count()
    if total_all == 0:
        slides.append({
            'tag': 'RUANG SUCI TANPA KUTUKAN',
            'headline': 'Lembah Graveyard Sunyi Senyap',
            'detail': 'Belum ada satu pun arwah bahan pangan yang menuntut balas. Seluruh bahan di dapurmu masih terjaga atau berhasil diselamatkan di Death Clock!',
            'tone': 'frost',
            'stat_value': '0 Arwah',
            'stat_label': 'Kulkas masih suci',
            'author': 'Penjaga Graveyard',
        })
    elif last_count == 0 and this_count > 0:
        # Kasus Cold-Start: Pengguna baru yang belum punya data bulan lalu
        slides.append({
            'tag': 'REKOR DOSA PERDANA',
            'headline': 'Awal dari Catatan Kelam',
            'detail': f'Bulan ini adalah jejak pemakaman pertamamu di Graveyard. Sebanyak {this_count} bahan telah kau kirim ke liang lahat.',
            'tone': 'blood',
            'stat_value': f'{this_count} Bahan',
            'stat_label': 'Limbah bulan perdana',
            'author': 'Kitab Kematian Pangan',
        })
    elif this_count > last_count:
        # Tren memburuk (Escalation)
        delta = this_count - last_count
        slides.append({
            'tag': 'ESKALASI KUTUKAN',
            'headline': 'Kuburan yang Semakin Penuh',
            'detail': f'Bulan ini kamu membuang {delta} bahan lebih banyak dibanding bulan lalu! Kulkasmu perlahan menjelma menjadi tempat pembantaian bahan makanan.',
            'tone': 'blood',
            'stat_value': f'+{delta} Lebih Banyak',
            'stat_label': f'Total {this_count} bahan bulan ini',
            'author': 'Neraca Penyesalan',
        })
    elif this_count < last_count and last_count > 0:
        # Tren membaik (Improvement)
        delta = last_count - this_count
        slides.append({
            'tag': 'ARWAH MULAI TENANG',
            'headline': 'Kutukan Mulai Melemah',
            'detail': f'Bulan ini kamu berhasil membuang {delta} bahan lebih sedikit dibanding bulan lalu! Kamu perlahan belajar menghargai dan mengolah sisa makanan.',
            'tone': 'frost',
            'stat_value': f'-{delta} Bahan',
            'stat_label': 'Pengurangan limbah',
            'author': 'Penjaga Graveyard',
        })
    elif this_count == last_count and this_count > 0:
        # Tren stagnan
        slides.append({
            'tag': 'LINGKARAN KUTUKAN',
            'headline': 'Dosa yang Berulang',
            'detail': f'Sama persis seperti bulan lalu, {this_count} bahan kembali berakhir di tempat sampah. Pola belanjamu belum menunjukkan tanda-tanda tobat.',
            'tone': 'ember',
            'stat_value': f'{this_count} Bahan',
            'stat_label': 'Statis tanpa perubahan',
            'author': 'Kitab Kematian Pangan',
        })
    else:
        # Ada total items masa lalu, namun bulan ini 0
        slides.append({
            'tag': 'BULAN PERTOBATAN',
            'headline': 'Nol Pembuangan Bulan Ini',
            'detail': 'Bulan ini belum ada satu pun bahan yang terbuang ke Graveyard. Pertahankan ritme penyelamatan ini!',
            'tone': 'frost',
            'stat_value': '0 Limbah',
            'stat_label': f'Periode {analytics.get("month_name", "Bulan Ini")}',
            'author': 'Penjaga Graveyard',
        })

    # -------------------------------------------------------------
    # SLIDE 2: BISIKAN ARWAH MAKANAN (The Voice of the Dead)
    # -------------------------------------------------------------
    if user_items.exists():
        # Cari bahan yang paling berdampak (misal yang paling baru atau kerugian tertinggi)
        prominent_item = (
            user_items.order_by('-estimated_loss', '-disposed_at').first()
            or user_items.first()
        )
        quote, author = get_item_epitaph(prominent_item)
        slides.append({
            'tag': 'BISIKAN ARWAH PANGAN',
            'headline': f'"{quote}"',
            'detail': f'Bahan: {prominent_item.name} ({prominent_item.quantity} {prominent_item.get_unit_display()}) · Alasan: {prominent_item.get_reason_display()}',
            'tone': 'blood',
            'stat_value': prominent_item.name.title(),
            'stat_label': 'Arwah yang menghantui',
            'author': author,
            'is_quote': True,
        })

    # -------------------------------------------------------------
    # SLIDE 3: PENYESALAN DOMPET (Anak Kost Financial Guilt)
    # -------------------------------------------------------------
    total_loss = Decimal(str(analytics.get('total_loss', 0)))
    if total_loss > 0:
        loss_formatted = format_rupiah_short(total_loss)
        if total_loss >= Decimal('15000'):
            porsi_geprek = int(total_loss // Decimal('15000'))
            analogi = f"setara dengan {porsi_geprek} porsi nasi ayam geprek yang kamu buang cuma-cuma."
        elif total_loss >= Decimal('5000'):
            porsi_esteh = int(total_loss // Decimal('3000'))
            analogi = f"setara dengan {porsi_esteh} gelas es teh manis dan camilan yang hangus sia-sia."
        else:
            analogi = "meski nominalnya kecil, uang ini lenyap begitu saja tanpa pernah mengenyangkan perutmu."

        slides.append({
            'tag': 'PENYESALAN DOMPET',
            'headline': 'Uang yang Menguap Jadi Abu',
            'detail': f'Total kerugian {loss_formatted} di tempat sampah ini {analogi}',
            'tone': 'blood',
            'stat_value': loss_formatted,
            'stat_label': 'Uang yang melayang',
            'author': 'Dompet Mahasiswa yang Menangis',
        })

    # -------------------------------------------------------------
    # SLIDE 4: DOSA EKOLOGIS (Jejak Karbon & Gas Rumah Kaca)
    # -------------------------------------------------------------
    total_carbon = float(analytics.get('total_carbon_kg', 0))
    if total_carbon > 0:
        total_weight = float(analytics.get('total_weight_kg', 0))
        slides.append({
            'tag': 'DOSA EKOLOGIS BUMI',
            'headline': 'Bumi Menanggung Lalaimu',
            'detail': f'Pembusukan {total_weight} kg limbah makananmu di TPA diperkirakan telah melepas {total_carbon} kg gas rumah kaca (CO₂e). Bau busuknya membekas di atmosfer.',
            'tone': 'frost',
            'stat_value': f'{total_carbon} kg',
            'stat_label': 'Potensi emisi CO₂e di TPA',
            'author': 'Catatan Iklim Bumi',
        })

    # -------------------------------------------------------------
    # SLIDE 5: MUSUH UTAMA KULKAS (Kategori Paling Sering Terbuang)
    # -------------------------------------------------------------
    top_cat = analytics.get('top_category')
    if top_cat and top_cat.get('count', 0) > 0:
        slides.append({
            'tag': 'KORBAN PALING SERING',
            'headline': f'Kategori Pembantaian: {top_cat["label"]}',
            'detail': f'Kategori ini sudah terbuang sebanyak {top_cat["count"]} kali di tanganmu. Sebelum belanja berikutnya ke supermarket, renungkan apakah kamu benar-benar akan memasaknya!',
            'tone': 'ember',
            'stat_value': f'{top_cat["count"]}x Mati',
            'stat_label': f'Korban: {top_cat["label"]}',
            'author': 'Arwah Kolektif Bahan Pangan',
        })

    return slides
