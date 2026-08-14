# 🤝 Katkı Rehberi

Bu projeye katkıda bulunacağın için teşekkürler! Aşağıdaki kurallar hem sana hem de projenin güvenliğine yardımcı olur.

## ⚠️ Gizlilik Uyarısı (Çok Önemli)

- Bu bot **gerçek TC kimlik numaralarıyla** çalışır.
- **Excel dosyalarını (`*.xlsx`) ASLA yükleme.** `.gitignore` zaten engelliyor ama sürükle-bırak sırasında dikkatli ol.
- Ekran görüntüleri ve günlüklerde de kimlik bilgisi paylaşma — örnek veriler kullan.

## 🐛 Hata Bildirimi

1. **Önce kontrol et:** Sorunun zaten bildirilmiş olup olmadığına bak (Issues + Discussions).
2. Issue'da şunları belirt:
   - **Sürüm** (`KURULUM.py` içindeki `SURUM` değeri veya release etiketi)
   - **Windows sürümü** ve **Chrome sürümü**
   - **Hata mesajının tam metni** (ekran görüntüsü veya kopyala-yapıştır)
   - Sorunu **tekrar etme adımları** (mümkünse örnek/anonim veriyle)

## 💻 Kod Katkısı

1. Repoyu fork et ve `main`'den yeni bir dal aç:
   ```
   git checkout -b ozellik/ne-ekliyorsun
   ```
2. Değişikliğini yap. Küçük ve odaklı değişiklikler tercih edilir.
3. Geliştirme ortamını kur ve test et:
   ```bat
   python -m pip install -r requirements.txt
   python sgk_bot.py --test
   ```
   `--test` modu sayfa açmadan tüm akışı doğrular.
4. Sürüm numarasını yükselt:
   - `sgk_bot.py` → `BOT_SURUM`
   - `KURULUM.py` → `SURUM`
5. Değişikliklerini commit'le (açıklayıcı mesaj yaz) ve dalını push et, ardından **Pull Request** aç.

## 📝 Commit Mesajı

Kısa ve net ol: `ekle: yeni özellik`, `duzelt: hata adı`, `site: açıklama` gibi. Ayrıntıyı commit gövdesine yaz.

## 🚀 Release Akışı

Release'ler otomatiktir: `v1.2.3` formatında **tag** atıldığında GitHub Actions, `KURULUM.exe`'yi derleyip release olarak yayınlar.

```bat
git tag v1.2.3
git push origin v1.2.3
```
