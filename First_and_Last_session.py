import pandas as pd
import os

# Укажите полный путь к папке с CSV файлами
path_to_folder = r"C:\Users\User\Desktop\Ha-ha-thone\NEW_Hackathon Cifrium. Case ADA\nessesary\INTEREST_in progress"

# Загрузка данных
students_df = pd.read_csv(os.path.join(path_to_folder, 'students_of_interest.csv'), encoding='utf-8-sig')
trainings_df = pd.read_csv(os.path.join(path_to_folder, 'user_trainings.csv'), encoding='utf-8-sig')
answers_df = pd.read_csv(os.path.join(path_to_folder, 'user_answers.csv'), encoding='utf-8-sig')

# Загружаем media_view_sessions без автоматического парсинга
media_df = pd.read_csv(os.path.join(path_to_folder, 'media_view_sessions.csv'), encoding='utf-8-sig')

actions_df = pd.read_csv(os.path.join(path_to_folder, 'wk_users_courses_actions.csv'), encoding='utf-8-sig')

# Функция для безопасного преобразования дат
def parse_date_safe(date_str):
    """Преобразует строку с датой в Timestamp, пробуя разные форматы"""
    if pd.isna(date_str):
        return None
    
    date_str = str(date_str).strip()
    
    # Пробуем форматы в порядке приоритета
    formats = [
        '%d/%m/%y %H:%M',      # 04/12/25 20:14
        '%m/%d/%Y %H:%M',      # 12/4/2025 20:12
        '%d/%m/%Y %H:%M',      # 14/12/2025 0:56
        '%Y-%m-%d %H:%M:%S',   # 2025-10-13 12:20:00
        '%m/%d/%y %H:%M',      # 12/04/25 20:14
    ]
    
    for fmt in formats:
        try:
            return pd.to_datetime(date_str, format=fmt)
        except (ValueError, TypeError):
            continue
    
    # Если ничего не подошло, пробуем автоматически
    try:
        return pd.to_datetime(date_str)
    except:
        return None

# Запрос user_id
user_id = int(input("Введите user_id: "))

# Сбор всех временных меток
timestamps = []

# 1. students_of_interest
user_student = students_df[students_df['user_id'] == user_id]
if not user_student.empty:
    for val in user_student['current_sign_in_at']:
        dt = parse_date_safe(val)
        if dt:
            timestamps.append(dt)
    for val in user_student['last_sign_in_at']:
        dt = parse_date_safe(val)
        if dt:
            timestamps.append(dt)

# 2. user_trainings
user_trainings = trainings_df[trainings_df['user_id'] == user_id]
for val in user_trainings['started_at']:
    dt = parse_date_safe(val)
    if dt:
        timestamps.append(dt)
for val in user_trainings['finished_at']:
    dt = parse_date_safe(val)
    if dt:
        timestamps.append(dt)

# 3. user_answers
user_answers = answers_df[answers_df['user_id'] == user_id]
for val in user_answers['created_at']:
    dt = parse_date_safe(val)
    if dt:
        timestamps.append(dt)
for val in user_answers['updated_at']:
    dt = parse_date_safe(val)
    if dt:
        timestamps.append(dt)

# 4. media_view_sessions
user_media = media_df[media_df['user_id'] == user_id]
for val in user_media['started_at']:
    dt = parse_date_safe(val)
    if dt:
        timestamps.append(dt)
for val in user_media['finished_at']:
    dt = parse_date_safe(val)
    if dt:
        timestamps.append(dt)

# 5. wk_users_courses_actions
user_actions = actions_df[actions_df['user_id'] == user_id]
for val in user_actions['created_at']:
    dt = parse_date_safe(val)
    if dt:
        timestamps.append(dt)

# Нахождение первой и последней даты
if timestamps:
    first_activity = min(timestamps)
    last_activity = max(timestamps)
    
    print(f"\nРезультаты для user_id = {user_id}:")
    print(f"Первая активность: {first_activity}")
    print(f"Последняя активность: {last_activity}")
    print(f"\nВсего активностей найдено: {len(timestamps)}")
else:
    print(f"\nДля user_id = {user_id} не найдено никаких активностей.")