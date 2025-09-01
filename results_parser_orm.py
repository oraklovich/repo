# results_parser_orm.py
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import re
from models import get_db_session, Prediction, Result, Analysis

FINISHED_KEYWORDS = ("закончен", "заверш", "finished", "completed")


def parse_results(date: str = "yesterday"):
    """Парсим результаты матчей по дате и берём только итоговый счёт"""
    if date == "yesterday":
        date = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")

    url = f"https://scores24.live/ru/soccer/{date}"
    print(f"🕸️ Парсим URL: {url}")

    try:
        response = requests.get(
            url,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36"
                )
            },
            timeout=20,
        )
        response.raise_for_status()
    except requests.RequestException as e:
        print(f"❌ Ошибка запроса: {e}")
        return []

    soup = BeautifulSoup(response.text, "html.parser")
    matches = []

    for match in soup.select("div.sc-17qxh4e-0"):
        try:
            team_nodes = match.select("div.sc-17qxh4e-10")
            if len(team_nodes) < 2:
                continue
            home_team = team_nodes[0].get_text(strip=True)
            away_team = team_nodes[1].get_text(strip=True)

            status_elem = match.select_one("div.sc-1p31vt4-0")
            status = status_elem.get_text(strip=True) if status_elem else "Завершен"

            if not any(k in status.lower() for k in FINISHED_KEYWORDS):
                continue

            scores_container = match.select_one("div.sc-4g7sie-0")
            if not scores_container:
                continue
            final_score_block = scores_container.select_one("div.sc-pvs6fr-0")
            if not final_score_block:
                continue
            score_cells = final_score_block.select("div.sc-pvs6fr-1")
            if len(score_cells) < 2:
                continue

            try:
                home_goals = int(score_cells[0].get_text(strip=True))
                away_goals = int(score_cells[1].get_text(strip=True))
            except ValueError:
                continue

            matches.append({
                "home_team": home_team,
                "away_team": away_team,
                "home_score": home_goals,
                "away_score": away_goals,
                "status": status,
            })
            print(f"⚽ {home_team} {home_goals}:{away_goals} {away_team} ({status})")

        except Exception as e:
            print(f"❌ Ошибка парсинга матча: {e}")
            continue

    print(f"📊 Найдено завершённых матчей: {len(matches)}")
    return matches


def normalize_name(name: str) -> str:
    return re.sub(r"[^\w]", "", name.lower().replace("ё", "е").strip())


def find_matching_result(prediction: Prediction, results: list):
    """Находим результат матча для данного прогноза"""
    pred_home_norm = normalize_name(prediction.home_team)
    pred_away_norm = normalize_name(prediction.away_team)

    for result in results:
        res_home_norm = normalize_name(result["home_team"])
        res_away_norm = normalize_name(result["away_team"])
        if (pred_home_norm in res_home_norm or res_home_norm in pred_home_norm) and \
           (pred_away_norm in res_away_norm or res_away_norm in pred_away_norm):
            return result
    return None


def analyze_prediction_accuracy(prediction: Prediction, result: dict, session):
    """Сравниваем прогноз BTTS с реальным результатом и сохраняем анализ"""
    predicted_btts = prediction.prediction_value.lower() in ["yes", "да", "true"]
    actual_btts = result["home_score"] > 0 and result["away_score"] > 0
    is_correct = predicted_btts == actual_btts

    analysis = Analysis(
        prediction_id=prediction.id,
        is_correct=is_correct
    )
    session.add(analysis)
    return is_correct


def main():
    print("🎯 PARSER & ANALYSIS BTTS")
    print("=" * 50)

    session = get_db_session()

    # Парсим последние 3 дня
    all_results = []
    for i in range(3):
        date = (datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d")
        print(f"\n📅 Парсим дату: {date}")
        results = parse_results(date)
        all_results.extend(results)

    # Берем все прогнозы без результатов в results
    predictions_without_results = session.query(Prediction).filter(
        ~session.query(Result).filter(
            Result.home_team == Prediction.home_team,
            Result.away_team == Prediction.away_team,
            Result.match_time == Prediction.match_time
        ).exists()
    ).all()

    print(f"\n🗄️ Прогнозов без результатов: {len(predictions_without_results)}")

    inserted = updated = analyzed = 0

    for pred in predictions_without_results:
        print(f"\n🔍 Ищем результат для: {pred.home_team} vs {pred.away_team} @ {pred.match_time}")
        match_result = find_matching_result(pred, all_results)
        if match_result:
            # Сохраняем или обновляем результат
            existing = session.query(Result).filter_by(
                home_team=pred.home_team,
                away_team=pred.away_team,
                match_time=pred.match_time
            ).first()
            if existing:
                existing.home_score = match_result["home_score"]
                existing.away_score = match_result["away_score"]
                existing.status = match_result["status"]
                updated += 1
                print(f"♻️ Обновлено: {pred.home_team} {match_result['home_score']}:{match_result['away_score']} {pred.away_team}")
            else:
                new_result = Result(
                    home_team=pred.home_team,
                    away_team=pred.away_team,
                    match_time=pred.match_time,
                    home_score=match_result["home_score"],
                    away_score=match_result["away_score"],
                    status=match_result["status"]
                )
                session.add(new_result)
                inserted += 1
                print(f"✅ Вставлено: {pred.home_team} {match_result['home_score']}:{match_result['away_score']} {pred.away_team}")

            # Анализ прогноза
            if analyze_prediction_accuracy(pred, match_result, session):
                print(f"📊 Прогноз верный")
            else:
                print(f"📊 Прогноз неверный")
            analyzed += 1
        else:
            print("❌ Результат не найден в парсинге")

    session.commit()
    session.close()

    print("\n🎯 ИТОГ:")
    print(f"   Вставлено результатов: {inserted}")
    print(f"   Обновлено результатов: {updated}")
    print(f"   Проанализировано прогнозов: {analyzed}")


if __name__ == "__main__":
    main()
