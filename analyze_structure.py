# analyze_structure.py
import json
from pprint import pprint

def analyze_urql_structure():
    """Анализирует структуру URQL данных"""
    print("Анализируем структуру URQL данных...")
    
    try:
        # Читаем сохраненные данные
        with open('debug_urql_data.json', 'r', encoding='utf-8') as f:
            urql_data = json.load(f)
        
        print(f"Тип корневого элемента: {type(urql_data)}")
        print(f"Ключи в корне: {list(urql_data.keys())}")
        
        # Анализируем каждый ключ
        for key, value in urql_data.items():
            print(f"\n--- Анализ ключа: {key} ---")
            print(f"Тип значения: {type(value)}")
            
            if isinstance(value, dict):
                print(f"Ключи в значении: {list(value.keys())}")
                
                # Если есть data, анализируем ее
                if 'data' in value:
                    data_value = value['data']
                    print(f"Тип data: {type(data_value)}")
                    
                    if isinstance(data_value, str):
                        # Пробуем распарсить data если это строка
                        try:
                            parsed_data = json.loads(data_value)
                            print(f"Parsed data type: {type(parsed_data)}")
                            if isinstance(parsed_data, dict):
                                print(f"Ключи в parsed data: {list(parsed_data.keys())}")
                                
                                # Ищем что-то связанное с матчами
                                for data_key, data_val in parsed_data.items():
                                    if 'match' in data_key.lower() or 'game' in data_key.lower():
                                        print(f"Найден ключ связанный с матчами: {data_key}")
                                        print(f"Тип значения: {type(data_val)}")
                                        if isinstance(data_val, list):
                                            print(f"Количество элементов: {len(data_val)}")
                                            if len(data_val) > 0:
                                                print(f"Первый элемент: {type(data_val[0])}")
                                                if isinstance(data_val[0], dict):
                                                    print(f"Ключи первого элемента: {list(data_val[0].keys())}")
                                        
                        except json.JSONDecodeError:
                            print("Data не является валидным JSON")
                    elif isinstance(data_value, dict):
                        print(f"Ключи в data dict: {list(data_value.keys())}")
            
            elif isinstance(value, list):
                print(f"Количество элементов в списке: {len(value)}")
                if len(value) > 0:
                    print(f"Тип первого элемента: {type(value[0])}")
                    if isinstance(value[0], dict):
                        print(f"Ключи первого элемента: {list(value[0].keys())}")
        
        # Поиск любых упоминаний матчей во всей структуре
        print(f"\n--- Поиск матчей во всей структуре ---")
        
        def find_matches(obj, path=""):
            """Рекурсивно ищет структуры с матчами"""
            if isinstance(obj, dict):
                for k, v in obj.items():
                    new_path = f"{path}.{k}" if path else k
                    if 'match' in k.lower() or 'game' in k.lower():
                        print(f"Найден ключ с матчем: {new_path}")
                        print(f"Тип значения: {type(v)}")
                        if isinstance(v, list):
                            print(f"Количество матчей: {len(v)}")
                    find_matches(v, new_path)
            elif isinstance(obj, list) and len(obj) > 0:
                if isinstance(obj[0], dict):
                    # Проверяем первый элемент списка на наличие признаков матча
                    first_item = obj[0]
                    if any(field in first_item for field in ['homeTeam', 'awayTeam', 'startTime', 'teams']):
                        print(f"Найден список матчей по пути: {path}")
                        print(f"Количество матчей: {len(obj)}")
                        print(f"Ключи первого матча: {list(first_item.keys())}")
        
        find_matches(urql_data)
        
    except Exception as e:
        print(f"Ошибка при анализе: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    analyze_urql_structure()
