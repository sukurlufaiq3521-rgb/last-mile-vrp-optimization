# 🚚 Last-Mile Delivery Route Optimization (VRP)

Python və Google OR-Tools istifadə edərək son mərhələ çatdırılma marşrutlarının optimallaşdırılması layihəsi. Bu layihə, real dünya logistika şirkətlərinin (Amazon, DHL, UPS) istifadə etdiyi Vehicle Routing Problem (VRP) metodologiyasını tələbə səviyyəsində tətbiq edir.

## 📋 Problem

80 çatdırılma nöqtəsi və 5 nəqliyyat vasitəsi olan bir ssenaridə, ümumi qət olunan məsafəni minimuma endirən optimal marşrutları tapmaq — hər maşının yük tutumu məhdudiyyətinə əməl edərək.

## 🎯 Nəticələr

| Metod | Ümumi Məsafə | 
|-------|--------------|
| Naive (optimallaşdırma yoxdur) | 427.74 km |
| **OR-Tools (optimallaşdırılmış)** | **94.07 km** |
| **Yaxşılaşma** | **78% azalma** |

> ⚠️ Qeyd: Naive baseline sıra-əsaslı (coğrafi məntiqsiz) bölgüdür — real dünya insan-idarəli planlaşdırma ilə müqayisədə fərq adətən 15-30% arasında olur, amma bu nəticə alqoritmin nəzəri potensialını göstərir.

## 🗺️ Marşrut Vizualizasiyası

Aşağıda 5 maşının optimallaşdırılmış marşrutları göstərilir (hər rəng bir maşına aiddir):

![Route Map](outputs/route_map_screenshot.png)

İnteraktiv versiya: `outputs/route_map.html` faylını brauzerdə açın.

## 🛠️ İstifadə Olunan Texnologiyalar

- **Python** — əsas proqramlaşdırma dili
- **Google OR-Tools** — VRP optimallaşdırma solver-i
- **Pandas / NumPy** — data emalı
- **Folium** — interaktiv xəritə vizualizasiyası

## 📂 Layihə Strukturu
## 🚀 Necə İşə Salmaq Olar

```bash
# Virtual environment yaradın və aktivləşdirin
python -m venv venv
venv\Scripts\activate  # Windows

# Kitabxanaları quraşdırın
pip install pandas numpy matplotlib ortools folium

# Skriptləri ardıcıl işə salın
python src/01_generate_data.py
python src/02_distance_matrix.py
python src/03_solve_vrp.py
python src/04_visualize.py
python src/05_compare_performance.py
```

## 🔑 Əsas Metodologiya

1. **Data Generasiyası** — Bakı ərazisində 80 sintetik çatdırılma nöqtəsi, hər birinin təsadüfi tələb (demand) dəyəri ilə
2. **Distance Matrix** — Haversine formulası ilə bütün nöqtə cütləri arasında real Yer kürəsi məsafəsi hesablanır
3. **VRP Solver** — Google OR-Tools ilə, hər maşının yük tutumu məhdudiyyəti (capacity constraint) daxil edilərək optimal marşrutlar tapılır
4. **Vizualizasiya** — Folium ilə real xəritə üzərində interaktiv marşrut göstərilməsi
5. **Performans Ölçülməsi** — Optimallaşdırılmamış (naive) və optimallaşdırılmış nəticələr müqayisə edilir

## 👤 Müəllif

Faiq Sukurlu — Logistika və Nəqliyyat Texnologiyaları tələbəsi

[linkedin.com/in/faiq-sukurlu-024813374] | [https://github.com/sukurlufaiq3521-rgb]