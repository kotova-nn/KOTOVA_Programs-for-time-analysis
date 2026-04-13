import pandas as pd
import os
from datetime import timedelta, datetime

# Путь к папке с CSV файлами
path_to_folder = r"C:\Users\User\Desktop\Ha-ha-thone\NEW_Hackathon Cifrium. Case ADA\nessesary\INTEREST_in progress"

# Загрузка данных
students_df = pd.read_csv(os.path.join(path_to_folder, 'students_of_interest.csv'), encoding='utf-8-sig')
trainings_df = pd.read_csv(os.path.join(path_to_folder, 'user_trainings.csv'), encoding='utf-8-sig')
answers_df = pd.read_csv(os.path.join(path_to_folder, 'user_answers.csv'), encoding='utf-8-sig')
media_df = pd.read_csv(os.path.join(path_to_folder, 'media_view_sessions.csv'), encoding='utf-8-sig')
actions_df = pd.read_csv(os.path.join(path_to_folder, 'wk_users_courses_actions.csv'), encoding='utf-8-sig')

# Очистка от пустых строк
students_df = students_df.dropna(subset=['user_id'])

# Список российских праздников
russian_holidays = [
    ('01-01', 'Новый год'), ('01-02', 'Новогодние каникулы'), ('01-03', 'Новогодние каникулы'),
    ('01-04', 'Новогодние каникулы'), ('01-05', 'Новогодние каникулы'), ('01-06', 'Новогодние каникулы'),
    ('01-07', 'Рождество Христово'), ('01-08', 'Новогодние каникулы'), ('02-23', 'День защитника Отечества'),
    ('03-08', 'Международный женский день'), ('05-01', 'Праздник Весны и Труда'),
    ('05-09', 'День Победы'), ('06-12', 'День России'), ('11-04', 'День народного единства'),
]

def parse_date_safe(date_str):
    if pd.isna(date_str):
        return None
    date_str = str(date_str).strip()
    formats = [
        '%d/%m/%y %H:%M:%S', '%d/%m/%y %H:%M', '%m/%d/%Y %H:%M:%S', '%m/%d/%Y %H:%M',
        '%d/%m/%Y %H:%M:%S', '%d/%m/%Y %H:%M', '%Y-%m-%d %H:%M:%S',
    ]
    for fmt in formats:
        try:
            return pd.to_datetime(date_str, format=fmt)
        except:
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

def get_academic_year(date):
    year = date.year
    month = date.month
    if month >= 9:
        return f"{year}-{year+1}"
    elif month <= 5:
        return f"{year-1}-{year}"
    return "summer"

def get_total_school_days_calendar(academic_year_str):
    start_year = int(academic_year_str.split('-')[0])
    start_date = datetime(start_year, 9, 1).date()
    end_date = datetime(start_year + 1, 5, 31).date()
    return (end_date - start_date).days + 1

def get_actual_school_days(academic_year_str):
    start_year = int(academic_year_str.split('-')[0])
    start_date = datetime(start_year, 9, 1).date()
    end_date = datetime(start_year + 1, 5, 31).date()
    holiday_month_day = {hd[0] for hd in russian_holidays}
    actual_days = 0
    current_date = start_date
    while current_date <= end_date:
        if current_date.weekday() >= 5:
            current_date += timedelta(days=1)
            continue
        if current_date.strftime('%m-%d') in holiday_month_day:
            current_date += timedelta(days=1)
            continue
        actual_days += 1
        current_date += timedelta(days=1)
    return actual_days

def format_timedelta(td):
    days = td.days
    hours = td.seconds // 3600
    minutes = (td.seconds % 3600) // 60
    seconds = td.seconds % 60
    return days, hours, minutes, seconds

def analyze_user(user_id):
    # 1. Сбор всех временных меток (первая/последняя активность)
    timestamps = []
    
    user_student = students_df[students_df['user_id'] == user_id]
    if not user_student.empty:
        for val in user_student['current_sign_in_at']:
            dt = parse_date_safe(val)
            if dt: timestamps.append(dt)
        for val in user_student['last_sign_in_at']:
            dt = parse_date_safe(val)
            if dt: timestamps.append(dt)
    
    user_trainings = trainings_df[trainings_df['user_id'] == user_id]
    for val in user_trainings['started_at']:
        dt = parse_date_safe(val)
        if dt: timestamps.append(dt)
    for val in user_trainings['finished_at']:
        dt = parse_date_safe(val)
        if dt: timestamps.append(dt)
    
    user_answers = answers_df[answers_df['user_id'] == user_id]
    for val in user_answers['created_at']:
        dt = parse_date_safe(val)
        if dt: timestamps.append(dt)
    for val in user_answers['submitted_at']:
        dt = parse_date_safe(val)
        if dt: timestamps.append(dt)
    
    user_media = media_df[media_df['user_id'] == user_id]
    for val in user_media['started_at']:
        dt = parse_date_safe(val)
        if dt: timestamps.append(dt)
    for val in user_media['finished_at']:
        dt = parse_date_safe(val)
        if dt: timestamps.append(dt)
    
    user_actions = actions_df[actions_df['user_id'] == user_id]
    for val in user_actions['created_at']:
        dt = parse_date_safe(val)
        if dt: timestamps.append(dt)
    
    if timestamps:
        first_activity = min(timestamps)
        last_activity = max(timestamps)
        total_events = len(timestamps)
        period_days = (last_activity - first_activity).days
    else:
        first_activity = last_activity = None
        total_events = 0
        period_days = 0
    
    # 2. Уникальные дни активности
    dates_set = set()
    for dt in timestamps:
        dates_set.add(dt.date())
    all_dates = sorted(dates_set)
    unique_days = len(all_dates)
    
    # 3. Анализ по периодам
    academic_days = {}
    summer_days = []
    weekend_days = []
    holiday_days = []
    holiday_month_day = {hd[0] for hd in russian_holidays}
    
    for date in all_dates:
        if date.weekday() >= 5:
            weekend_days.append(date)
        if date.strftime('%m-%d') in holiday_month_day:
            holiday_days.append(date)
        
        season = get_academic_year(date)
        if season == "summer":
            summer_days.append(date)
        else:
            if season not in academic_days:
                academic_days[season] = []
            academic_days[season].append(date)
    
    # 4. Общее время на сайте (как в X_active_hours.py)
    all_intervals = []
    MAX_TASK_DURATION = timedelta(hours=2)
    MAX_TRAINING_DURATION = timedelta(hours=6)
    MAX_DAILY_ACTIONS = timedelta(hours=12)
    
    # user_trainings
    for _, row in user_trainings.iterrows():
        start = parse_date_safe(row['started_at'])
        finish = parse_date_safe(row['finished_at'])
        if start and finish and finish > start:
            duration = finish - start
            if duration > MAX_TRAINING_DURATION:
                duration = MAX_TRAINING_DURATION
                finish = start + duration
            all_intervals.append((start, finish))
    
    # user_answers
    for _, row in user_answers.iterrows():
        start = parse_date_safe(row['created_at'])
        finish = parse_date_safe(row['submitted_at'])
        if start and finish and finish > start:
            duration = finish - start
            if duration > MAX_TASK_DURATION:
                duration = MAX_TASK_DURATION
                finish = start + duration
            if duration.total_seconds() > 0:
                all_intervals.append((start, finish))
    
    # media_view_sessions
    for _, row in user_media.iterrows():
        start = parse_date_safe(row['started_at'])
        finish = parse_date_safe(row['finished_at'])
        if start and finish and finish > start:
            all_intervals.append((start, finish))
    
    # wk_users_courses_actions
    if len(user_actions) > 0:
        actions_parsed = user_actions['created_at'].apply(parse_date_safe).dropna()
        if len(actions_parsed) > 1:
            actions_df_temp = pd.DataFrame({'created_at_parsed': actions_parsed})
            actions_df_temp['date_only'] = actions_df_temp['created_at_parsed'].dt.date
            for date, group in actions_df_temp.groupby('date_only'):
                if len(group) >= 2:
                    min_time = group['created_at_parsed'].min()
                    max_time = group['created_at_parsed'].max()
                    duration = max_time - min_time
                    if duration > MAX_DAILY_ACTIONS:
                        duration = MAX_DAILY_ACTIONS
                        max_time = min_time + duration
                    if duration.total_seconds() > 0:
                        all_intervals.append((min_time, max_time))
    
    # Объединяем пересекающиеся интервалы
    total_duration = total_duration_from_intervals(all_intervals)
    
    # Форматируем результат
    total_days, total_hours, total_minutes, total_seconds_only = format_timedelta(total_duration)
    total_time_str = f"{total_days} дн {total_hours} ч {total_minutes} мин {total_seconds_only} сек"
    avg_minutes_per_day = (total_duration.total_seconds() / 60) / unique_days if unique_days > 0 else 0
    
    # Формируем результат
    academic_year_key = list(academic_days.keys())[0] if academic_days else None
    school_days_visited = len(academic_days.get(academic_year_key, [])) if academic_year_key else 0
    total_calendar = get_total_school_days_calendar(academic_year_key) if academic_year_key else 0
    total_actual = get_actual_school_days(academic_year_key) if academic_year_key else 0
    percent_calendar = round(school_days_visited / total_calendar * 100, 1) if total_calendar > 0 else 0
    percent_actual = round(school_days_visited / total_actual * 100, 1) if total_actual > 0 else 0
    
    result = {
        'user_id': user_id,
        'first_activity': first_activity.strftime('%d.%m.%Y %H:%M:%S') if first_activity else None,
        'last_activity': last_activity.strftime('%d.%m.%Y %H:%M:%S') if last_activity else None,
        'total_events': total_events,
        'unique_days': unique_days,
        'academic_year': academic_year_key,
        'school_days_visited': school_days_visited,
        'total_school_days_calendar': total_calendar,
        'percent_of_calendar': percent_calendar,
        'total_school_days_actual': total_actual,
        'percent_of_actual_school': percent_actual,
        'summer_days': len(summer_days),
        'weekend_days': len(weekend_days),
        'holiday_days': len(holiday_days),
        'total_time_on_site': total_time_str,
        'avg_minutes_per_day': round(avg_minutes_per_day, 1),
        'period_days': period_days,
    }
    return result

# Сбор данных для всех пользователей
all_users = students_df['user_id'].unique()
results = []

print("Начинаем сбор данных...")
for uid in all_users:
    print(f"  Обработка user_id = {uid}...")
    try:
        result = analyze_user(int(uid))
        results.append(result)
    except Exception as e:
        print(f"    Ошибка: {e}")
        results.append({'user_id': uid, 'error': str(e)})

# Сохраняем в CSV с десятичной запятой для Excel
df_results = pd.DataFrame(results)
output_path = os.path.join(path_to_folder, 'user_analysis_report.csv')
df_results.to_csv(output_path, index=False, encoding='utf-8-sig', decimal=',')
print(f"\n✅ Отчёт сохранён: {output_path}")

# Выводим таблицу в консоль
print(f"\n{'='*100}")
print("СВОДНАЯ ТАБЛИЦА ПО ВСЕМ ПОЛЬЗОВАТЕЛЯМ")
print(f"{'='*100}\n")
print(df_results.to_string(index=False))