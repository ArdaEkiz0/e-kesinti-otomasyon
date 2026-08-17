# AI Ajanları Kitabı — Referans Notu (ai-agent-book)

İleride uygulama geliştirirken başvuru kaynağı olarak kullanılır.

## Kitap
- "深入理解 AI Agent" / "AI Agents in Depth" — Li Bojie, açık kaynak (Apache-2.0), ~37.5k yıldız
- GitHub: https://github.com/bojieli/ai-agent-book
- 10 bölüm + 95 çalıştırılabilir deney, 13 dil (TÜRKÇE dahil: `book-tr/` klasörü)
- Türkçe PDF: https://github.com/bojieli/ai-agent-book/releases/download/latest/AI-Agents-in-Depth-tr.pdf
- Temel formül: **Ajan = LLM + Bağlam + Araçlar**

## Bölüm haritası (ihtiyaca göre ilgili bölüm açılır)
1. Temeller — ajan mimarisi, harness mühendisliği
2. Bağlam mühendisliği — KV cache, prompt engineering, agent skills, bağlam sıkıştırma
3. Kullanıcı belleği + bilgi tabanları — RAG, yapısal indeks, bilgi grafları
4. Araçlar — MCP protokolü, olay-güdümlü ajanlar
5. Kodlama ajanları (production-grade)
6. Etkileşim — çok modlu, Computer Use, robot
7. Ajan değerlendirmesi — benchmark, istatistiksel anlamlılık
8. Model sonradan eğitimi — SFT vs RL
9. Sürekli evrim — trajectory'den öğrenme
10. Çoklu ajan işbirliği

## Kullanım
Yeni bir uygulamada LLM tabanlı ajan/otomasyon tasarlarken MCP, RAG, bellek ve çoklu ajan
kalıpları için bu kaynağa başvur. Kitap kavramsal rehber; kod örnekleri chapter1-10/ klasörlerinde.

_Not: opencode Supermemory'ye kaydedilemedi (API anahtarı tanımlı değil) — bu dosya kalıcı referans olarak duruyor._