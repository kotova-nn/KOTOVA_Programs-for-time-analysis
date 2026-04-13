import pandas as pd
import os
from datetime import timedelta, datetime

path_to_folder = r"C:\Users\User\Desktop\Ha-ha-thone\NEW_Hackathon Cifrium. Case ADA\nessesary\INTEREST_in progress"

# Загрузка данных
students_df = pd.read_csv(os.path.join(path_to_folder, 'students_of_interest.csv'), encoding='utf-8-sig')
trainings_df = pd.read_csv(os.path.join(path_to_folder, 'user_trainings.csv'), encoding='utf-8-sig')
answers_df = pd.read_csv(os.path.join(path_to_folder, 'user_answers.csv'), encoding='utf-8-sig')
media_df = pd.read_csv(os.path.join(path_to_folder, 'media_view_sessions.csv'), encoding='utf-8-sig')
actions_df = pd.read_csv(os.path.join(path_to_folder, 'wk_users_courses_actions.csv'), encoding='utf-8-sig')

def parse_date_safe(date_str):
    if pd.isna(date_str):
        return None
    date_str = str(date_str).strip()
    formats = [
        '%d/%m/%y %H:%M:%S',
        '%d/%m/%y %H:%M',
        '%m/%d/%Y %H:%M:%S',
        '%m/%d/%Y %H:%M',
        '%d/%m/%Y %H:%M:%S',
        '%d/%m/%Y %H:%M',
        '%Y-%m-%d %H:%M:%S',
    ]
    for fmt in formats:
        try:
            return pd.to_datetime(date_str, format=fmt)
        except (ValueError, TypeError):
            continue
    try:
        return pd.to_datetime(date_str)
    except:
        return None

def merge_intervals(intervals):
    if not intervals:
        return []
    intervals.sort(key=lambda x: x[0])
    merged = [list(intervals[0])]
    for start, end in intervals[1:]:
        if start <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], end)
        else:
            merged.append([start, end])
    return merged

def total_duration_from_intervals(intervals):
    merged = merge_intervals(intervals)
    total = timedelta()
    for start, end in merged:
        total += (end - start)
    return total

user_id = int(input("Введите user_id: "))

all_intervals = []

# Ограничения на длительность
MAX_TASK_DURATION = timedelta(hours=2)      # максимум 2 часа на задачу
MAX_TRAINING_DURATION = timedelta(hours=6)  # максимум 6 часов на тренировку
MAX_DAILY_ACTIONS = timedelta(hours=12)     # максимум 12 часов в день из actions

# 1. user_trainings
user_trainings = trainings_df[trainings_df['user_id'] == user_id]
for _, row in user_trainings.iterrows():
    start = parse_date_safe(row['started_at'])
    finish = parse_date_safe(row['finished_at'])
    if start and finish and finish > start:
        duration = finish - start
        if duration > MAX_TRAINING_DURATION:
            duration = MAX_TRAINING_DURATION
        all_intervals.append((start, start + duration))

# 2. user_answers (с ограничением на длительность)
user_answers = answers_df[answers_df['user_id'] == user_id]
for _, row in user_answers.iterrows():
    start = parse_date_safe(row['created_at'])
    finish = parse_date_safe(row['submitted_at'])
    if start and finish and finish > start:
        duration = finish - start
        if duration > MAX_TASK_DURATION:
            duration = MAX_TASK_DURATION
        if duration.total_seconds() > 0:
            all_intervals.append((start, start + duration))

# 3. media_view_sessions
user_media = media_df[media_df['user_id'] == user_id]
for _, row in user_media.iterrows():
    start = parse_date_safe(row['started_at'])
    finish = parse_date_safe(row['finished_at'])
    if start and finish and finish > start:
        all_intervals.append((start, finish))

# 4. wk_users_courses_actions (только в рамках одного дня, макс MAX_DAILY_ACTIONS)
user_actions = actions_df[actions_df['user_id'] == user_id].copy()
user_actions['created_at_parsed'] = user_actions['created_at'].apply(parse_date_safe)
user_actions = user_actions.dropna(subset=['created_at_parsed'])
user_actions = user_actions.sort_values('created_at_parsed')
user_actions['date_only'] = user_actions['created_at_parsed'].dt.date

for date, group in user_actions.groupby('date_only'):
    if len(group) >= 2:
        min_time = group['created_at_parsed'].min()
        max_time = group['created_at_parsed'].max()
        duration = max_time - min_time
        if duration.total_seconds() > 0:
            if duration > MAX_DAILY_ACTIONS:
                duration = MAX_DAILY_ACTIONS
            all_intervals.append((min_time, min_time + duration))

# Объединяем пересекающиеся интервалы
total_duration = total_duration_from_intervals(all_intervals)

# Период активности (для информации)
all_dates = []

user_student = students_df[students_df['user_id'] == user_id]
if not user_student.empty:
    for val in user_student['current_sign_in_at']:
        dt = parse_date_safe(val)
        if dt: all_dates.append(dt)
    for val in user_student['last_sign_in_at']:
        dt = parse_date_safe(val)
        if dt: all_dates.append(dt)

for val in user_trainings['started_at']:
    dt = parse_date_safe(val)
    if dt: all_dates.append(dt)
for val in user_trainings['finished_at']:
    dt = parse_date_safe(val)
    if dt: all_dates.append(dt)

for val in user_answers['created_at']:
    dt = parse_date_safe(val)
    if dt: all_dates.append(dt)
for val in user_answers['submitted_at']:
    dt = parse_date_safe(val)
    if dt: all_dates.append(dt)

for val in user_media['started_at']:
    dt = parse_date_safe(val)
    if dt: all_dates.append(dt)
for val in user_media['finished_at']:
    dt = parse_date_safe(val)
    if dt: all_dates.append(dt)

for val in user_actions['created_at']:
    dt = parse_date_safe(val)
    if dt: all_dates.append(dt)

if all_dates:
    first_activity = min(all_dates)
    last_activity = max(all_dates)
    period_days = (last_activity - first_activity).days
else:
    first_activity = None
    last_activity = None
    period_days = 0

def format_timedelta(td):
    days = td.days
    hours = td.seconds // 3600
    minutes = (td.seconds % 3600) // 60
    seconds = td.seconds % 60
    return days, hours, minutes, seconds

print(f"\n{'='*60}")
print(f"РЕЗУЛЬТАТЫ АНАЛИЗА ДЛЯ user_id = {user_id}")
print(f"{'='*60}\n")

print("⏱️ ОБЩЕЕ ВРЕМЯ НА САЙТЕ:")
days, hours, minutes, seconds = format_timedelta(total_duration)
print(f"  {days} дн {hours} ч {minutes} мин {seconds} сек")

print(f"\n📊 СРАВНЕНИЕ:")
print(f"  Уникальных дней активности: 24")
if days > 0:
    avg_minutes = (total_duration.total_seconds() / 60) / 24
    print(f"  Среднее время в день: {avg_minutes:.1f} минут")

print(f"\n📅 ПЕРИОД АКТИВНОСТИ:")
if first_activity and last_activity:
    print(f"  С {first_activity.strftime('%d.%m.%Y %H:%M:%S')}")
    print(f"  ПО {last_activity.strftime('%d.%m.%Y %H:%M:%S')}")
    print(f"  Длительность периода: {period_days} дней")