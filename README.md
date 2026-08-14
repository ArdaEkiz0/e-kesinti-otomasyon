# 🌾 SGK Tarımsal Kesinti Botu

SGK Bağ-Kur tarımsal faaliyet bildirimi işlemlerini **otomatikleştiren** Selenium tabanlı masaüstü botu.
Excel'deki üretici listesini okur, SGK sayfasında tek tek işler ve işlem sonucunu ekranda raporlar.

![Python](https://img.shields.io/badge/Python-3.9%2B-blue?logo=python&logoColor=white)
![Platform](https://img.shields.io/badge/Platform-Windows-green)
![Otomasyon](https://img.shields.io/badge/Otomasyon-Selenium-orange?logo=selenium)
![Lisans](https://img.shields.io/badge/Lisans-MIT-brightgreen)
[![Sürüm](https://img.shields.io/github/v/release/ArdaEkiz0/e-kesinti-otomasyon?color=purple&label=S%C3%BCr%C3%BCm)](https://github.com/ArdaEkiz0/e-kesinti-otomasyon/releases)
[![Derleme](https://github.com/ArdaEkiz0/e-kesinti-otomasyon/actions/workflows/release.yml/badge.svg)](https://github.com/ArdaEkiz0/e-kesinti-otomasyon/actions)
[![Tanıtım Sayfası](https://img.shields.io/badge/Tan%C4%B1t%C4%B1m-Site-blueviolet)](https://ardaekiz0.github.io/e-kesinti-otomasyon/)

---

## ✨ Özellikler

- ⚡ **Tek Tık Kurulum** — `KURULUM.exe` Python, Chrome, chromedriver ve paketleri kendisi kurar
- 🔄 **Otomatik Güncelleme** — kurulum aracı açılışta GitHub'dan yeni sürüm olup olmadığını kontrol eder, varsa kendini günceller
- 📊 **Renkli ve İlerlemeli Arayüz** — her kayıt için ilerleme çubuğu, yeşil/kırmızı durum mesajları
- 🔄 **Otomatik Tekrar Deneme** — hata olan kayıt 3 kez denenir (site yavaşsa başarı oranı artar)
- 🔔 **Windows Bitiş Bildirimi** — işlem bitince ekrana bakmadan bildirimle öğrenirsin
- 📁 **Herhangi Bir Excel'i Kullan** — adı ne olursa olsun Excel dosyasını seç ya da sürükle-bırak
- 🧪 **Test Modu** — gerçek işlem yapmadan (sahte sürücü ile) uygulamanın çalıştığını dener
- 🧹 **Otomatik Temizlik** — eski sürücü kilitlerini temizler, sürücü bulunamazsa yerel yedeğe düşer

---

## 🚀 Kurulum

### Seçenek 1: KURULUM.exe ile (Önerilen)

1. `KURULUM.exe` dosyasını indir
2. Çift tıkla, **5 adımı otomatik yapar**:
   - Python 3.9+ kontrolü (yoksa kurar)
   - Gerekli paketler: `selenium`, `pandas`, `openpyxl`, `webdriver-manager`
   - Google Chrome kontrolü (yoksa kurar)
   - chromedriver'ı Chrome sürümüne göre indirir
   - Şablon Excel dosyasını oluşturur

### Seçenek 2: Kaynaktan çalıştırma

```bat
git clone https://github.com/ArdaEkiz0/e-kesinti-otomasyon.git
cd e-kesinti-otomasyon
python KURULUM.py
```

> 📌 Kurulumu `KURULUM.py` üzerinden de çalıştırabilirsin: `python KURULUM.py`

---

## 📄 Excel Formatı

Uygulama şu sütunlara sahip bir Excel dosyası bekler (şablonu kurulum otomatik oluşturur):

| Sütun | İçerik |
|-------|--------|
| **Ünvan** | Üretici adı (yazılması zorunlu değil) |
| **TC Kimlik No** | 11 haneli TC kimlik numarası |
| **Matrah** | Alım bedeli (ondalık kısmı virgülle: `13014,09`) |
| **Bağ-Kur** | Kesinti tutarı (hesaplanır) |

---

## 🖥️ Kullanım

1. Excel dosyanı hazırla (veya şablonu kullan)
2. `BOT_BAŞLAT.bat` dosyasına **çift tıkla** — dosyayı sorar
3. **Daha kolay:** Excel dosyanı `BOT_BAŞLAT.bat` üzerine **sürükle-bırak**
4. Bot SGK sayfasını açar, kayıtları tek tek işler ve raporu ekranda gösterir

### Test Modu

```bat
python sgk_bot.py --test
```

Sayfa açmadan, sahte sürücü ile tüm akışın çalıştığını doğrular.

---

## ❓ Sık Karşılaşılan Sorunlar

| Sorun | Çözüm |
|-------|-------|
| Bot açılmıyor / sürücü hatası | `KURULUM.exe` yeniden çalıştır (Chrome güncellenmiş olabilir) |
| Kuruş yanlış yazılıyor (ör: `13014,90`) | Bu botun eski sürüm sorunudur; güncel sürümde kuruş her zaman 2 haneli (`09`) yazılır |
| Sayfa elemanı bulunamadı | SGK sitesi değişmiş olabilir — sürümü kontrol et |

---

## 👨‍💻 Geliştirici

**Arda M. Ekiz** — GitHub: [ArdaEkiz0](https://github.com/ArdaEkiz0)
