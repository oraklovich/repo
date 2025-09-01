# working_results_parser.py
import requests
from bs4 import BeautifulSoup
from database import get_db_connection

FINISHED_KEYWORDS = ("закончен", "заверш")

def parse_results(date: str = "yesterday"):
    """
    Парсим результаты матчей по дате (или вчерашние).
    date: "yesterday" или "YYYY-MM-DD"
    Берём ТОЛЬКО итоговый счёт: первый div.sc-pvs6fr-0 внутри контейнера div.sc-4g7sie-0.
    """
    url = f"https://scores24.live/ru/soccer/{date}"
    print(f"🕸️  Парсим URL: {url}")

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
        print(f"❌ Ошибка при запросе: {e}")
        return []

    soup = BeautifulSoup(response.text, "html.parser")
    matches = []

    # Каждый матч — корневой блок
    for match in soup.select("div.sc-17qxh4e-0"):
        try:
            # 1) Названия команд
            team_nodes = match.select("div.sc-17qxh4e-10")
            if len(team_nodes) < 2:
                continue
            home_team = team_nodes[0].get_text(strip=True)
            away_team = team_nodes[1].get_text(strip=True)

            # 2) Статус матча — обрабатываем только завершённые
            status_elem = match.select_one("div.sc-1p31vt4-0")
            status = status_elem.get_text(strip=True) if status_elem else ""
            if status and not any(k in status.lower() for k in FINISHED_KEYWORDS):
                # Если матч не завершён — пропускаем
                continue
            if not status:
                status = "Завершен"

            # 3) Контейнер со счетами и ВЗЯТЬ ПЕРВЫЙ блок как итог
            scores_container = match.select_one("div.sc-4g7sie-0")
            if not scores_container:
                continue

            final_score_block = scores_container.select_one("div.sc-pvs6fr-0")
            if not final_score_block:
                continue

            # Внутри финального блока два числа: хозяева и гости
            score_cells = final_score_block.select("div.sc-pvs6fr-1")
            if len(score_cells) < 2:
                continue

            try:
                home_goals = int(score_cells[0].get_text(strip=True))
                away_goals = int(score_cells[1].get_text(strip=True))
            except ValueError:
                continue

            match_data = {
                "home_team": home_team,
                "away_team": away_team,
                "home_score": home_goals,
                "away_score": away_goals,
                "score": f"{home_goals}:{away_goals}",
                "status": status,
                "both_to_score": home_goals > 0 and away_goals > 0,
            }
            matches.append(match_data)
            print(f"   ⚽ {home_team} {home_goals}:{away_goals} {away_team} ({status})")

        except Exception as e:
            print(f"❌ Ошибка при парсинге матча: {e}")
            continue

    print(f"📊 Найдено завершённых матчей: {len(matches)}")
    return matches


def get_matches_without_results():
    """Возвращает список матчей из predictions без результатов в results."""
    conn = get_db_connection()
    cur = conn.cursor()

    query = """
        SELECT p.id, p.home_team, p.away_team, p.match_time
        FROM predictions p
        WHERE NOT EXISTS (
            SELECT 1
            FROM results r
            WHERE r.home_team = p.home_team
              AND r.away_team = p.away_team
              AND r.match_time = p.match_time
        )
        ORDER BY p.match_time DESC;
    """

    cur.execute(query)
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return rows


def upsert_result_to_db(home_team, away_team, match_time, home_score, away_score, status):
    """
    Обновляет результат, если запись уже есть (по home+away+match_time),
    иначе — вставляет новую. Возвращает 'inserted' | 'updated' | 'skipped'.
    """
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        # Пытаемся обновить существующую запись
        cur.execute(
            """
            UPDATE results
               SET home_score = %s,
                   away_score = %s,
                   status = %s,
                   updated_at = NOW()
             WHERE home_team = %s
               AND away_team = %s
               AND match_time = %s
            """,
            (home_score, away_score, status, home_team, away_team, match_time),
        )
        if cur.rowcount > 0:
            conn.commit()
            print(f"♻️  Обновлено: {home_team} {home_score}:{away_score} {away_team}")
            return "updated"

        # Если не обновили — вставляем новую
        cur.execute(
            """
            INSERT INTO results (home_team, away_team, match_time, home_score, away_score, status, updated_at)
            VALUES (%s, %s, %s, %s, %s, %s, NOW())
            """,
            (home_team, away_team, match_time, home_score, away_score, status),
        )
        conn.commit()
        print(f"✅ Вставлено: {home_team} {home_score}:{away_score} {away_team}")
        return "inserted"

    except Exception as e:
        conn.rollback()
        print(f"❌ Ошибка при сохранении: {e}")
        return "skipped"
    finally:
        cur.close()
        conn.close()


def main():
    print("🎯 РАБОЧИЙ ПАРСЕР РЕЗУЛЬТАТОВ (финальный счёт)")
    print("=" * 60)

    # Даты для парсинга — подставь свои
    dates_to_parse = ["2025-08-23", "2025-08-22", "yesterday"]

    all_results = []
    for date in dates_to_parse:
        print(f"\n📅 Парсим дату: {date}")
        results = parse_results(date)
        all_results.extend(results)

    print(f"\n📊 Всего найдено завершённых результатов: {len(all_results)}")

    # Матчи из БД, у которых ещё нет результата
    matches = get_matches_without_results()
    print(f"🗄️  В БД без результата: {len(matches)}")

    # Для наглядности
    if matches:
        print("\n📋 Матчи из predictions:")
        for i, m in enumerate(matches, 1):
            print(f"   {i:2d}. {m[1]} vs {m[2]}  @ {m[3]}")

    # Индексируем результаты для быстрого сопоставления по именам
    saved_inserted = saved_updated = 0

    def norm(s: str) -> str:
        return s.lower().replace("ё", "е").strip()

    for pid, p_home, p_away, p_time in matches:
        print(f"\n🔍 Ищем результат: {p_home} vs {p_away} @ {p_time}")
        found = False

        for r in all_results:
            # Гибкое сравнение: подстрочное совпадение в обе стороны
            if (norm(r["home_team"]) in norm(p_home) or norm(p_home) in norm(r["home_team"])) \
               and (norm(r["away_team"]) in norm(p_away) or norm(p_away) in norm(r["away_team"])):

                found = True
                action = upsert_result_to_db(
                    p_home, p_away, p_time, r["home_score"], r["away_score"], r["status"]
                )
                if action == "inserted":
                    saved_inserted += 1
                elif action == "updated":
                    saved_updated += 1
                break

        if not found:
            print("   ❌ Результат не найден в распарсенных данных")

    print(f"\n🎯 ИТОГ: вставлено {saved_inserted}, обновлено {saved_updated}")

if __name__ == "__main__":
    main()
