name: 🐛 Hata Bildirimi
description: Bot çalışırken bir hata mı oluştu? Bu şablonu kullanarak bildir.
title: "[Hata] Kısa açıklama"
labels: ["bug"]
body:
  - type: markdown
    attributes:
      value: |
        ⚠️ **Önemli:** Gerçek TC kimlik numarası veya Excel dosyası paylaşmayın. Örnek/anonim veri kullanın.
  - type: input
    id: surum
    attributes:
      label: Sürüm
      description: Sürüm numarası (release etiketi, örn. v1.0.3) veya `KURULUM.py` içindeki `SURUM` değeri
      placeholder: v1.0.3
    validations:
      required: true
  - type: input
    id: ortam
    attributes:
      label: Sistem
      description: Windows sürümü ve Chrome sürümü
      placeholder: Windows 11 · Chrome 130
    validations:
      required: true
  - type: textarea
    id: hata
    attributes:
      label: Hata mesajı
      description: Ekrandaki hatanın tam metni veya ekran görüntüsü
    validations:
      required: true
  - type: textarea
    id: adimlar
    attributes:
      label: Tekrar etme adımları
      description: Hatayı görmek için neler yaptınız?
      placeholder: |
        1. KURULUM.exe çalıştırdım
        2. Excel dosyasını seçtim
        3. ...
    validations:
      required: true
  - type: textarea
    id: beklenti
    attributes:
      label: Beklenen davranış
      description: Neyin olması gerekiyordu?