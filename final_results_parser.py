import requests
from bs4 import BeautifulSoup

def parse_results(date: str = "yesterday"):
    """
    Парсим результаты матчей по дате (или вчерашние).
    date может быть "yesterday" или "2025-08-23"
    """
    url = f"https://scores24.live/ru/soccer/{date}"
    response = requests.get(url)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")

    matches = []
    for match in soup.select("div.sc-17qxh4e-0"):
        # команды
        teams = match.select("div.sc-17qxh4e-10")
        if len(teams) < 2:
            continue
        home_team, away_team = teams[0].get_text(strip=True), teams[1].get_text(strip=True)

        # финальный счёт (берем последний блок sc-pvs6fr-0)
        score_blocks = match.select("div.sc-pvs6fr-0")
        if not score_blocks:
            continue
        final_score = score_blocks[-1].get_text(strip=True)
        try:
            home_goals, away_goals = map(int, final_score)
        except Exception:
            continue

        matches.append({
            "home": home_team,
            "away": away_team,
            "score": f"{home_goals}:{away_goals}",
            "both_to_score": home_goals > 0 and away_goals > 0
        })

    return matches
