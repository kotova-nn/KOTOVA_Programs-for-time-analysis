""" 
Команда Фруктовый Сад. Хакатом МФТИ апрель 2026. 
Кейс 2. (ADA) Наглядный итоговый отчет об активности ученика на платформе Цифриум
Авторы программы: Шандра Иван, Котова Наталья 

"""
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime, timedelta
import sys
import warnings
import os
from collections import defaultdict, Counter
import json
import io

# Настройка кодировки вывода
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

warnings.filterwarnings('ignore')
sns.set_style("whitegrid")
plt.rcParams['figure.figsize'] = (12, 6)
#===========================================================================================================================
#                                                      КОНФИГУРАЦИЯ 
# ==========================================================================================================================
DATA_PATH = 'C:/Base/Hackathon/Hackathon Cifrium. Case ADA/NewData'

RUSSIAN_HOLIDAYS = {
    '01-01', '01-02', '01-03', '01-04', '01-05', '01-06', '01-07', '01-08',
    '02-23', '03-08', '05-01', '05-09', '06-12', '11-04'
}

MAX_TASK_DURATION = timedelta(hours=2)
MAX_TRAINING_DURATION = timedelta(hours=6)
MAX_DAILY_ACTIONS = timedelta(hours=12)
MAX_MEDIA_DURATION = timedelta(hours=4)
#===========================================================================================================================
#                                                ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ==========================================================================================================================

def get_user_id():
    if len(sys.argv) > 1:
        try:
            return int(sys.argv[1])
        except ValueError:
            print("Ошибка: аргумент должен быть числом. Использую ввод с клавиатуры.")
    try:
        return int(input("Введите user_id интересующего студента: "))
    except ValueError:
        print("Некорректный ввод. Завершение программы.")
        sys.exit(1)

def parse_date(date_str):
    if pd.isna(date_str):
        return None
    date_str = str(date_str).strip()
    formats = [
        '%d/%m/%y %H:%M:%S', '%d/%m/%y %H:%M',
        '%m/%d/%Y %H:%M:%S', '%m/%d/%Y %H:%M',
        '%d/%m/%Y %H:%M:%S', '%d/%m/%Y %H:%M',
        '%Y-%m-%d %H:%M:%S',
        '%d %b, %Y, %H:%M', '%d %b, %Y, %H:%M:%S',
        '%b %d, %Y, %H:%M', '%b %d, %Y, %H:%M:%S',
    ]
    for fmt in formats:
        try:
            dt = pd.to_datetime(date_str, format=fmt)
            if dt.tzinfo is not None:
                dt = dt.tz_localize(None)
            return dt
        except (ValueError, TypeError):
            continue
    try:
        dt = pd.to_datetime(date_str)
        if dt.tzinfo is not None:
            dt = dt.tz_localize(None)
        return dt
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

def total_duration(intervals):
    merged = merge_intervals(intervals)
    total = timedelta()
    for s, e in merged:
        total += (e - s)
    return total

def get_academic_year(date):
    year = date.year
    if date.month >= 9:
        return f"{year}-{year+1}"
    elif date.month <= 5:
        return f"{year-1}-{year}"
    else:
        return "summer"

def is_holiday(date):
    return date.strftime('%m-%d') in RUSSIAN_HOLIDAYS

def is_weekend(date):
    return date.weekday() >= 5

def get_school_days_in_year(academic_year_str, exclude_holidays_weekends=True):
    start_year = int(academic_year_str.split('-')[0])
    start = datetime(start_year, 9, 1).date()
    end = datetime(start_year + 1, 5, 31).date()
    if exclude_holidays_weekends:
        days = 0
        d = start
        while d <= end:
            if not is_weekend(d) and not is_holiday(d):
                days += 1
            d += timedelta(days=1)
        return days
    else:
        return (end - start).days + 1

def safe_filter(df, user_col_candidates, df_name, user_id):
    for col in user_col_candidates:
        if col in df.columns:
            return df[df[col] == user_id]
    print(f"⚠️ В таблице {df_name} не найдены столбцы {user_col_candidates}. Фильтрация не выполнена.")
    return df

def safe_get_columns(df, candidates, default=None):
    for col in candidates:
        if col in df.columns:
            return col
    return default

def filter_df_by_period(df, start_date, end_date, date_columns):
    """Фильтрует DataFrame по временным колонкам, оставляя записи в заданном периоде."""
    if df.empty or start_date is None or end_date is None:
        return df
    mask = pd.Series([False] * len(df), index=df.index)
    for col in date_columns:
        if col in df.columns:
            dates = df[col].apply(parse_date)
            col_mask = (dates >= start_date) & (dates <= end_date)
            mask = mask | col_mask
    return df[mask].copy()
#===========================================================================================================================
#                                                   ВЫБОР ПЕРИОДА АНАЛИЗА   
# ==========================================================================================================================

def select_period():
    """Интерактивный выбор периода анализа."""
    print("\nВыберите период для анализа:")
    print("  1. Всё время")
    print("  2. Триместр")
    print("  3. Произвольный диапазон дат")
    
    choice = input("Ваш выбор (1-3, по умолчанию 1): ").strip() or "1"
    
    if choice == "1":
        return None, None  # всё время
    
    
    elif choice == "2":
        print("\nДоступные триместры:")
        print("  1 триместр: 1 сентября – 14 ноября")
        print("  2 триместр: 24 ноября – 20 февраля")
        print("  3 триместр: 2 марта – 22 мая")
        trim = input("Введите номер триместра (1, 2 или 3): ").strip()
        year = input("Введите учебный год в формате YYYY-YYYY (например, 2025-2026): ").strip()
        try:
            start_year = int(year.split('-')[0])
            if trim == "1":
                start_date = datetime(start_year, 9, 1)
                end_date = datetime(start_year, 11, 14, 23, 59, 59)
            elif trim == "2":
                start_date = datetime(start_year, 11, 24)
                end_date = datetime(start_year + 1, 2, 20, 23, 59, 59)
            elif trim == "3":
                start_date = datetime(start_year + 1, 3, 2)
                end_date = datetime(start_year + 1, 5, 22, 23, 59, 59)
            else:
                raise ValueError
            return start_date, end_date
        except:
            print("Неверный формат. Использую всё время.")
            return None, None
    
    
    elif choice == "3":
        start_str = input("Введите начальную дату в формате ДД.ММ.ГГГГ: ").strip()
        end_str = input("Введите конечную дату в формате ДД.ММ.ГГГГ: ").strip()
        try:
            start_date = datetime.strptime(start_str, "%d.%m.%Y")
            end_date = datetime.strptime(end_str, "%d.%m.%Y") + timedelta(days=1) - timedelta(seconds=1)
            return start_date, end_date
        except:
            print("Неверный формат. Использую всё время.")
            return None, None
    
    else:
        return None, None
#===========================================================================================================================
#                                                        ЗАГРУЗКА ДАННЫХ          
# ==========================================================================================================================

def load_filtered_data(user_id):
    data = {}
    
    # 1. students_of_interest
    df = pd.read_csv(os.path.join(DATA_PATH, 'students_of_interest.csv'), encoding='utf-8')
    df = df.dropna(how='all')
    data['students_info'] = safe_filter(df, ['user_id', 'id'], 'students_of_interest', user_id)
    if not data['students_info'].empty:
        if 'id' in data['students_info'].columns and 'user_id' not in data['students_info'].columns:
            data['students_info'].rename(columns={'id': 'user_id'}, inplace=True)
    
    # 2. courses_stats
    df = pd.read_csv(os.path.join(DATA_PATH, 'courses_stats.csv'), encoding='utf-8')
    data['courses_stats'] = safe_filter(df, ['user_id'], 'courses_stats', user_id)
    
    # 3. user_courses
    df = pd.read_csv(os.path.join(DATA_PATH, 'user_courses.csv'), encoding='utf-8')
    data['user_courses'] = safe_filter(df, ['user_id'], 'user_courses', user_id)
    
    # 4. user_trainings
    df = pd.read_csv(os.path.join(DATA_PATH, 'user_trainings.csv'), encoding='utf-8')
    data['user_trainings'] = safe_filter(df, ['user_id'], 'user_trainings', user_id)
    
    # 5. user_lessons
    df = pd.read_csv(os.path.join(DATA_PATH, 'user_lessons.csv'), encoding='utf-8')
    data['user_lessons'] = safe_filter(df, ['user_id'], 'user_lessons', user_id)
    
    # 6. lessons
    lessons_path = os.path.join(DATA_PATH, 'lessons.csv')
    if os.path.exists(lessons_path):
        data['lessons'] = pd.read_csv(lessons_path, encoding='utf-8')
    else:
        data['lessons'] = pd.DataFrame()
    
    # 7. trainings
    trainings_path = os.path.join(DATA_PATH, 'trainings.csv')
    if os.path.exists(trainings_path):
        data['trainings'] = pd.read_csv(trainings_path, encoding='utf-8')
    else:
        data['trainings'] = pd.DataFrame()
    
    # 8. Награды
    award_badges_path = os.path.join(DATA_PATH, 'award_badges.csv')
    if os.path.exists(award_badges_path):
        award_badges = pd.read_csv(award_badges_path, encoding='utf-8')
    else:
        award_badges = pd.DataFrame()
    user_awards = pd.read_csv(os.path.join(DATA_PATH, 'user_award_badges.csv'), encoding='utf-8')
    user_awards = safe_filter(user_awards, ['user_id'], 'user_award_badges', user_id)
    if not user_awards.empty and not award_badges.empty:
        if 'user_id' in award_badges.columns:
            data['awards'] = user_awards.merge(award_badges, left_on='award_badge_id', right_on='user_id', how='left')
        else:
            data['awards'] = user_awards
    else:
        data['awards'] = user_awards
    
    # 9. user_answers
    data['user_answers'] = pd.DataFrame()
    answers_path = os.path.join(DATA_PATH, 'user_answers.csv')
    if os.path.exists(answers_path):
        for chunk in pd.read_csv(answers_path, encoding='utf-8', chunksize=50000):
            filtered = safe_filter(chunk, ['user_id'], 'user_answers', user_id)
            if not filtered.empty:
                data['user_answers'] = pd.concat([data['user_answers'], filtered], ignore_index=True)
    
    # 10. user_actions (wk_users_courses_actions)
    data['user_actions'] = pd.DataFrame()
    actions_path = os.path.join(DATA_PATH, 'wk_users_courses_actions.csv')
    if os.path.exists(actions_path):
        for chunk in pd.read_csv(actions_path, encoding='utf-8', chunksize=50000):
            filtered = safe_filter(chunk, ['user_id'], 'wk_users_courses_actions', user_id)
            if not filtered.empty:
                data['user_actions'] = pd.concat([data['user_actions'], filtered], ignore_index=True)
    
    # 11. media_view_sessions
    data['media_sessions'] = pd.DataFrame()
    media_path = os.path.join(DATA_PATH, 'media_view_sessions.csv')
    if os.path.exists(media_path):
        try:
            for chunk in pd.read_csv(media_path, encoding='utf-8', chunksize=50000, thousands=',', quotechar='"'):
                if 'viewer_id' in chunk.columns:
                    chunk.rename(columns={'viewer_id': 'user_id'}, inplace=True)
                if 'segment_size' in chunk.columns:
                    chunk['segment_size'] = pd.to_numeric(chunk['segment_size'], errors='coerce')
                if 'viewed_segments_count' in chunk.columns:
                    chunk['viewed_segments_count'] = pd.to_numeric(chunk['viewed_segments_count'], errors='coerce')
                filtered = safe_filter(chunk, ['user_id'], 'media_view_sessions', user_id)
                if not filtered.empty:
                    data['media_sessions'] = pd.concat([data['media_sessions'], filtered], ignore_index=True)
        except Exception as e:
            print(f"Ошибка при загрузке media_view_sessions: {e}")
    
    # 12. students_popular_time
    data['popular_time'] = pd.DataFrame()
    pt_path = os.path.join(DATA_PATH, 'students_popular_time.csv')
    if os.path.exists(pt_path):
        pt_df = pd.read_csv(pt_path, encoding='utf-8-sig', sep=';')
        pt_df = pt_df.dropna(subset=['user_id'])
        pt_df['user_id'] = pt_df['user_id'].astype(int)
        data['popular_time'] = pt_df[pt_df['user_id'] == user_id]
    
    return data
#===========================================================================================================================
#                                               АНАЛИЗ ВРЕМЕНИ НА ПЛАТФОРМЕ       
# ==========================================================================================================================

def compute_time_intervals(data):
    intervals = []
    
    # Тренинги
    ut = data['user_trainings']
    if not ut.empty:
        start_col = safe_get_columns(ut, ['started_at'])
        end_col = safe_get_columns(ut, ['finished_at'])
        if start_col and end_col:
            for _, row in ut.iterrows():
                start = parse_date(row[start_col])
                end = parse_date(row[end_col])
                if start and end and end > start:
                    dur = end - start
                    if dur > MAX_TRAINING_DURATION:
                        dur = MAX_TRAINING_DURATION
                        end = start + dur
                    intervals.append((start, end))
    
    # Ответы
    ua = data['user_answers']
    if not ua.empty:
        start_col = safe_get_columns(ua, ['created_at'])
        end_col = safe_get_columns(ua, ['submitted_at', 'updated_at', 'finished_at'])
        if start_col and end_col:
            for _, row in ua.iterrows():
                start = parse_date(row[start_col])
                end = parse_date(row[end_col])
                if start and end and end > start:
                    dur = end - start
                    if dur > MAX_TASK_DURATION:
                        dur = MAX_TASK_DURATION
                        end = start + dur
                    if dur.total_seconds() > 0:
                        intervals.append((start, end))
    
    # Медиа
    ms = data['media_sessions']
    if not ms.empty:
        start_col = safe_get_columns(ms, ['started_at'])
        if start_col:
            for _, row in ms.iterrows():
                start = parse_date(row[start_col])
                if not start:
                    continue
                duration = None
                if 'finished_at' in ms.columns:
                    end = parse_date(row['finished_at'])
                    if end and end > start:
                        duration = end - start
                elif 'viewed_segments_count' in ms.columns and 'segment_size' in ms.columns:
                    try:
                        cnt = int(row['viewed_segments_count']) if pd.notna(row['viewed_segments_count']) else 0
                        sz = int(row['segment_size']) if pd.notna(row['segment_size']) else 0
                        if cnt > 0 and sz > 0:
                            duration = timedelta(seconds=cnt * sz)
                    except:
                        pass
                elif 'duration' in ms.columns:
                    try:
                        duration = timedelta(seconds=float(row['duration']))
                    except:
                        pass
                if duration and duration.total_seconds() > 0:
                    if duration > MAX_MEDIA_DURATION:
                        duration = MAX_MEDIA_DURATION
                    intervals.append((start, start + duration))
    
    # Действия (по дням)
    ua = data['user_actions']
    if not ua.empty:
        col = safe_get_columns(ua, ['created_at'])
        if col:
            actions = ua.copy()
            actions['dt'] = actions[col].apply(parse_date)
            actions = actions.dropna(subset=['dt'])
            if not actions.empty:
                actions['date'] = actions['dt'].dt.date
                for date, group in actions.groupby('date'):
                    if len(group) >= 2:
                        min_t = group['dt'].min()
                        max_t = group['dt'].max()
                        dur = max_t - min_t
                        if dur.total_seconds() > 0:
                            if dur > MAX_DAILY_ACTIONS:
                                dur = MAX_DAILY_ACTIONS
                                max_t = min_t + dur
                            intervals.append((min_t, max_t))
    
    return intervals

def analyze_time_and_days(data, intervals):
    all_dates = set()
    for s, e in intervals:
        all_dates.add(s.date())
        all_dates.add(e.date())
    
    si = data['students_info']
    if not si.empty:
        for col in ['current_sign_in_at', 'last_sign_in_at']:
            if col in si.columns:
                for val in si[col]:
                    dt = parse_date(val)
                    if dt:
                        all_dates.add(dt.date())
    
    unique_days = sorted(all_dates)
    academic = {}
    summer = []
    weekend = []
    holiday = []
    
    for d in unique_days:
        if is_weekend(d):
            weekend.append(d)
        if is_holiday(d):
            holiday.append(d)
        ay = get_academic_year(d)
        if ay == 'summer':
            summer.append(d)
        else:
            academic.setdefault(ay, []).append(d)
    
    total_td = total_duration(intervals)
    first_activity = min([s for s, e in intervals]) if intervals else None
    last_activity = max([e for s, e in intervals]) if intervals else None
    period_days = (last_activity - first_activity).days if first_activity and last_activity else 0
    
    return {
        'total_time': total_td,
        'unique_days': len(unique_days),
        'first_activity': first_activity,
        'last_activity': last_activity,
        'period_days': period_days,
        'academic_days': academic,
        'summer_days': len(summer),
        'weekend_days': len(weekend),
        'holiday_days': len(holiday),
        'all_dates': unique_days,
    }
#===========================================================================================================================
#                                                 АНАЛИЗ УСПЕВАЕМОСТИ        
# ==========================================================================================================================

def analyze_performance(data):
    perf = {}
    cs = data['courses_stats']
    if not cs.empty:
        row = cs.iloc[0]
        for ru_col in ['Регион', 'Муниципалитет', 'Школа', 'Класс',
                       'Всего просмотров уроков', 'Из них онлайн', 'Из них в записи',
                       'Решал задач', 'Всего задач', 'Набрал баллов', 'Всего баллов']:
            if ru_col in cs.columns:
                perf[ru_col] = row[ru_col]
    
    uc = data['user_courses']
    if not uc.empty:
        row = uc.iloc[0]
        for en_col in ['wk_points', 'wk_max_points', 'wk_solved_task_count']:
            if en_col in uc.columns:
                perf[en_col] = row[en_col]
    
    ut = data['user_trainings']
    if not ut.empty:
        perf['trainings_count'] = len(ut)
        if 'mark' in ut.columns:
            perf['avg_mark'] = ut['mark'].mean()
        if 'earned_points' in ut.columns:
            perf['total_earned_points'] = ut['earned_points'].sum()
    
    ua = data['user_answers']
    if not ua.empty:
        perf['total_answers'] = len(ua)
        if 'solved' in ua.columns:
            perf['solved_answers'] = ua['solved'].sum()
        if 'points' in ua.columns:
            perf['avg_points_per_answer'] = ua['points'].mean()
        if 'attempts' in ua.columns:
            perf['avg_attempts'] = ua['attempts'].mean()
    
    ul = data['user_lessons']
    if not ul.empty:
        if 'video_visited' in ul.columns:
            perf['lessons_video_visited'] = ul['video_visited'].sum()
        if 'solved' in ul.columns:
            perf['lessons_solved'] = ul['solved'].sum()
    
    if 'wk_points' in perf and 'wk_max_points' in perf and perf['wk_max_points']:
        user_percent = (perf['wk_points'] / perf['wk_max_points']) * 100
        all_uc_path = os.path.join(DATA_PATH, 'user_courses.csv')
        if os.path.exists(all_uc_path):
            all_uc = pd.read_csv(all_uc_path, encoding='utf-8')
            all_percents = []
            for _, row in all_uc.iterrows():
                if row['wk_max_points'] > 0:
                    all_percents.append((row['wk_points'] / row['wk_max_points']) * 100)
            if all_percents:
                better_than = (np.array(all_percents) < user_percent).mean() * 100
                perf['course_percent'] = user_percent
                perf['better_than_percent'] = better_than
    
    awards = data['awards']
    if not awards.empty:
        cols = []
        for c in ['title', 'level', 'created_at']:
            if c in awards.columns:
                cols.append(c)
        if cols:
            perf['awards'] = awards[cols].to_dict('records')
    
    return perf

def analyze_course_time(data):
    ul = data['user_lessons']
    lessons = data['lessons']
    if ul.empty or lessons.empty:
        return None
    if 'lesson_id' not in ul.columns:
        return None
    if 'id' not in lessons.columns or 'course_id' not in lessons.columns or 'wk_video_duration' not in lessons.columns:
        return None
    merged = ul.merge(
        lessons[['id', 'course_id', 'wk_video_duration']],
        left_on='lesson_id', right_on='id', how='left'
    )
    visited = merged[merged['video_visited'] == True]
    if visited.empty:
        return None
    course_time = visited.groupby('course_id')['wk_video_duration'].sum().dropna()
    return course_time.sort_values(ascending=False)

#===========================================================================================================================
#                                             АНАЛИЗ НЕДЕЛЬНОЙ АКТИВНОСТИ         
# ==========================================================================================================================
DAYS_RU_TO_EN = {
    'Понедельник': 'Monday', 'Вторник': 'Tuesday', 'Среда': 'Wednesday',
    'Четверг': 'Thursday', 'Пятница': 'Friday', 'Суббота': 'Saturday', 'Воскресенье': 'Sunday'
}
DAYS_EN_TO_RU = {v: k for k, v in DAYS_RU_TO_EN.items()}
WEEKDAY_ORDER = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']

DAY_CHARACTERISTICS = {
    'Monday': {'name_ru': 'Понедельник', 'type': '🔋 Энерджайзер', 'slogan': 'Задаю тон неделе. Заряжаюсь с понедельника.'},
    'Tuesday': {'name_ru': 'Вторник', 'type': '🧘 Дзен-мастер', 'slogan': 'Середина недели — моя зона комфорта. Работаю без стресса.'},
    'Wednesday': {'name_ru': 'Среда', 'type': '🧘 Дзен-мастер', 'slogan': 'Середина недели — моя зона комфорта. Работаю без стресса.'},
    'Thursday': {'name_ru': 'Четверг', 'type': '🚀 Финишный ускоритель', 'slogan': 'Разгоняюсь к концу недели. Главные дела — в четверг.'},
    'Friday': {'name_ru': 'Пятница', 'type': '🎮 Финальный босс', 'slogan': 'В пятницу становлюсь легендой. Побеждаю главные вызовы недели.'},
    'Saturday': {'name_ru': 'Суббота', 'type': '⚔️ Уикенд-воин', 'slogan': 'Выходные — моя боевая готовность. Главные битвы в субботу.'},
    'Sunday': {'name_ru': 'Воскресенье', 'type': '⚔️ Уикенд-воин', 'slogan': 'Выходные — моя боевая готовность. Главные битвы в воскресенье.'}
}

def analyze_weekly_activity(data):
    pt = data.get('popular_time')
    if pt is None or pt.empty:
        return None
    
    day_counts = Counter()
    for _, row in pt.iterrows():
        day_ru = row.get('день недели')
        if pd.notna(day_ru):
            day_en = DAYS_RU_TO_EN.get(day_ru, day_ru)
            day_counts[day_en] += 1
    
    total = sum(day_counts.values())
    if total == 0:
        return None
    
    day_percents = {}
    for day in WEEKDAY_ORDER:
        cnt = day_counts.get(day, 0)
        day_percents[day] = {'count': cnt, 'percent': round(cnt/total*100, 1)}
    
    max_count = max(day_counts.values())
    most_active = [d for d, c in day_counts.items() if c == max_count]
    most_active.sort(key=lambda d: WEEKDAY_ORDER.index(d))
    
    active_info = []
    for day in most_active:
        info = DAY_CHARACTERISTICS.get(day, {})
        active_info.append({
            'day_ru': info.get('name_ru', day),
            'type': info.get('type', 'Неизвестно'),
            'slogan': info.get('slogan', '')
        })
    
    weekday_sess = sum(day_counts.get(d,0) for d in ['Monday','Tuesday','Wednesday','Thursday','Friday'])
    weekend_sess = sum(day_counts.get(d,0) for d in ['Saturday','Sunday'])
    wday_pct = round(weekday_sess/total*100,1)
    wend_pct = round(weekend_sess/total*100,1)
    
    if 40 <= wday_pct <= 60:
        act_type = '🌊 Гибкий поток'
        act_slogan = 'Учусь когда хочу. График не властен надо мной.'
    elif wday_pct > wend_pct:
        act_type = '🏢 Король будней'
        act_slogan = 'В будни я в тонусе. Учебный ритм — моё всё.'
    else:
        act_type = '🏆 Уикенд-чемпион'
        act_slogan = 'Выходные созданы для побед. Пять дней жду субботы.'
    
    return {
        'total_sessions': total,
        'day_percents': day_percents,
        'most_active_days': most_active,
        'active_day_info': active_info,
        'weekday_percent': wday_pct,
        'weekend_percent': wend_pct,
        'activity_type': act_type,
        'activity_slogan': act_slogan
    }

#===========================================================================================================================
#                                                 АНАЛИЗ БИОРИТМОВ     
# ==========================================================================================================================

def get_hour_from_time(time_str):
    if pd.isna(time_str):
        return None
    try:
        return int(str(time_str).split(':')[0])
    except:
        return None

def classify_session_time(hour):
    if hour is None:
        return 'unknown'
    if 4 <= hour < 12:
        return 'morning'
    elif 12 <= hour < 18:
        return 'day'
    else:
        return 'night'

def get_confidence_level(n):
    if n >= 20: return 'high'
    if n >= 10: return 'medium'
    if n >= 5: return 'low'
    return 'insufficient'

def analyze_circadian_rhythm(data):
    pt = data.get('popular_time')
    if pt is None or pt.empty:
        return None
    
    n = len(pt)
    if n == 0:
        return None
    
    morning = day = night = 0
    for _, row in pt.iterrows():
        h = get_hour_from_time(row.get('начало сессии'))
        t = classify_session_time(h)
        if t == 'morning': morning += 1
        elif t == 'day': day += 1
        elif t == 'night': night += 1
    
    m_pct = round(morning/n*100,1)
    d_pct = round(day/n*100,1)
    n_pct = round(night/n*100,1)
    conf = get_confidence_level(n)
    
    if conf == 'insufficient':
        rhythm_type = 'unknown'
        classification = 'Недостаточно данных'
        prob_note = f"Недостаточно данных (всего {n} сессий)"
    elif m_pct >= 50:
        rhythm_type = 'morning_lark'
        classification = 'Явный жаворонок'
        prob_note = f"Вероятность ~{m_pct}% на основе {n} сессий"
    elif n_pct >= 50:
        rhythm_type = 'night_owl'
        classification = 'Явная сова'
        prob_note = f"Вероятность ~{n_pct}% на основе {n} сессий"
    elif m_pct >= 35 and n_pct >= 35:
        rhythm_type = 'mixed'
        classification = 'Смешанный тип'
        prob_note = f"Активен и утром ({m_pct}%), и вечером ({n_pct}%)"
    elif m_pct > n_pct:
        rhythm_type = 'leaning_morning'
        classification = 'Склонен к утреннему типу'
        prob_note = f"Утро {m_pct}% против вечера {n_pct}%"
    elif n_pct > m_pct:
        rhythm_type = 'leaning_night'
        classification = 'Склонен к вечернему типу'
        prob_note = f"Вечер {n_pct}% против утра {m_pct}%"
    else:
        rhythm_type = 'day_oriented'
        classification = 'Дневной тип'
        prob_note = f"Активность в середине дня ({d_pct}%)"
    
    return {
        'rhythm_type': rhythm_type,
        'classification': classification,
        'morning_percent': m_pct,
        'day_percent': d_pct,
        'night_percent': n_pct,
        'num_sessions': n,
        'confidence': conf,
        'probability_note': prob_note
    }

#===========================================================================================================================
#                                           ПОИСК САМОГО ПРОДУКТИВНОГО ДНЯ               
# ==========================================================================================================================

def collect_productivity_data(data, start_date=None, end_date=None):
    videos = defaultdict(int)
    tasks = defaultdict(int)
    points = defaultdict(float)
    badges_by_day = defaultdict(list)

    def in_period(dt):
        if dt is None:
            return False
        if start_date and dt < start_date:
            return False
        if end_date and dt > end_date:
            return False
        return True

    # 1. Видео из wk_users_courses_actions
    ua = data['user_actions']
    if not ua.empty and 'action' in ua.columns and 'created_at' in ua.columns:
        for _, row in ua.iterrows():
            if row['action'] == 'visit_video':
                dt = parse_date(row['created_at'])
                if in_period(dt):
                    videos[dt.date()] += 1

    # 2. Видео из user_lessons
    ul = data['user_lessons']
    if not ul.empty and 'video_visited' in ul.columns:
        col_cr = safe_get_columns(ul, ['created_at'])
        if col_cr:
            for _, row in ul.iterrows():
                if row['video_visited'] == True:
                    dt = parse_date(row[col_cr])
                    if in_period(dt):
                        videos[dt.date()] += 1

    # 3. Видео из media_sessions
    ms = data['media_sessions']
    if not ms.empty:
        col_st = safe_get_columns(ms, ['started_at'])
        if col_st:
            for _, row in ms.iterrows():
                dt = parse_date(row[col_st])
                if in_period(dt):
                    videos[dt.date()] += 1

    # 4. Решённые задачи и баллы из user_answers
    uans = data['user_answers']
    if not uans.empty:
        col_cr = safe_get_columns(uans, ['created_at'])
        if col_cr and 'solved' in uans.columns:
            for _, row in uans.iterrows():
                if row['solved'] == True:
                    dt = parse_date(row[col_cr])
                    if in_period(dt):
                        tasks[dt.date()] += 1
                        results = row.get('results')
                        if pd.notna(results) and results:
                            try:
                                results_list = json.loads(results)
                                for result in results_list:
                                    for task_id, task_data in result.items():
                                        pts = task_data.get('points', 0)
                                        points[dt.date()] += pts
                            except:
                                pass

    # 5. Баллы из user_trainings
    ut = data['user_trainings']
    if not ut.empty:
        col_st = safe_get_columns(ut, ['started_at'])
        if col_st and 'earned_points' in ut.columns:
            for _, row in ut.iterrows():
                pts = row['earned_points']
                if pts > 0:
                    dt = parse_date(row[col_st])
                    if in_period(dt):
                        points[dt.date()] += pts

    # 6. Баллы из user_lessons
    if not ul.empty and 'wk_points' in ul.columns:
        col_cr = safe_get_columns(ul, ['created_at'])
        if col_cr:
            for _, row in ul.iterrows():
                pts = row['wk_points']
                if pts and pts > 0:
                    dt = parse_date(row[col_cr])
                    if in_period(dt):
                        points[dt.date()] += pts

    # 7. Награды
    awards = data['awards']
    if not awards.empty:
        col_cr = safe_get_columns(awards, ['created_at'])
        if col_cr:
            for _, row in awards.iterrows():
                dt = parse_date(row[col_cr])
                if in_period(dt):
                    points[dt.date()] += 1
                    title = row.get('title', 'Награда')
                    level = row.get('level', '')
                    if level and pd.notna(level):
                        title = f"{title} (ур. {int(level)})"
                    badges_by_day[dt.date()].append({'title': title})

    return videos, tasks, points, badges_by_day

def find_most_productive_day(data, start_date=None, end_date=None):
    videos, tasks, points, badges = collect_productivity_data(data, start_date, end_date)
    all_dates = set(videos.keys()) | set(tasks.keys()) | set(points.keys())
    if not all_dates:
        return None

    if start_date is None and end_date is None:
        first_date = min(all_dates)
        if first_date.month >= 9:
            period_start = datetime(first_date.year, 9, 1)
            period_end = datetime(first_date.year + 1, 5, 31, 23, 59, 59)
        else:
            period_start = datetime(first_date.year - 1, 9, 1)
            period_end = datetime(first_date.year, 5, 31, 23, 59, 59)
    else:
        period_start = start_date if start_date else min(all_dates)
        period_end = end_date if end_date else max(all_dates)

    filtered_dates = [d for d in all_dates if period_start.date() <= d <= period_end.date()]
    if not filtered_dates:
        return None

    productivity = {}
    for d in filtered_dates:
        productivity[d] = videos.get(d, 0) + tasks.get(d, 0) + points.get(d, 0)

    max_prod = max(productivity.values())
    best_days = [d for d, p in productivity.items() if p == max_prod]
    best_days.sort()

    results = []
    days_ru_nom = {
        'Monday': 'понедельник', 'Tuesday': 'вторник', 'Wednesday': 'среда',
        'Thursday': 'четверг', 'Friday': 'пятница', 'Saturday': 'суббота', 'Sunday': 'воскресенье'
    }

    for d in best_days:
        weekday_en = d.strftime('%A')
        weekday_ru = days_ru_nom.get(weekday_en, weekday_en)
        results.append({
            'date': d,
            'weekday_ru': weekday_ru,
            'videos': videos.get(d, 0),
            'tasks': tasks.get(d, 0),
            'points': round(points.get(d, 0), 2),
            'productivity_score': productivity[d],
            'badges': badges.get(d, [])
        })

    return results, period_start, period_end

def analyze_productive_day(data, start_date=None, end_date=None):
    result = find_most_productive_day(data, start_date, end_date)
    if result is None:
        print("\n⚠️ Недостаточно данных для определения самого продуктивного дня.")
        return

    results, period_start, period_end = result

    days_gender = {
        'понедельник': 'это был самый мощный',
        'вторник': 'это был самый мощный',
        'среда': 'это была самая мощная',
        'четверг': 'это был самый мощный',
        'пятница': 'это была самая мощная',
        'суббота': 'это была самая мощная',
        'воскресенье': 'это было самое мощное'
    }

    print("\n" + "="*60)
    print("🏆 АНАЛИЗ САМОГО ПРОДУКТИВНОГО ДНЯ")
    print("="*60)

    print(f"\n📅 АНАЛИЗИРУЕМЫЙ ПЕРИОД:")
    print(f"   {period_start.strftime('%d.%m.%Y')} — {period_end.strftime('%d.%m.%Y')}")

    print(f"\n💪 САМЫЙ ПРОДУКТИВНЫЙ ДЕНЬ (ДНИ):")
    for res in results:
        wd = res['weekday_ru']
        phrase = days_gender.get(wd, 'это был самый мощный')
        print(f"\n   📍 Твой день силы — {res['date'].strftime('%d.%m.%Y')}, {phrase} {wd} в периоде")
        print(f"      ├─ Просмотрено видео: {res['videos']}")
        print(f"      ├─ Решено задач: {res['tasks']}")
        print(f"      └─ Заработано баллов: {res['points']}")
        if res['badges']:
            badges_str = ', '.join([b['title'] for b in res['badges']])
            print(f"      └─ Получено наград: {badges_str}")

    if len(results) > 1:
        print(f"\n⚠️ Примечание: обнаружено {len(results)} дня с одинаковой продуктивностью.")
        print(f"   Все они признаны самыми продуктивными.")

#===========================================================================================================================
#                                            ПОДБОР ТОТЕМНОГО ЖИВОТНОГО          
# ==========================================================================================================================


def determine_archetype(data, user_id, weekly_info, rhythm_info, time_info, perf_info):
    # ---------- Вспомогательные функции ----------
    def get_hour_from_time(time_str):
        if pd.isna(time_str):
            return None
        try:
            return int(str(time_str).split(':')[0])
        except:
            return None

    def classify_session_time(hour):
        if hour is None:
            return 'unknown'
        if 4 <= hour < 12:
            return 'morning'
        elif 12 <= hour < 18:
            return 'day'
        else:
            return 'night'

    # ---------- 1. ВРЕМЯ (циркадный ритм) ----------
    pt = data.get('popular_time')
    time_preference = "any"
    time_note = "Не определено"
    if pt is not None and not pt.empty:
        n = len(pt)
        morning = day = night = 0
        for _, row in pt.iterrows():
            h = get_hour_from_time(row.get('начало сессии'))
            t = classify_session_time(h)
            if t == 'morning':
                morning += 1
            elif t == 'day':
                day += 1
            elif t == 'night':
                night += 1
        if n > 0:
            m_pct = morning / n * 100
            n_pct = night / n * 100
            if m_pct >= 50:
                time_preference = "morning"
                time_note = "Явный жаворонок"
            elif n_pct >= 50:
                time_preference = "night"
                time_note = "Явная сова"
            elif m_pct >= 35 and n_pct >= 35:
                time_preference = "mixed"
                time_note = "Смешанный тип"
            elif m_pct > n_pct:
                time_preference = "morning"
                time_note = "Склонен к утреннему типу"
            elif n_pct > m_pct:
                time_preference = "night"
                time_note = "Склонен к вечернему типу"
            else:
                time_preference = "mixed"
                time_note = "Смешанный тип"

    # ---------- 2. КАЧЕСТВО ----------
    uc = data['user_courses']
    if not uc.empty:
        wk_points = uc['wk_points'].iloc[0] if 'wk_points' in uc.columns else 0
        wk_max = uc['wk_max_points'].iloc[0] if 'wk_max_points' in uc.columns else 1
        points_ratio = (wk_points / wk_max * 100) if wk_max > 0 else 0
    else:
        points_ratio = 0

    ua = data['user_answers']
    first_attempt_success = 0
    accuracy = 0
    perfect_rate = 0
    if not ua.empty and 'attempts' in ua.columns:
        first_attempt_success = len(ua[ua['attempts'] == 1]) / len(ua) * 100
        if 'solved' in ua.columns:
            solved_count = len(ua[ua['solved'] == True])
            accuracy = (solved_count / len(ua) * 100) if len(ua) > 0 else 0
        if 'points' in ua.columns and 'max_attempts' in ua.columns:
            max_possible = ua['max_attempts'].iloc[0] if not ua.empty else 1
            perfect_count = len(ua[ua['points'] == max_possible])
            perfect_rate = (perfect_count / len(ua) * 100) if len(ua) > 0 else 0

    quality_score = (points_ratio * 0.4) + (first_attempt_success * 0.3) + (accuracy * 0.2) + (perfect_rate * 0.1)
    if quality_score >= 90:
        quality_level = "maximum"
        quality_note = f"Максимальное качество ({quality_score:.1f}%)"
    elif quality_score >= 75:
        quality_level = "high"
        quality_note = f"Высокое качество ({quality_score:.1f}%)"
    elif quality_score >= 50:
        quality_level = "medium"
        quality_note = f"Среднее качество ({quality_score:.1f}%)"
    else:
        quality_level = "low"
        quality_note = f"Низкое качество ({quality_score:.1f}%)"

    # Стабильность
    if not uc.empty and 'wk_points' in uc.columns and len(uc) > 1:
        points_std = uc['wk_points'].std()
        if points_std < 5 and points_std > 0:
            quality_level = "stable"
            quality_note = f"Стабильные результаты (отклонение {points_std:.1f})"

    # ---------- 3. АКТИВНОСТЬ ----------
    uact = data['user_actions']
    ms = data['media_sessions']
    unique_days = 0
    total_sessions = 0
    if not uact.empty and 'created_at' in uact.columns:
        try:
            dates = pd.to_datetime(uact['created_at']).dt.date
            unique_days = len(dates.unique())
            total_sessions = len(uact)
        except:
            pass
    total_sessions += len(ms)

    if unique_days > 40 or total_sessions > 100:
        activity_level = "very_high"
        activity_note = f"Очень высокая активность ({unique_days} дней, {total_sessions} сессий)"
    elif unique_days > 20 or total_sessions > 50:
        activity_level = "high"
        activity_note = f"Высокая активность ({unique_days} дней, {total_sessions} сессий)"
    elif unique_days > 10 or total_sessions > 20:
        activity_level = "medium"
        activity_note = f"Средняя активность ({unique_days} дней, {total_sessions} сессий)"
    else:
        activity_level = "low"
        activity_note = f"Низкая активность ({unique_days} дней, {total_sessions} сессий)"

    # Проверка на spikes
    if not uact.empty and 'created_at' in uact.columns:
        try:
            dates_series = pd.to_datetime(uact['created_at']).dt.date
            daily_counts = dates_series.value_counts()
            if len(daily_counts) > 0:
                max_daily = daily_counts.max()
                avg_daily = daily_counts.mean()
                if max_daily > avg_daily * 3 and max_daily > 10:
                    activity_level = "spikes"
                    activity_note = f"Активность всплесками (макс {max_daily} действий в день)"
        except:
            pass


    # ---------- 4. НАСТОЙЧИВОСТЬ ----------
    avg_attempts = 1
    if not ua.empty and 'attempts' in ua.columns:
        avg_attempts = ua['attempts'].mean()
    if avg_attempts > 2.5:
        persistence_level = "maximum"
        persistence_note = f"Максимальная настойчивость ({avg_attempts:.1f} попыток)"
    elif avg_attempts >= 1.8:
        persistence_level = "high"
        persistence_note = f"Высокая настойчивость ({avg_attempts:.1f} попыток)"
    elif avg_attempts >= 1.2:
        persistence_level = "medium"
        persistence_note = f"Средняя настойчивость ({avg_attempts:.1f} попыток)"
    else:
        persistence_level = "low"
        persistence_note = f"Низкая настойчивость ({avg_attempts:.1f} попыток)"

    # ---------- 5. ВНИМАТЕЛЬНОСТЬ ----------
    ul = data['user_lessons']
    video_percent = 0
    if not ul.empty and 'video_viewed' in ul.columns:
        video_viewed = ul['video_viewed'].sum()
        video_percent = (video_viewed / len(ul) * 100) if len(ul) > 0 else 0
    if video_percent > 90:
        attentiveness_level = "maximum"
        attentiveness_note = f"Максимальная внимательность ({video_percent:.1f}% видео просмотрено)"
    elif video_percent > 70:
        attentiveness_level = "high"
        attentiveness_note = f"Высокая внимательность ({video_percent:.1f}% видео просмотрено)"
    elif video_percent > 30:
        attentiveness_level = "medium"
        attentiveness_note = f"Средняя внимательность ({video_percent:.1f}% видео просмотрено)"
    else:
        attentiveness_level = "low"
        attentiveness_note = f"Низкая внимательность ({video_percent:.1f}% видео просмотрено)"

    # Использование подготовительных материалов
    uses_prep = False
    if not uact.empty and 'action' in uact.columns:
        uses_prep = len(uact[uact['action'] == 'visit_preparation_material']) > 0

    # ---------- 6. ОСОБЫЕ КРИТЕРИИ ----------
    special_criteria = []
    # Олимпиадник
    awards = data['awards']
    if not awards.empty and 'title' in awards.columns:
        if any('Олимпиадник' in str(t) for t in awards['title']):
            special_criteria.append("Имеет награду Олимпиадник")
    # Тип недельной активности
    if pt is not None and not pt.empty:
        day_counts = pt['день недели'].value_counts()
        wd_sess = day_counts[day_counts.index.isin(['Понедельник','Вторник','Среда','Четверг','Пятница'])].sum()
        we_sess = day_counts[day_counts.index.isin(['Суббота','Воскресенье'])].sum()
        total = wd_sess + we_sess
        if total > 0:
            if wd_sess > we_sess:
                special_criteria.append("activity_type = Король будней")
            elif abs(wd_sess - we_sess) / total < 0.2:
                special_criteria.append("activity_type = Гибкий поток")
    # visit_preparation_material + низкий просмотр видео
    if uses_prep and video_percent < 30:
        special_criteria.append("visit_preparation_material = TRUE, video_viewed = FALSE")
    # Коэффициент неравномерности
    if not uact.empty and 'created_at' in uact.columns:
        try:
            dates_series = pd.to_datetime(uact['created_at']).dt.date
            daily_counts = dates_series.value_counts()
            if len(daily_counts) > 0:
                max_daily = daily_counts.max()
                avg_daily = daily_counts.mean()
                if avg_daily > 0 and (max_daily / avg_daily) > 2.0:
                    special_criteria.append(f"Коэффициент неравномерности >2.0 ({max_daily/avg_daily:.1f})")
        except:
            pass

    # ---------- 7. МАТРИЦА АРХЕТИПОВ (точная копия из Animal_totem.py) ----------
    archetypes = [
        {
            'name': 'Дракон', 'emoji': '🐉', 'archetype': 'Гений-полимат',
            'slogan': 'Мне подвластны любые вершины. Я создаю правила игры.',
            'conditions': {
                'quality_level': ['maximum'],
                'activity_level': ['very_high', 'high'],
                'persistence_level': ['maximum', 'very_high'],
                'attentiveness_level': ['maximum', 'high']
            }
        },
        {
            'name': 'Орел', 'emoji': '🦅', 'archetype': 'Лидер-отличник',
            'slogan': 'Я беру высоту. Мои результаты говорят сами за себя.',
            'conditions': {
                'quality_level': ['maximum', 'high'],
                'activity_level': ['high', 'very_high'],
                'persistence_level': ['high', 'very_high', 'maximum'],
                'attentiveness_level': ['high', 'maximum']
            }
        },
        {
            'name': 'Пчелка', 'emoji': '🐝', 'archetype': 'Трудолюбивый системщик',
            'slogan': 'Капля за каплей — и вот уже океан знаний.',
            'conditions': {
                'quality_level': ['medium', 'high'],
                'activity_level': ['very_high', 'high', 'smooth'],
                'persistence_level': ['high', 'very_high'],
                'attentiveness_level': ['medium', 'high'],
                'special_contains': 'activity_type = Король будней'
            }
        },
        {
            'name': 'Волк-одиночка', 'emoji': '🐺', 'archetype': 'Автономный исследователь',
            'slogan': 'Я выбираю свой путь. Знания добываю сам.',
            'conditions': {
                'quality_level': ['medium'],
                'activity_level': ['low', 'medium'],
                'persistence_level': ['high', 'very_high'],
                'attentiveness_level': ['low', 'medium'],
                'special_contains': 'activity_type = Гибкий поток'
            }
        },
        {
            'name': 'Кошка', 'emoji': '🐱', 'archetype': 'Любознательный исследователь',
            'slogan': 'Моё любопытство не знает границ. Я пробую всё новое!',
            'conditions': {
                'quality_level': ['low', 'medium'],
                'activity_level': ['high', 'medium'],
                'persistence_level': ['low', 'medium'],
                'attentiveness_level': ['high', 'maximum'],
                'special_contains': 'Имеет награду Олимпиадник'
            }
        },
        {
            'name': 'Панда', 'emoji': '🐼', 'archetype': 'Основательный',
            'slogan': 'Ничего не забываю. Моя память — моя сила.',
            'conditions': {
                'quality_level': ['medium', 'stable'],
                'activity_level': ['medium', 'low'],
                'persistence_level': ['very_high', 'maximum'],
                'attentiveness_level': ['low', 'medium']
            }
        },
        {
            'name': 'Белка', 'emoji': '🐿️', 'archetype': 'Спринтер-гиперфокус',
            'slogan': 'Когда я в деле — остановить меня нельзя. Мощный рывок к цели!',
            'conditions': {
                'quality_level': ['high', 'maximum'],
                'activity_level': ['spikes'],
                'persistence_level': ['high', 'very_high'],
                'attentiveness_level': ['medium', 'high']
            }
        },
        {
            'name': 'Бабочка', 'emoji': '🦋', 'archetype': 'Вдохновенный',
            'slogan': 'Когда приходит вдохновение — я творю чудеса.',
            'conditions': {
                'quality_level': ['high', 'maximum'],
                'activity_level': ['uneven', 'spikes'],
                'persistence_level': ['medium', 'high'],
                'attentiveness_level': ['high', 'maximum'],
                'special_contains': 'Коэффициент неравномерности'
            }
        },
        {
            'name': 'Лиса', 'emoji': '🦊', 'archetype': 'Хитрый оптимизатор',
            'slogan': 'Работаю умнее, а не тяжелее. Каждая минута на вес золота.',
            'conditions': {
                'quality_level': ['high', 'maximum'],
                'activity_level': ['optimal', 'medium'],
                'persistence_level': ['low', 'medium'],
                'attentiveness_level': ['low'],
                'special_contains': 'visit_preparation_material = TRUE'
            }
        },
        {
            'name': 'Бизон', 'emoji': '🐂', 'archetype': 'Упорный марафонец',
            'slogan': 'Я не гонюсь за скоростью. Моя сила — в выдержке и терпении.',
            'conditions': {
                'quality_level': ['low', 'medium'],
                'activity_level': ['low', 'medium'],
                'persistence_level': ['maximum', 'very_high'],
                'attentiveness_level': ['low', 'medium']
            }
        },
        {
            'name': 'Сова', 'emoji': '🦉', 'archetype': 'Аналитик-стратег',
            'slogan': 'Мудрость приходит с опытом. Я вникаю в каждую деталь.',
            'conditions': {
                'time_preference': ['night'],
                'quality_level': ['high', 'maximum'],
                'activity_level': ['medium', 'low'],
                'persistence_level': ['high', 'very_high'],
                'attentiveness_level': ['high', 'maximum']
            }
        },
        {
            'name': 'Жаворонок', 'emoji': '🐦', 'archetype': 'Ранний старт',
            'slogan': 'Утро — время побед. Я заряжаю день энергией знаний!',
            'conditions': {
                'time_preference': ['morning'],
                'quality_level': ['medium', 'high'],
                'activity_level': ['high', 'very_high'],
                'persistence_level': ['medium', 'high'],
                'attentiveness_level': ['medium', 'high']
            }
        }
    ]

    # ---------- 8. ПОИСК ЛУЧШЕГО СОВПАДЕНИЯ ----------
    selected = None
    best_score = 0
    for arch in archetypes:
        score = 0
        total = 0
        cond = arch['conditions']
        if 'time_preference' in cond:
            total += 1
            if time_preference in cond['time_preference']:
                score += 1
        if 'quality_level' in cond:
            total += 1
            if quality_level in cond['quality_level']:
                score += 1
        if 'activity_level' in cond:
            total += 1
            if activity_level in cond['activity_level']:
                score += 1
        if 'persistence_level' in cond:
            total += 1
            if persistence_level in cond['persistence_level']:
                score += 1
        if 'attentiveness_level' in cond:
            total += 1
            if attentiveness_level in cond['attentiveness_level']:
                score += 1
        if 'special_contains' in cond:
            total += 1
            special_text = cond['special_contains']
            if any(special_text in crit for crit in special_criteria):
                score += 1
        if total > 0:
            pct = (score / total) * 100
            if pct > best_score:
                best_score = pct
                selected = arch

    if selected is None or best_score < 40:
        selected = {
            'name': 'Бизон', 'emoji': '🐂', 'archetype': 'Упорный марафонец',
            'slogan': 'Я не гонюсь за скоростью. Моя сила — в выдержке и терпении.'
        }
        best_score = 100

    return {
        'animal_emoji': selected['emoji'],
        'animal_name': selected['name'],
        'archetype_name': selected['archetype'],
        'slogan': selected['slogan'],
        'match_confidence': f"{best_score:.0f}%",
        # отладочная информация
        '_time_level': f"{time_preference} ({time_note})",
        '_quality_level': f"{quality_level} ({quality_note})",
        '_activity_level': f"{activity_level} ({activity_note})",
        '_persistence_level': f"{persistence_level} ({persistence_note})",
        '_attentiveness_level': f"{attentiveness_level} ({attentiveness_note})",
        '_special_criteria': special_criteria
    }

#===========================================================================================================================
#                                                          ВИЗУАЛИЗАЦИЯ        
# ==========================================================================================================================

def plot_results(user_id, data, time_info, perf_info, course_time, weekly_info, rhythm_info, start_date=None, end_date=None):
    # # 1. Основные показатели
    # fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    # ax = axes[0,0]
    # if 'wk_points' in perf_info and 'wk_max_points' in perf_info:
    #     ax.bar(['Набрано', 'Максимум'], [perf_info['wk_points'], perf_info['wk_max_points']])
    #     ax.set_title('Баллы в курсе')
    # ax = axes[0,1]
    # if 'Решал задач' in perf_info and 'Всего задач' in perf_info:
    #     ax.bar(['Решено', 'Всего'], [perf_info['Решал задач'], perf_info['Всего задач']])
    #     ax.set_title('Решение задач')
    # ax = axes[1,0]
    # if 'Всего просмотров уроков' in perf_info:
    #     views = [perf_info['Всего просмотров уроков'],
    #              perf_info.get('Из них онлайн',0),
    #              perf_info.get('Из них в записи',0)]
    #     ax.bar(['Всего', 'Онлайн', 'В записи'], views)
    #     ax.set_title('Просмотры уроков')
    # ax = axes[1,1]
    # if 'trainings_count' in perf_info and perf_info['trainings_count'] > 0:
    #     ax.bar(['Кол-во', 'Ср.оценка*10'], [perf_info['trainings_count'], perf_info.get('avg_mark',0)*10])
    #     ax.set_title('Тренинги')
    # else:
    #     ax.text(0.5,0.5,'Нет тренингов', ha='center')
    # plt.tight_layout()
    # plt.show()
    
    # 2. Активность по дням
    if not data['user_actions'].empty:
        col = safe_get_columns(data['user_actions'], ['created_at'])
        if col:
            actions = data['user_actions'].copy()
            actions['date'] = actions[col].apply(parse_date).dt.date
            daily = actions.groupby('date').size().reset_index(name='count')
            if not daily.empty:
                plt.figure(figsize=(12,5))
                plt.plot(daily['date'], daily['count'], marker='o')
                plt.title('Активность по дням')
                plt.xticks(rotation=45)
                plt.tight_layout()
                plt.show()
    
    # 3. Распределение действий
    if not data['user_actions'].empty and 'action' in data['user_actions'].columns:
        action_counts = data['user_actions']['action'].value_counts()
        plt.figure(figsize=(8,8))
        plt.pie(action_counts, labels=action_counts.index, autopct='%1.1f%%')
        plt.title('Типы действий')
        plt.show()
    
    # # 4. Накопление баллов за ответы
    # if not data['user_answers'].empty:
    #     col_cr = safe_get_columns(data['user_answers'], ['created_at'])
    #     if col_cr and 'points' in data['user_answers'].columns:
    #         answers = data['user_answers'].copy()
    #         answers['dt'] = answers[col_cr].apply(parse_date)
    #         answers = answers.sort_values('dt')
    #         answers['cum_points'] = answers['points'].cumsum()
    #         plt.figure(figsize=(12,5))
    #         plt.plot(answers['dt'], answers['cum_points'], marker='.')
    #         plt.title('Накопление баллов за ответы')
    #         plt.xticks(rotation=45)
    #         plt.grid(alpha=0.3)
    #         plt.tight_layout()
    #         plt.show()
    
    # # 5. Топ курсов
    # if course_time is not None and not course_time.empty:
    #     plt.figure(figsize=(8,5))
    #     course_time.head(5).plot(kind='bar', color='skyblue')
    #     plt.title('Топ-5 курсов по времени просмотра видео')
    #     plt.xlabel('ID курса')
    #     plt.ylabel('Минуты')
    #     plt.xticks(rotation=45)
    #     plt.tight_layout()
    #     plt.show()
    
    # 6. Недельная активность
    if weekly_info:
        days = WEEKDAY_ORDER
        percents = [weekly_info['day_percents'][d]['percent'] for d in days]
        plt.figure(figsize=(10,5))
        bars = plt.bar([DAYS_EN_TO_RU[d] for d in days], percents, color='steelblue')
        plt.title('Распределение активности по дням недели (за всё время)')
        plt.ylabel('% сессий')
        plt.xticks(rotation=45)
        for bar, p in zip(bars, percents):
            plt.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 1, f'{p}%', ha='center')
        plt.tight_layout()
        plt.show()
    
    # 7. Биоритмы
    if rhythm_info:
        labels = ['Утро (04-12)', 'День (12-18)', 'Вечер/Ночь (18-04)']
        sizes = [rhythm_info['morning_percent'], rhythm_info['day_percent'], rhythm_info['night_percent']]
        colors = ['#ffcc00', '#66b3ff', '#2d2d5e']
        plt.figure(figsize=(7,7))
        plt.pie(sizes, labels=labels, autopct='%1.1f%%', colors=colors, startangle=90)
        plt.title('Распределение активности по времени суток (за всё время)')
        plt.tight_layout()
        plt.show()
    
    # # 8. Продуктивность по дням
    # videos, tasks, points, _ = collect_productivity_data(data, start_date, end_date)
    # all_dates = set(videos.keys()) | set(tasks.keys()) | set(points.keys())
    # if all_dates:
    #     dates = sorted(all_dates)
    #     prod_values = [videos.get(d,0) + tasks.get(d,0) + points.get(d,0) for d in dates]
    #     plt.figure(figsize=(14,5))
    #     plt.bar(dates, prod_values, color='orange', alpha=0.7)
    #     plt.title('Продуктивность по дням (видео + задачи + баллы)')
    #     plt.xlabel('Дата')
    #     plt.ylabel('Суммарная продуктивность')
    #     plt.xticks(rotation=45)
    #     plt.tight_layout()
    #     plt.show()

#===========================================================================================================================
#                                                 ФУНКЦИЯ ВЫБОРА ИНСАЙТОВ        
# ==========================================================================================================================

def select_insights(metrics):
    """
    Выбирает топ-2 инсайта на основе метрик пользователя
    """
    import pandas as pd
    import os
    
    # Путь к файлу с базой инсайтов
    insights_path = os.path.join(DATA_PATH, 'insights_database.csv')
    
    # Для отладки
    print(f"\n🔍 Поиск файла инсайтов: {insights_path}")
    
    if not os.path.exists(insights_path):
        print(f"⚠️ Файл не найден: {insights_path}")
        return [{
            'id': 'default',
            'category': 'default',
            'text': 'За этот период у тебя стабильный прогресс. Ты движешься в правильном направлении!',
            'recommendation': 'Продолжай в том же духе — и результат не заставит себя ждать.'
        }]
    
    # Загрузка файла с правильной кодировкой
    try:
        insights_df = pd.read_csv(insights_path, encoding='utf-8-sig', sep=';')
        print(f"✅ Файл загружен, строк: {len(insights_df)}")
    except Exception as e:
        print(f"⚠️ Ошибка загрузки: {e}")
        return [{
            'id': 'default',
            'category': 'default',
            'text': 'За этот период у тебя стабильный прогресс. Ты движешься в правильном направлении!',
            'recommendation': 'Продолжай в том же духе — и результат не заставит себя ждать.'
        }]
    
    matched_insights = []
    
    for _, row in insights_df.iterrows():
        match = True
        score = 0
        
        # Пропускаем строки с пустым trigger_field
        if pd.isna(row['trigger_field']) or str(row['trigger_field']).strip() == '':
            continue
        
        # Проверка первого триггера
        trigger_type = str(row['trigger_type']).strip()
        trigger_field = str(row['trigger_field']).strip()
        min_val = row['trigger_value_min']
        max_val = row['trigger_value_max']
        
        if trigger_type == 'exact':
            if trigger_field in metrics:
                metric_value = metrics[trigger_field]
                if str(metric_value) != str(min_val):
                    match = False
            else:
                match = False
        elif trigger_type == 'range':
            if trigger_field in metrics:
                metric_value = metrics[trigger_field]
                if pd.isna(metric_value):
                    match = False
                else:
                    try:
                        if float(metric_value) < float(min_val) or float(metric_value) > float(max_val):
                            match = False
                    except:
                        match = False
            else:
                match = False
        
        if not match:
            continue
        score += 1
        
        # Проверка второго триггера (если есть)
        if pd.notna(row['trigger_2_field']) and str(row['trigger_2_field']).strip():
            trigger2_type = str(row['trigger_2_type']).strip()
            trigger2_field = str(row['trigger_2_field']).strip()
            min2_val = row['trigger_2_value_min']
            max2_val = row['trigger_2_value_max']
            
            if trigger2_type == 'exact':
                if trigger2_field in metrics:
                    if str(metrics[trigger2_field]) != str(min2_val):
                        match = False
                else:
                    match = False
            elif trigger2_type == 'range':
                if trigger2_field in metrics:
                    metric2_value = metrics[trigger2_field]
                    if pd.isna(metric2_value):
                        match = False
                    else:
                        try:
                            if float(metric2_value) < float(min2_val) or float(metric2_value) > float(max2_val):
                                match = False
                        except:
                            match = False
                else:
                    match = False
            
            if not match:
                continue
            score += 1
        
        # Инсайт подошёл
        matched_insights.append({
            'id': row['id'],
            'category': row['category'],
            'text': row['text'],
            'recommendation': row['recommendation'],
            'score': score
        })
    
    # Функция приоритета
    def priority(insight):
        if insight['category'] == 'combined':
            return 3
        elif insight['category'] in ['rhythm', 'weekday', 'totem']:
            return 2
        else:
            return 1
    
    # Сортировка
    matched_insights.sort(key=lambda x: (priority(x), x['score']), reverse=True)
    
    # Выбираем топ-2 с разными категориями
    selected = []
    categories_used = set()
    
    for insight in matched_insights:
        if len(selected) >= 2:
            break
        if insight['category'] not in categories_used:
            selected.append(insight)
            categories_used.add(insight['category'])
    
    # Если не набрали 2 инсайта, добираем из любых
    if len(selected) < 2:
        for insight in matched_insights:
            if len(selected) >= 2:
                break
            if insight not in selected:
                selected.append(insight)
    
    # Если всё равно нет инсайтов — базовый
    if len(selected) == 0:
        selected.append({
            'id': 'default',
            'category': 'default',
            'text': 'За этот период у тебя стабильный прогресс. Ты движешься в правильном направлении!',
            'recommendation': 'Продолжай в том же духе — и результат не заставит себя ждать.'
        })
    
    return selected

#===========================================================================================================================
#                                                    ОСНОВНАЯ ФУНКЦИЯ    
# =========================================================================================================================

def main():
    user_id = get_user_id()
    print(f"\n=== Анализ для пользователя {user_id} ===\n")
    
    print("Загрузка данных...")
    data = load_filtered_data(user_id)
    
    if (data['courses_stats'].empty and data['user_actions'].empty and 
        data['popular_time'].empty and data['user_answers'].empty):
        print(f"Нет данных для пользователя {user_id}. Проверьте корректность ID.")
        return
    
    start_date, end_date = select_period()
    if start_date and end_date:
        print(f"\nАнализ за период: {start_date.strftime('%d.%m.%Y')} – {end_date.strftime('%d.%m.%Y')}")
        data['user_answers'] = filter_df_by_period(data['user_answers'], start_date, end_date, 
                                                   ['created_at', 'updated_at', 'submitted_at'])
        data['user_actions'] = filter_df_by_period(data['user_actions'], start_date, end_date, ['created_at'])
        data['media_sessions'] = filter_df_by_period(data['media_sessions'], start_date, end_date, 
                                                     ['started_at', 'finished_at'])
        data['user_trainings'] = filter_df_by_period(data['user_trainings'], start_date, end_date, 
                                                     ['started_at', 'finished_at'])
        data['user_lessons'] = filter_df_by_period(data['user_lessons'], start_date, end_date, 
                                                   ['created_at', 'updated_at'])
    else:
        print("\nАнализ за всё время")
    
    print("Расчёт времени на платформе...")
    intervals = compute_time_intervals(data)
    time_info = analyze_time_and_days(data, intervals)
    
    print("Анализ успеваемости...")
    perf_info = analyze_performance(data)
    
    course_time = analyze_course_time(data)
    
    print("Анализ недельной активности...")
    weekly_info = analyze_weekly_activity(data)
    
    print("Анализ биоритмов...")
    rhythm_info = analyze_circadian_rhythm(data)
    
    print("Определение тотемного животного...")
    archetype_info = determine_archetype(data, user_id, weekly_info, rhythm_info, time_info, perf_info)
    
    # Вывод самого продуктивного дня
    analyze_productive_day(data, start_date, end_date)
    
    # Вывод результатов
    print("\n" + "="*60)
    print("РЕЗУЛЬТАТЫ АНАЛИЗА")
    print("="*60)
    
    print("\n📌 ОБЩАЯ ИНФОРМАЦИЯ:")
    for k in ['Регион', 'Муниципалитет', 'Школа', 'Класс']:
        if k in perf_info:
            print(f"  {k}: {perf_info[k]}")
    
    print("\n⏱️ ВРЕМЯ НА ПЛАТФОРМЕ:")
    total = time_info['total_time']
    print(f"  Общее время: {total.days} дн {total.seconds//3600} ч {(total.seconds%3600)//60} мин")
    avg_min = (total.total_seconds() / 60) / time_info['unique_days'] if time_info['unique_days'] else 0
    print(f"  Среднее в день: {avg_min:.1f} мин")
    print(f"  Уникальных дней активности: {time_info['unique_days']}")
    if time_info['first_activity']:
        print(f"  Первая активность: {time_info['first_activity'].strftime('%d.%m.%Y %H:%M')}")
        print(f"  Последняя активность: {time_info['last_activity'].strftime('%d.%m.%Y %H:%M')}")
        print(f"  Период: {time_info['period_days']} дней")
    
    print("\n📅 РАСПРЕДЕЛЕНИЕ ДНЕЙ АКТИВНОСТИ:")
    for ay, days_list in time_info['academic_days'].items():
        visited = len(days_list)
        total_cal = get_school_days_in_year(ay, False)
        total_act = get_school_days_in_year(ay, True)
        print(f"  Учебный год {ay}: {visited} дней")
        print(f"    от всех дней: {visited/total_cal*100:.1f}% ({total_cal} дней)")
        print(f"    от учебных дней: {visited/total_act*100:.1f}% ({total_act} дней)")
    print(f"  Летние дни: {time_info['summer_days']}")
    print(f"  Выходные: {time_info['weekend_days']}")
    print(f"  Праздники: {time_info['holiday_days']}")
    
    print("\n📚 УСПЕВАЕМОСТЬ:")
    if 'wk_points' in perf_info and 'wk_max_points' in perf_info:
        print(f"  Баллы в курсе: {perf_info['wk_points']} / {perf_info['wk_max_points']}")
        if 'course_percent' in perf_info:
            print(f"  Процент выполнения: {perf_info['course_percent']:.1f}%")
            print(f"  Это выше, чем у {perf_info['better_than_percent']:.1f}% учеников")
    if 'Решал задач' in perf_info and 'Всего задач' in perf_info:
        print(f"  Решено задач: {perf_info['Решал задач']} / {perf_info['Всего задач']}")
    if 'Всего просмотров уроков' in perf_info:
        print(f"  Просмотров уроков: {perf_info['Всего просмотров уроков']} (онлайн: {perf_info.get('Из них онлайн',0)}, запись: {perf_info.get('Из них в записи',0)})")
    if 'trainings_count' in perf_info:
        print(f"  Тренингов: {perf_info['trainings_count']}, средняя оценка: {perf_info.get('avg_mark', 0):.2f}")
    if 'total_answers' in perf_info:
        print(f"  Ответов: {perf_info['total_answers']} (решено: {perf_info.get('solved_answers',0)})")
    
    if 'awards' in perf_info:
        print("\n🏅 НАГРАДЫ:")
        for a in perf_info['awards']:
            title = a.get('title', '?')
            level = a.get('level', '?')
            created = a.get('created_at', '?')
            print(f"  {title} (ур. {level}) — {created}")
    
    if course_time is not None and not course_time.empty:
        print("\n🎓 ТОП-5 КУРСОВ ПО ВРЕМЕНИ ПРОСМОТРА:")
        for cid, mins in course_time.head(5).items():
            print(f"  Курс {cid}: {mins:.1f} мин")
    
    if weekly_info:
        print("\n📅 НЕДЕЛЬНАЯ АКТИВНОСТЬ (за всё время):")
        print(f"  Всего сессий: {weekly_info['total_sessions']}")
        for day in WEEKDAY_ORDER:
            d = weekly_info['day_percents'][day]
            print(f"    {DAYS_EN_TO_RU[day]}: {d['count']} сессий ({d['percent']}%)")
        print(f"  Общий тип: {weekly_info['activity_type']}")
        print(f"  {weekly_info['activity_slogan']}")
        print(f"  Самый активный день (дни):")
        for info in weekly_info['active_day_info']:
            print(f"    - {info['day_ru']}: {info['type']} – {info['slogan']}")
        print(f"  Баланс: будни {weekly_info['weekday_percent']}% / выходные {weekly_info['weekend_percent']}%")
    else:
        print("\n⚠️ Нет данных о недельной активности.")
    
    if rhythm_info:
        print("\n🌙 БИОРИТМЫ (за всё время):")
        print(f"  Утро (04-12): {rhythm_info['morning_percent']}%")
        print(f"  День (12-18): {rhythm_info['day_percent']}%")
        print(f"  Вечер/Ночь (18-04): {rhythm_info['night_percent']}%")
        print(f"  Тип: {rhythm_info['classification']}")
        print(f"  Уверенность: {rhythm_info['confidence']}")
        print(f"  {rhythm_info['probability_note']}")
    else:
        print("\n⚠️ Нет данных о биоритмах.")
    
    if archetype_info:
        print("\n" + "="*60)
        print("🐾 ТОТЕМНОЕ ЖИВОТНОЕ")
        print("="*60)
        print(f"\n   {archetype_info['animal_emoji']} {archetype_info['animal_name']} — {archetype_info['archetype_name']}")
        print(f"\n   📢 Слоган: \"{archetype_info['slogan']}\"")
        print(f"\n   🎯 Точность определения: {archetype_info['match_confidence']}")
    
    archetype_info = determine_archetype(data, user_id, weekly_info, rhythm_info, time_info, perf_info)
    print("\n🔍 ОТЛАДКА МЕТРИК АРХЕТИПА:")
    print(f"  time:        {archetype_info['_time_level']}")
    print(f"  quality:     {archetype_info['_quality_level']}")
    print(f"  activity:    {archetype_info['_activity_level']}")
    print(f"  persistence: {archetype_info['_persistence_level']}")
    print(f"  attentiveness: {archetype_info['_attentiveness_level']}")
    print(f"  special:     {archetype_info['_special_criteria']}")

    # ====================================================================================================================
    #                                                  СБОР МЕТРИК ДЛЯ ИНСАЙТОВ
    # ====================================================================================================================
    
    # Безопасное получение значения из словаря
    def safe_get(dict_obj, key, default=0):
        if dict_obj is None or not isinstance(dict_obj, dict):
            return default
        value = dict_obj.get(key, default)
        if pd.isna(value):
            return default
        return value
    
    # 1. Из rhythm_info
    rhythm_type = 'unknown'
    if rhythm_info and isinstance(rhythm_info, dict):
        rhythm_type = rhythm_info.get('rhythm_type', 'unknown')
    
    # 2. Из weekly_info
    most_active_day = 'unknown'
    activity_type = 'unknown'
    if weekly_info and isinstance(weekly_info, dict):
        most_active_days = weekly_info.get('most_active_days', [])
        if most_active_days and len(most_active_days) > 0:
            most_active_day = most_active_days[0]
        activity_type = weekly_info.get('activity_type', 'unknown')
    
    # 3. Из time_info
    avg_minutes_per_day = 0
    if time_info and isinstance(time_info, dict):
        total_seconds = 0
        total_time = time_info.get('total_time', None)
        if total_time:
            if hasattr(total_time, 'total_seconds'):
                total_seconds = total_time.total_seconds()
            elif isinstance(total_time, (int, float)):
                total_seconds = total_time
        unique_days = time_info.get('unique_days', 1)
        if unique_days > 0:
            avg_minutes_per_day = (total_seconds / 60) / unique_days
    
    # 4. Из perf_info
    accuracy = 0
    points_ratio = 0
    avg_attempts = 1
    video_percent = 0
    
    if perf_info and isinstance(perf_info, dict):
        # accuracy
        solved_answers = perf_info.get('solved_answers', 0)
        total_answers = perf_info.get('total_answers', 0)
        if total_answers > 0:
            accuracy = (solved_answers / total_answers) * 100
        
        # points_ratio
        wk_points = perf_info.get('wk_points', 0)
        wk_max_points = perf_info.get('wk_max_points', 1)
        if wk_max_points > 0:
            points_ratio = (wk_points / wk_max_points) * 100
        
        # avg_attempts
        avg_attempts = perf_info.get('avg_attempts', 1)
        if avg_attempts is None or avg_attempts == 0:
            avg_attempts = 1
        
        # video_percent
        video_views = perf_info.get('Всего просмотров уроков', 0)
        total_lessons = 65
        if total_lessons > 0:
            video_percent = (video_views / total_lessons) * 100
            if video_percent > 100:
                video_percent = 100
    
    # 5. Из archetype_info
    totem = 'unknown'
    if archetype_info and isinstance(archetype_info, dict):
        totem = archetype_info.get('animal_name', 'unknown')
    
    # Собираем все метрики в один словарь
    insights_metrics = {
        'rhythm_type': rhythm_type,
        'most_active_day': most_active_day,
        'activity_type': activity_type,
        'avg_minutes_per_day': avg_minutes_per_day,
        'accuracy': accuracy,
        'points_ratio': points_ratio,
        'avg_attempts': avg_attempts,
        'video_percent': video_percent,
        'totem': totem
    }
    
    # # Отладочный вывод (можно закомментировать после проверки)
    # print("\n📊 МЕТРИКИ ДЛЯ ИНСАЙТОВ:")
    # print(f"   rhythm_type: {rhythm_type}")
    # print(f"   most_active_day: {most_active_day}")
    # print(f"   activity_type: {activity_type}")
    # print(f"   avg_minutes_per_day: {avg_minutes_per_day:.1f}")
    # print(f"   accuracy: {accuracy:.1f}%")
    # print(f"   points_ratio: {points_ratio:.1f}%")
    # print(f"   avg_attempts: {avg_attempts:.1f}")
    # print(f"   video_percent: {video_percent:.1f}%")
    # print(f"   totem: {totem}")
    
    
    # ВЫЗОВ ФУНКЦИИ ВЫБОРА ИНСАЙТОВ 
    try:
        selected_insights = select_insights(insights_metrics)
        print(f"\n✅ Найдено подходящих инсайтов: {len(selected_insights)}")
    except Exception as e:
        print(f"\n⚠️ Ошибка при генерации инсайтов: {e}")
        selected_insights = [{
            'id': 'default',
            'category': 'default',
            'text': 'За этот период у тебя стабильный прогресс. Ты движешься в правильном направлении!',
            'recommendation': 'Продолжай в том же духе — и результат не заставит себя ждать.'
        }]
    
    
    # ВЫВОД ИНСАЙТОВ  
    print("\n" + "="*60)
    print("💡 ПЕРСОНАЛЬНЫЕ ИНСАЙТЫ")
    print("="*60)
    
    for i, insight in enumerate(selected_insights, 1):
        print(f"\n📌 ИНСАЙТ {i}:")
        print(f"   {insight['text']}")
        print(f"\n   🎯 РЕКОМЕНДАЦИЯ:")
        print(f"   {insight['recommendation']}")
        print("-"*50)

# окончание блока вфзова функции инсайтов 
    print("\nГенерация графиков...")
    plot_results(user_id, data, time_info, perf_info, course_time, weekly_info, rhythm_info, start_date, end_date)

    print("\n✅ Анализ завершён.")

if __name__ == "__main__":
    main()