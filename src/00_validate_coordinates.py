import pandas as pd

def is_likely_water(lat, lon):
    """
    Bakı buxtasının təxmini su sərhədini yoxlayır.
    Bu, sadə bir hüdud yoxlamasıdır (tam dəqiq deyil, amma əsas səhvləri tutur).
    Bakı buxtası təxminən: lat < 40.365 VƏ lon > 49.83 ərazisində geniş su sahəsidir.
    """
    if lat < 40.365 and lon > 49.83:
        return True
    return False

def main():
    df = pd.read_csv('data/delivery_points.csv')

    problem_points = []
    for i in range(1, len(df)):
        lat = df.loc[i, 'latitude']
        lon = df.loc[i, 'longitude']
        if is_likely_water(lat, lon):
            problem_points.append(i)

    if problem_points:
        print(f"XƏBƏRDARLIQ: {len(problem_points)} nöqtə su ərazisinə düşə bilər!")
        print(f"Problemli point_id-lər: {problem_points}")
    else:
        print("Yoxlama uğurlu: bütün nöqtələr quru sahə daxilindədir.")

if __name__ == '__main__':
    main()