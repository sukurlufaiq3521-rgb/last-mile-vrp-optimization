![Tests](https://github.com/sukurlufaiq3521-rgb/last-mile-vrp-optimization/actions/workflows/tests.yml/badge.svg)
# 🚚 Last-Mile Delivery Route Optimization (VRP)

Python və Google OR-Tools istifadə edərək son mərhələ çatdırılma marşrutlarının optimallaşdırılması layihəsi. Bu layihə, real dünya logistika şirkətlərinin (Amazon, DHL, UPS) istifadə etdiyi Vehicle Routing Problem (VRP) metodologiyasını real yol şəbəkəsi inteqrasiyası və tam interaktiv dashboard ilə tətbiq edir.

## 📋 Problem

80 çatdırılma nöqtəsi və dəyişkən sayda nəqliyyat vasitəsi olan bir ssenaridə, hər maşının yük tutumu məhdudiyyətinə əməl edərək, ümumi qət olunan məsafəni minimuma endirən optimal marşrutları tapmaq.

## 🎯 Əsas Nəticələr

| Metod | Ümumi Məsafə |
|-------|--------------|
| Naive (optimallaşdırma yoxdur) | 164.47 km |
| **OR-Tools (optimallaşdırılmış)** | **66.88 km** |
| **Yaxşılaşma** | **~59% azalma** |

> ⚠️ Qeyd: Naive baseline sıra-əsaslı (coğrafi məntiqsiz) bölgüdür. Real dünya insan-idarəli planlaşdırma ilə müqayisədə fərq adətən 15-30% arasında olur, amma bu nəticə alqoritmin nəzəri potensialını göstərir.

## 🖥️ İnteraktiv Dashboard

Layihə, Streamlit ilə qurulmuş tam interaktiv bir dashboard daxildir:

- 🎚️ Nəqliyyat vasitəsi sayını real-vaxtda dəyişmək (slider)
- ☑️ Hər maşının marşrutunu ayrı-ayrı aç/bağla etmək
- 📊 Canlı KPI göstəriciləri (məsafə, yük, maşın sayı)
- 📈 Sensitivity Analiz — fərqli flot ölçülərinin ümumi məsafəyə təsirini müqayisə etmək
- 🗺️ Real yol şəbəkəsi (OSRM) ilə dəqiq marşrut vizualizasiyası
- 📥 Nəticələri CSV formatında endirmək

**Dashboard-u işə salmaq üçün:**
```bash
streamlit run app.py
```

## 🗺️ Marşrut Vizualizasiyası

Real Bakı yol şəbəkəsi üzərində, hər rəng bir nəqliyyat vasitəsinin marşrutunu göstərir:

![Route Map](outputs/route_map_screenshot.png)
![Demo Animation](outputs/demo.gif)

Statik interaktiv versiyalar da mövcuddur:
- `outputs/enhanced_route_map.html` — statistika və legend ilə zənginləşdirilmiş xəritə
- `outputs/before_after_map.html` — optimallaşdırmadan əvvəl/sonra müqayisəsi

## 🛠️ İstifadə Olunan Texnologiyalar

| Texnologiya | Məqsəd |
|---|---|
| **Python** | Əsas proqramlaşdırma dili |
| **Google OR-Tools** | VRP optimallaşdırma solver-i (capacity constraint ilə) |
| **OSRM** | Real yol şəbəkəsi üzrə marşrut həndəsəsi |
| **Streamlit** | İnteraktiv veb dashboard |
| **Pandas / NumPy** | Data emalı və riyazi hesablamalar |
| **Folium** | Xəritə vizualizasiyası (Leaflet.js əsaslı) |

## 📂 Layihə Strukturu
## 🚀 Necə İşə Salmaq Olar

```bash
# Repozitoriyu klonlayın
git clone https://github.com/sukurlufaiq3521-rgb/last-mile-vrp-optimization.git
cd last-mile-vrp-optimization

# Virtual environment yaradın və aktivləşdirin
python -m venv venv
venv\Scripts\activate  # Windows

# Kitabxanaları quraşdırın
pip install -r requirements.txt

# Datanı və modelləri hazırlayın (ardıcıl işə salın)
python src/01_generate_data.py
python src/02_distance_matrix.py
python src/03_solve_vrp.py
python src/04_visualize.py
python src/05_compare_performance.py
python src/06_enhanced_map.py
python src/07_before_after_map.py

# İnteraktiv dashboard-u işə salın
streamlit run app.py
```

## 🔑 Əsas Metodologiya

1. **Data Generasiyası** — Bakının real rayonlarına (Yasamal, Nəsimi, Xətai, Nərimanov, Səbail) bölünmüş 80 sintetik çatdırılma nöqtəsi
2. **Koordinat Validasiyası** — su ərazilərinə düşən nöqtələrin avtomatik yoxlanılması
3. **Distance Matrix** — Haversine formulası ilə bütün nöqtə cütləri arasında məsafə hesablanması
4. **VRP Solver** — Google OR-Tools ilə, capacity constraint daxil edilərək optimal marşrutlar tapılması
5. **Real Yol İnteqrasiyası** — OSRM vasitəsilə düz-xətt marşrutların real küçə şəbəkəsinə çevrilməsi
6. **İnteraktiv Vizualizasiya** — Streamlit dashboard ilə real-vaxt parametr dəyişikliyi və nəticə analizi
7. **Sensitivity Analiz** — fərqli flot ölçülərinin (2-10 maşın) ümumi məsafəyə təsirinin kəmiyyətcə ölçülməsi

## 📊 Sensitivity Analiz

Dashboard daxilində, nəqliyyat vasitəsi sayının 2-dən 10-a qədər dəyişməsinin ümumi məsafəyə təsiri analiz edilir və marginal qənaət faizi hesablanaraq, optimal flot ölçüsü üçün analitik tövsiyə verilir — bu, real logistika konsaltinqində "fleet sizing" qərarlarına bənzər bir yanaşmadır.

## 👤 Müəllif

**Faiq Sukurlu** — Logistika və Nəqliyyat Texnologiyaları tələbəsi

[GitHub Profili](https://github.com/sukurlufaiq3521-rgb)