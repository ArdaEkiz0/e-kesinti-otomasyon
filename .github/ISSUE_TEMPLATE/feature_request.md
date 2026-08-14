name: ✨ Özellik Talebi
description: Bir özellik eksik mi? Fikrini buradan paylaş.
title: "[Özellik] Kısa açıklama"
labels: ["enhancement"]
body:
  - type: markdown
    attributes:
      value: |
        ⚠️ **Önemli:** Gerçek TC kimlik numarası veya Excel dosyası paylaşmayın.
  - type: textarea
    id: sorun
    attributes:
      label: Hangi sorunu çözecek?
      description: Bu özellik hangi durumda işe yarayacak?
    validations:
      required: true
  - type: textarea
    id: cozum
    attributes:
      label: Önerilen çözüm
      description: Nasıl çalışmasını istersiniz? Ne kadar ayrıntılı olursa o kadar iyi.
    validations:
      required: true
  - type: textarea
    id: alternatif
    attributes:
      label: Alternatifler
      description: Şu an bu ihtiyacı nasıl karşılıyorsunuz?