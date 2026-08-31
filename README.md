<div align="center">

<img src="docs/logo-512.png" alt="SGK E-Kesinti Otomasyon Logo" width="140"/>

# 🌾 SGK E-Kesinti Otomasyonu

**SGK Bağ-Kur tarımsal faaliyet kesinti bildirimlerini tek tıkla otomatikleştiren masaüstü botu**

Excel'deki üretici listesini okur • SGK sayfasında sırayla işler • Sonucu raporlar

[![Sürüm](https://img.shields.io/github/v/release/ArdaEkiz0/e-kesinti-otomasyon?color=purple&label=S%C3%BCr%C3%BCm&style=flat-square)](https://github.com/ArdaEkiz0/e-kesinti-otomasyon/releases)
[![İndirme](https://img.shields.io/github/downloads/ArdaEkiz0/e-kesinti-otomasyon/total?color=orange&label=%C4%B0ndirme&style=flat-square)](https://github.com/ArdaEkiz0/e-kesinti-otomasyon/releases)
[![Python](https://img.shields.io/badge/Python-3.9%2B-blue?logo=python&logoColor=white&style=flat-square)](https://www.python.org)
[![Platform](https://img.shields.io/badge/Platform-Windows-green?logo=windows&style=flat-square)](#)
[![Derleme](https://img.shields.io/github/actions/workflow/status/ArdaEkiz0/e-kesinti-otomasyon/release.yml?label=Derleme&style=flat-square)](https://github.com/ArdaEkiz0/e-kesinti-otomasyon/actions)
[![Lisans](https://img.shields.io/badge/Lisans-MIT-brightgreen?style=flat-square)](LICENSE)

<br>

[⬇️ **HEMEN İNDİR**](https://github.com/ArdaEkiz0/e-kesinti-otomasyon/releases/latest/download/SGK_E_Kesinti_Otomasyon.zip)

*Son sürümü ZIP olarak indir — kurulum gerekmez*

</div>

---

## 📸 Ekran Görüntüleri

| Bot çalışırken | Kurulum aracı |
| :---: | :---: |
| ![Bot ekran görüntüsü](docs/ekran-bot.png) | ![Kurulum aracı ekran görüntüsü](docs/ekran-kurulum.png) |

---

## ✨ Özellikler

| | |
| :--- | :--- |
| ⚡ **Tek Tık Kurulum** | `BAT_KURULUM.bat` Python ve tüm paketleri kendisi kurar |
| 🔄 **Otomatik Güncelleme** | Bot açılışta yeni sürümü kontrol eder; onaylarsan kendini indirip günceller |
| 🔐 **Oturum Kurtarma** | SGK oturumu düşerse yeniden giriş ister, kaldığı kayıttan devam eder |
| 🔢 **200+ Kayıt Destek** | Tek seferde yüzlerce üreticiyi sıraya koyar; her kayıtta kalan süre gösterilir |
| 💰 **Doğru Kuruş Formatı** | `13014,09` gibi tutarlar asla bozulmaz (`09` sorunu tarihe gömüldü) |
| ✂️ **Büyük Matrah Bölme** | 1 milyon TL üzeri alımları otomatik ikiye bölerek iki işlem yapar |
| 📊 **Renkli İlerleme Arayüzü** | İlerleme çubuğu + yeşil/kırmızı durum mesajları |
| 🔁 **Akıllı Tekrar Deneme** | Hata olan kayıt 3 kez denenir; sonda "hatalılar tekrar denensin mi?" sorar |
| 🔔 **Windows Bildirimi** | İşlem bitince balon bildirimle haber verir |
| 🖼️ **Logolu Masaüstü Kısayolu** | İlk başlatmada buğday logolu kısayolu masaüstüne kendisi oluşturur |
| 🧪 **Test Modu** | Tarayıcı açmadan tüm akışı simüle eder (`--test`) |

---

## 🚀 Kurulum (2 dakika)

1. [**ZIP paketini indir**](https://github.com/ArdaEkiz0/e-kesinti-otomasyon/releases/latest/download/SGK_E_Kesinti_Otomasyon.zip)
2. ZIP'i bir klasöre **çıkart**
3. **`BAT_KURULUM.bat`** dosyasına çift tıkla *(Python + paketleri otomatik kurar)*
4. **`BAT_BASLAT.bat`** dosyasına çift tıkla → bot hazır! 🎉

> 💡 İlk `BAT_BASLAT.bat` çalıştırmasında masaüstüne **buğday logolu kısayol** eklenir.
> Bir daha ZIP klasörünü açmana gerek kalmaz.

<details>
<summary><b>📦 Kaynaktan çalıştırma (geliştiriciler için)</b></summary>

```bat
git clone https://github.com/ArdaEkiz0/e-kesinti-otomasyon.git
cd e-kesinti-otomasyon
python -m pip install -r requirements.txt
python sgk_bot.py
```

</details>

---

## 📄 Excel Formatı

Bot şu sütunlara sahip Excel bekler — şablonu (`çalışmaaaa.xlsx`) kurulum kendisi oluşturur:

| Sütun | İçerik | Örnek |
|-------|--------|-------|
| **Ünvan** | Üretici adı (zorunlu değil) | Ahmet Yılmaz |
| **TC Kimlik No** | 11 haneli TC numarası | 12345678901 |
| **Matrah** | Alım bedeli | 13014,09 |
| **Bağ-Kur** | Kesinti tutarı | 1952,11 |

> 💡 Matrahı **1 milyon TL** ve üzerinde girersen bot otomatik ikiye bölüp iki işlem yapar.

---

## 🖥️ Kullanım

1. Excel dosyanı hazırla (veya şablonu doldur)
2. `BAT_BASLAT.bat`'a çift tıkla → SGK sayfası açılır → **elle login ol** → terminale dönüp **ENTER**'a bas
3. Gerisini bot halleder — kayıtlar tek tek işlenir, ilerleme ekranda akar
4. Bitince özet rapor + Windows bildirimi gelir

**Daha da kolayı:** Excel dosyanı `BAT_BASLAT.bat` üzerine **sürükle-bırak**.

### 🧪 Test Modu

```bat
python sgk_bot.py --test
```

Tarayıcı açmadan, sahte sürücüyle tüm akışın çalıştığını doğrular.

---

## ❓ Sık Karşılaşılan Sorunlar

| Sorun | Çözüm |
|-------|-------|
| "Python bulunamadı" | `BAT_KURULUM.bat`'ı çalıştır — Windows Store'un sahte python taklidini otomatik atlar |
| Sürücü/tarayıcı hatası | Chrome'u güncelle, `BAT_KURULUM.bat`'ı tekrar çalıştır |
| Oturum düştü uyarısı | Tarayıcıdan tekrar login ol, ENTER'a bas — bot kaldığı yerden devam eder |
| Bazı kayıtlar hatalı | İşlem sonunda sorulan **"tekrar denensin mi?"** sorusuna **E** de |

---

## 🤝 Katkı

- 🐛 [Issues](https://github.com/ArdaEkiz0/e-kesinti-otomasyon/issues) — hata bildirimi
- 💬 [Discussions](https://github.com/ArdaEkiz0/e-kesinti-otomasyon/discussions) — soru & öneri
- 📖 [CONTRIBUTING.md](CONTRIBUTING.md) — katkı rehberi

---

<div align="center">

**👨‍💻 Geliştirici: Arda M. Ekiz** — [ArdaEkiz0](https://github.com/ArdaEkiz0)

⭐ Bu proje işine yaradıysa yıldızlamayı unutma!

</div>
