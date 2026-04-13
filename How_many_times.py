import pandas as pd
import os
from datetime import datetime, timedelta

# Укажите полный путь к папке с CSV файлами
path_to_folder = r"C:\Users\User\Desktop\Ha-ha-thone\NEW_Hackathon Cifrium. Case ADA\nessesary\INTEREST_in progress"

# Загрузка данных
students_df = pd.read_csv(os.path.join(path_to_folder, 'students_of_interest.csv'), encoding='utf-8-sig')
trainings_df = pd.read_csv(os.path.join(path_to_folder, 'user_trainings.csv'), encoding='utf-8-sig')
answers_df = pd.read_csv(os.path.join(path_to_folder, 'user_answers.csv'), encoding='utf-8-sig')
media_df = pd.read_csv(os.path.join(path_to_folder, 'media_view_sessions.csv'), encoding='utf-8-sig')
actions_df = pd.read_csv(os.path.join(path_to_folder, 'wk_users_courses_actions.csv'), encoding='utf-8-sig')

# Функция для безопасного преобразования дат
def parse_date_safe(date_str):
    """Преобразует строку с датой в Timestamp, пробуя разные форматы"""
    if pd.isna(date_str):
        return None
    
    date_str = str(date_str).strip()
    
    formats = [
        '%d/%m/%y %H:%M',
        '%m/%d/%Y %H:%M',
        '%d/%m/%Y %H:%M',
        '%Y-%m-%d %H:%M:%S',
        '%m/%d/%y %H:%M',
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

# Функция для подсчёта общего количества дней в учебном году (календарных)
def get_total_school_days_calendar(academic_year_str):
    """
    Возвращает количество дней с 1 сентября по 31 мая включительно
    """
    start_year = int(academic_year_str.split('-')[0])
    start_date = datetime(start_year, 9, 1).date()
    end_date = datetime(start_year + 1, 5, 31).date()
    
    delta = end_date - start_date
    return delta.days + 1

# Функция для подсчёта реальных учебных дней (без выходных и праздников)
def get_actual_school_days(academic_year_str):
    """
    Возвращает количество учебных дней с 1 сентября по 31 мая
    (исключая субботы, воскресенья и официальные праздники)
    """
    start_year = int(academic_year_str.split('-')[0])
    start_date = datetime(start_year, 9, 1).date()
    end_date = datetime(start_year + 1, 5, 31).date()
    
    # Список праздников в формате месяц-день
    holiday_month_day = {hd[0] for hd in russian_holidays}
    
    actual_days = 0
    current_date = start_date
    
    while current_date <= end_date:
        # Проверяем, не выходной ли день
        if current_date.weekday() >= 5:  # суббота или воскресенье
            current_date += timedelta(days=1)
            continue
        
        # Проверяем, не праздник ли
        month_day = current_date.strftime('%m-%d')
        if month_day in holiday_month_day:
            current_date += timedelta(days=1)
            continue
        
        actual_days += 1
        current_date += timedelta(days=1)
    
    return actual_days

# Список российских праздников (даты)
russian_holidays = [
    ('01-01', 'Новый год'),
    ('01-02', 'Новогодние каникулы'),
    ('01-03', 'Новогодние каникулы'),
    ('01-04', 'Новогодние каникулы'),
    ('01-05', 'Новогодние каникулы'),
    ('01-06', 'Новогодние каникулы'),
    ('01-07', 'Рождество Христово'),
    ('01-08', 'Новогодние каникулы'),
    ('02-23', 'День защитника Отечества'),
    ('03-08', 'Международный женский день'),
    ('05-01', 'Праздник Весны и Труда'),
    ('05-09', 'День Победы'),
    ('06-12', 'День России'),
    ('11-04', 'День народного единства'),
]

def is_weekend(date):
    """Проверяет, является ли дата выходным днём"""
    return date.weekday() >= 5

def is_holiday(date):
    """Проверяет, является ли дата праздником в России"""
    month_day = date.strftime('%m-%d')
    for hd, name in russian_holidays:
        if month_day == hd:
            return True
    return False

def get_academic_year(date):
    """Определяет учебный год для даты"""
    year = date.year
    month = date.month
    
    if month >= 9:
        return f"{year}-{year+1}"
    elif month <= 5:
        return f"{year-1}-{year}"
    else:
        return "summer"

def get_season_type(date):
    """Определяет тип сезона: учебный год или лето"""
    month = date.month
    if month in [6, 7, 8]:
        return "Летний период"
    else:
        return "Учебный год"

# Запрос user_id
user_id = int(input("Введите user_id: "))

# Сбор всех дат активности (уникальные, без времени)
dates_set = set()

# 1. students_of_interest
user_student = students_df[students_df['user_id'] == user_id]
if not user_student.empty:
    for val in user_student['current_sign_in_at']:
        dt = parse_date_safe(val)
        if dt:
            dates_set.add(dt.date())
    for val in user_student['last_sign_in_at']:
        dt = parse_date_safe(val)
        if dt:
            dates_set.add(dt.date())

# 2. user_trainings
user_trainings = trainings_df[trainings_df['user_id'] == user_id]
for val in user_trainings['started_at']:
    dt = parse_date_safe(val)
    if dt:
        dates_set.add(dt.date())
for val in user_trainings['finished_at']:
    dt = parse_date_safe(val)
    if dt:
        dates_set.add(dt.date())

# 3. user_answers
user_answers = answers_df[answers_df['user_id'] == user_id]
for val in user_answers['created_at']:
    dt = parse_date_safe(val)
    if dt:
        dates_set.add(dt.date())
for val in user_answers['updated_at']:
    dt = parse_date_safe(val)
    if dt:
        dates_set.add(dt.date())

# 4. media_view_sessions
user_media = media_df[media_df['user_id'] == user_id]
for val in user_media['started_at']:
    dt = parse_date_safe(val)
    if dt:
        dates_set.add(dt.date())
for val in user_media['finished_at']:
    dt = parse_date_safe(val)
    if dt:
        dates_set.add(dt.date())

# 5. wk_users_courses_actions
user_actions = actions_df[actions_df['user_id'] == user_id]
for val in user_actions['created_at']:
    dt = parse_date_safe(val)
    if dt:
        dates_set.add(dt.date())

# Сортируем даты
all_dates = sorted(dates_set)

# Анализ по периодам
academic_years = {}  # {учебный год: список дней}
summer_days = []
weekend_days = []
holiday_days = []

for date in all_dates:
    # Определяем выходные
    if is_weekend(date):
        weekend_days.append(date)
    
    # Определяем праздники
    if is_holiday(date):
        holiday_days.append(date)
    
    # Определяем период
    season = get_season_type(date)
    if season == "Учебный год":
        academic_year = get_academic_year(date)
        if academic_year not in academic_years:
            academic_years[academic_year] = []
        academic_years[academic_year].append(date)
    else:
        summer_days.append(date)

# ВЫВОД СПИСКА ВЫХОДНЫХ ДНЕЙ (для проверки)
if weekend_days:
    print(f"\n📅 СПИСОК ВЫХОДНЫХ ДНЕЙ С АКТИВНОСТЬЮ:")
    for d in sorted(weekend_days):
        weekday_name = d.strftime('%A')
        if weekday_name == 'Saturday':
            weekday_name = 'Суббота'
        elif weekday_name == 'Sunday':
            weekday_name = 'Воскресенье'
        print(f"    {d.strftime('%d.%m.%Y')} ({weekday_name})")
else:
    print(f"\n📅 Нет активности в выходные дни")

# Формирование вывода
print(f"\n{'='*60}")
print(f"РЕЗУЛЬТАТЫ АНАЛИЗА ДЛЯ user_id = {user_id}")
print(f"{'='*60}\n")

# 1. Учебные годы (с двумя вариантами процентов)
print("📚 ПОСЕЩЕНИЯ В УЧЕБНЫЕ ГОДЫ:")
for year, days_list in sorted(academic_years.items()):
    visit_count = len(days_list)
    
    # Вариант 1: календарные дни
    total_calendar = get_total_school_days_calendar(year)
    percent_calendar = (visit_count / total_calendar) * 100
    
    # Вариант 2: реальные учебные дни (без выходных и праздников)
    total_actual = get_actual_school_days(year)
    percent_actual = (visit_count / total_actual) * 100 if total_actual > 0 else 0
    
    print(f"  Учебный год {year}: {visit_count} дней")
    print(f"    📅 от всех дней в году: {total_calendar} дней ({percent_calendar:.1f}%)")
    print(f"    📚 от учебных дней: {total_actual} дней ({percent_actual:.1f}%)")
    print(f"    Диапазон: с {min(days_list)} по {max(days_list)}")

# 2. Летний период
print(f"\n☀️ ЛЕТНИЙ ПЕРИОД:")
if summer_days:
    print(f"  Количество дней: {len(summer_days)}")
    print(f"  Диапазон: с {min(summer_days)} по {max(summer_days)}")
else:
    print(f"  Нет посещений в летний период")

# 3. Выходные дни
print(f"\n📅 ВЫХОДНЫЕ ДНИ (суббота, воскресенье):")
if all_dates:
    print(f"  Всего посещений в выходные: {len(weekend_days)} дней из {len(all_dates)} ({len(weekend_days)/len(all_dates)*100:.1f}%)")

# 4. Праздничные дни
print(f"\n🎉 ПРАЗДНИЧНЫЕ ДНИ (Россия):")
if all_dates:
    print(f"  Всего посещений в праздники: {len(holiday_days)} дней из {len(all_dates)} ({len(holiday_days)/len(all_dates)*100:.1f}%)")
if holiday_days:
    print(f"  Праздничные даты: {', '.join([d.strftime('%d.%m.%Y') for d in holiday_days])}")

# 5. Общая статистика
print(f"\n📊 ОБЩАЯ СТАТИСТИКА:")
print(f"  Всего уникальных дней активности: {len(all_dates)}")
print(f"  Самый первый день: {min(all_dates)}")
print(f"  Самый последний день: {max(all_dates)}")

# Диагностика источников
print(f"\n🔍 ДИАГНОСТИКА ИСТОЧНИКОВ:")
print(f"  students_of_interest: {len(user_student)} записей")
print(f"  user_trainings: {len(user_trainings)} записей")
print(f"  user_answers: {len(user_answers)} записей")
print(f"  media_view_sessions: {len(user_media)} записей")
print(f"  wk_users_courses_actions: {len(user_actions)} записей")
print(f"\n  Всего записей (до схлопывания): {len(user_student)*2 + len(user_trainings)*2 + len(user_answers)*2 + len(user_media)*2 + len(user_actions)}")
print(f"  Уникальных дней после схлопывания: {len(dates_set)}")