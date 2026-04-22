# ===================================================================================================================
#                                                Импорт библиотек
# ===================================================================================================================

from flask import Flask, request, send_file, render_template_string, jsonify
from datetime import datetime
import json
import uuid
import csv
import os
from database import SessionLocal, ShareToken
from certificate_generator import ReportGenerator

# ===================================================================================================================
#                                                Инициализация приложения
# ===================================================================================================================

app = Flask(__name__)
report_gen = ReportGenerator()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATASET_PATH = os.path.join(BASE_DIR, 'students.csv')

# Создаём папки для кеша отчётов и шаблонов, если они не существуют
os.makedirs('share_cache', exist_ok=True)
os.makedirs('templates', exist_ok=True)

# Список всех обязательных колонок в CSV-файле датасета
CSV_FIELDS = ['user_id', 'last_name', 'first_name', 'wk_solved_task_count', 'wk_points', 'wk_max_task_count', 'wk_max_points', 'grade', 'period_type', 'period_number', 'period_year', 'favorite_day', 'activity_type', 'total_events', 'total_minutes']


# ===================================================================================================================
#                                                Функции для работы с данными
# ===================================================================================================================

def load_student_from_dataset(student_id, period_type, period_number, period_year):
    """
    Загружает данные ученика из CSV-файла за указанный период.
    
    Параметры:
        student_id (int): ID ученика
        period_type (str): 'year' или 'trimester'
        period_number (int): 1 для года, 1-3 для триместра
        period_year (int): учебный год
    
    Возвращает:
        dict: словарь с данными ученика
        None: если данные не найдены
        dict с ключом 'error': если структура CSV неверна
    """
    try:
        # Проверяем, существует ли файл датасета
        if not os.path.exists(DATASET_PATH):
            return None
        
        with open(DATASET_PATH, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            
            # Список всех обязательных колонок, которые должны быть в CSV
            required_fields = ['user_id', 'last_name', 'first_name', 'wk_solved_task_count', 
                              'wk_points', 'wk_max_task_count', 'wk_max_points', 'grade', 
                              'period_type', 'period_number', 'period_year', 'favorite_day', 
                              'activity_type', 'total_events', 'total_minutes']
            
            # Проверяем наличие всех обязательных колонок
            for field in required_fields:
                if field not in reader.fieldnames:
                    return {"error": f"Неверная структура датасета: отсутствует колонка '{field}'"}
            
            # Перебираем все строки CSV в поисках нужного ученика и периода
            for row in reader:
                # Пропускаем строки без ID ученика или года периода
                if not row.get('user_id') or not row.get('period_year'):
                    continue
                
                # Проверяем совпадение ID ученика
                if int(row['user_id']) == student_id:
                    # Получаем данные о периоде из строки
                    row_period_type = row.get('period_type')
                    row_period_number = row.get('period_number')
                    row_period_year = row.get('period_year')
                    
                    # Пропускаем строки с пустыми полями периода
                    if not row_period_type or not row_period_number or not row_period_year:
                        continue
                    
                    # Проверяем совпадение периода (тип, номер, год)
                    if (row_period_type == period_type and 
                        str(row_period_number) == str(period_number) and 
                        int(row_period_year) == period_year):
                        
                        try:
                            # Извлекаем все необходимые поля из строки
                            wk_solved_task_count_str = row.get('wk_solved_task_count')
                            wk_points_str = row.get('wk_points')
                            wk_max_task_count_str = row.get('wk_max_task_count')
                            wk_max_points_str = row.get('wk_max_points')
                            total_minutes_str = row.get('total_minutes')
                            total_events_str = row.get('total_events')
                            grade_str = row.get('grade')
                            last_name = row.get('last_name')
                            first_name = row.get('first_name')
                            favorite_day = row.get('favorite_day')
                            activity_type = row.get('activity_type')
                            
                            # Проверяем, что все обязательные поля не пустые
                            if not all([wk_solved_task_count_str, wk_points_str, wk_max_task_count_str, 
                                       wk_max_points_str, total_minutes_str, total_events_str, grade_str]):
                                continue
                            
                            # Преобразуем строки в нужные типы данных
                            wk_solved_task_count = float(wk_solved_task_count_str)
                            wk_points = float(wk_points_str)
                            wk_max_task_count = float(wk_max_task_count_str)
                            wk_max_points = float(wk_max_points_str)
                            total_minutes = int(total_minutes_str)
                            total_events = int(total_events_str)
                            grade = int(grade_str)
                            
                            # Возвращаем словарь с данными ученика
                            return {
                                'user_id': int(row['user_id']),
                                'last_name': last_name if last_name else '',
                                'first_name': first_name if first_name else '',
                                'wk_solved_task_count': wk_solved_task_count,
                                'wk_points': wk_points,
                                'wk_max_task_count': int(wk_max_task_count),
                                'wk_max_points': wk_max_points,
                                'grade': grade,
                                'favorite_day': favorite_day if favorite_day else '',
                                'activity_type': activity_type if activity_type else '',
                                'total_events': total_events,
                                'total_minutes': total_minutes,
                                'period_type': period_type,
                                'period_number': period_number,
                                'period_year': period_year
                            }
                        except (ValueError, TypeError):
                            # Если преобразование типов не удалось, пропускаем строку
                            continue
            return None
    except Exception as e:
        print(f"Ошибка: {e}")
        return None


def get_all_students_list():
    """Возвращает список всех уникальных учеников из CSV (ID, имя, фамилия)."""
    try:
        if not os.path.exists(DATASET_PATH):
            return []
        
        students_dict = {}
        with open(DATASET_PATH, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if not row.get('user_id'):
                    continue
                student_id = int(row['user_id'])
                # Используем словарь, чтобы каждый ученик встречался только один раз
                if student_id not in students_dict:
                    students_dict[student_id] = {
                        'user_id': student_id,
                        'last_name': row.get('last_name', ''),
                        'first_name': row.get('first_name', '')
                    }
        return list(students_dict.values())
    except:
        return []


def get_next_student_id():
    """Возвращает следующий доступный ID для нового ученика (максимальный ID + 1)."""
    students = get_all_students_list()
    if not students:
        return 1
    return max([s['user_id'] for s in students]) + 1


def determine_age_group(grade):
    """
    Определяет возрастную группу по классу.
    1-4 класс → начальная школа ('primary')
    5+ класс → старшая школа ('senior')
    """
    if grade <= 4:
        return 'primary'
    else:
        return 'senior'


def get_period_name(period_type, period_number, period_year):
    """Возвращает человеко-читаемое название периода для отображения в отчёте."""
    if period_type == 'trimester':
        return f"{period_year} учебный год, {period_number} триместр"
    else:
        return f"{period_year} учебный год"


# ===================================================================================================================
#                                                API эндпоинты для работы с учениками
# ===================================================================================================================

@app.route('/api/students', methods=['GET'])
def get_students():
    """Возвращает список всех учеников (ID, имя, фамилия)."""
    students = get_all_students_list()
    return jsonify({'status': 'success', 'count': len(students), 'students': students})


@app.route('/api/student/<int:student_id>', methods=['GET'])
def get_student(student_id):
    """
    Возвращает данные ученика за указанный период.
    
    Параметры запроса (опциональные):
        period_type - 'year' или 'trimester' (по умолчанию 'year')
        period_number - номер периода (по умолчанию 1)
        period_year - учебный год (по умолчанию текущий)
    """
    try:
        # Получаем параметры из строки запроса с значениями по умолчанию
        period_type = request.args.get('period_type', 'year')
        period_number = request.args.get('period_number', 1, type=int)
        period_year = request.args.get('period_year', datetime.now().year, type=int)
        
        # Валидация типа периода
        if period_type not in ['year', 'trimester']:
            return jsonify({'error': 'Тип периода должен быть "year" или "trimester"'}), 400
        
        # Загружаем данные ученика
        student = load_student_from_dataset(student_id, period_type, period_number, period_year)
        
        # Обработка случаев, когда ученик не найден
        if student is None:
            return jsonify({'error': f'Ученик не найден за период {period_type} {period_number} {period_year}'}), 404
        # Обработка ошибки структуры датасета
        if isinstance(student, dict) and 'error' in student:
            return jsonify({'error': student['error']}), 400
        
        return jsonify({'status': 'success', 'student': student})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/student-available-periods/<int:student_id>', methods=['GET'])
def get_student_available_periods(student_id):
    """
    Возвращает список доступных периодов для ученика.
    
    Ответ содержит:
        years - список учебных годов
        periods_by_year - для каждого года: есть ли данные за год и список триместров
    """
    try:
        if not os.path.exists(DATASET_PATH):
            return jsonify({'status': 'success', 'years': [], 'periods_by_year': {}})
        
        periods_by_year = {}
        
        with open(DATASET_PATH, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            
            # Проверяем наличие обязательных колонок для работы с периодами
            required_fields = ['user_id', 'period_type', 'period_number', 'period_year']
            for field in required_fields:
                if field not in reader.fieldnames:
                    return jsonify({'error': f'Неверная структура датасета: отсутствует колонка "{field}"'}), 400
            
            for row in reader:
                if not row.get('user_id'):
                    continue
                    
                # Фильтруем только строки нужного ученика
                if int(row['user_id']) != student_id:
                    continue
                
                year_str = row.get('period_year')
                if not year_str:
                    continue
                
                year = int(year_str)
                if year == 0:
                    continue
                
                # Инициализируем запись для года, если её ещё нет
                if year not in periods_by_year:
                    periods_by_year[year] = {'year': False, 'trimesters': []}
                
                period_type = row.get('period_type', '')
                period_number_str = row.get('period_number', '')
                
                if not period_number_str:
                    continue
                    
                period_number = int(period_number_str)
                
                # Отмечаем наличие года или триместра
                if period_type == 'year':
                    periods_by_year[year]['year'] = True
                elif period_type == 'trimester':
                    if period_number not in periods_by_year[year]['trimesters']:
                        periods_by_year[year]['trimesters'].append(period_number)
        
        # Сортируем триместры для каждого года
        for year in periods_by_year:
            periods_by_year[year]['trimesters'].sort()
        
        return jsonify({
            'status': 'success',
            'years': sorted(periods_by_year.keys(), reverse=True),
            'periods_by_year': periods_by_year
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ===================================================================================================================
#                                                API эндпоинты для управления датасетом
# ===================================================================================================================

@app.route('/api/students/add', methods=['POST'])
def add_student():
    """Добавляет нового ученика в датасет. Все поля обязательны."""
    try:
        data = request.json
        
        # Список всех обязательных полей для добавления ученика
        required_fields = ['user_id', 'last_name', 'first_name', 'wk_solved_task_count', 
                          'wk_points', 'wk_max_task_count', 'wk_max_points', 'grade', 
                          'period_type', 'period_number', 'period_year', 'favorite_day',
                          'activity_type', 'total_events', 'total_minutes']
        
        # Проверяем наличие каждого обязательного поля
        for field in required_fields:
            if field not in data:
                return jsonify({'error': f'Отсутствует обязательное поле: {field}'}), 400
        
        student_id = data['user_id']
        period_type = data['period_type']
        period_number = data['period_number']
        period_year = data['period_year']
        
        # Валидация типа периода
        if period_type not in ['year', 'trimester']:
            return jsonify({'error': 'Тип периода должен быть "year" или "trimester"'}), 400
        
        # Проверяем, нет ли уже записи за этот период (защита от дубликатов)
        existing = load_student_from_dataset(student_id, period_type, period_number, period_year)
        if existing is not None and not isinstance(existing, dict):
            return jsonify({'error': f'Запись для ученика ID {student_id} за период {period_type} {period_number} {period_year} уже существует'}), 400
        
        # Формируем словарь с данными нового ученика
        new_student = {
            'user_id': student_id,
            'last_name': data['last_name'],
            'first_name': data['first_name'],
            'wk_solved_task_count': data['wk_solved_task_count'],
            'wk_points': data['wk_points'],
            'wk_max_task_count': data['wk_max_task_count'],
            'wk_max_points': data['wk_max_points'],
            'grade': data['grade'],
            'period_type': period_type,
            'period_number': period_number,
            'period_year': period_year,
            'favorite_day': data['favorite_day'],
            'activity_type': data['activity_type'],
            'total_events': data['total_events'],
            'total_minutes': data['total_minutes']
        }
        
        # Добавляем запись в CSV-файл
        file_exists = os.path.exists(DATASET_PATH) and os.path.getsize(DATASET_PATH) > 0
        with open(DATASET_PATH, 'a', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=CSV_FIELDS)
            # Если файл новый, сначала записываем заголовки
            if not file_exists:
                writer.writeheader()
            writer.writerow(new_student)
        
        return jsonify({'status': 'success', 'message': f'Запись для ученика {data["first_name"]} {data["last_name"]} (ID {student_id}) добавлена'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/students/update/<int:student_id>', methods=['PUT'])
def update_student(student_id):
    """Обновляет данные существующего ученика."""
    try:
        data = request.json
        rows = []
        found = False
        
        # Читаем все строки из CSV
        with open(DATASET_PATH, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            rows = list(reader)
        
        # Проверяем, что все поля, которые пытаются обновить, существуют в структуре датасета
        valid_keys = set(CSV_FIELDS)
        for key in data.keys():
            if key not in valid_keys:
                return jsonify({'error': f'Поле "{key}" не существует в датасете. Допустимые поля: {", ".join(CSV_FIELDS)}'}), 400
        
        # Ищем нужного ученика и обновляем его поля
        for row in rows:
            if int(row['user_id']) == student_id:
                found = True
                for key, value in data.items():
                    if key in row:
                        row[key] = value
                break
        
        # Если ученик не найден, возвращаем ошибку
        if not found:
            return jsonify({'error': 'Ученик не найден'}), 404
        
        # Перезаписываем весь CSV-файл с обновлёнными данными
        with open(DATASET_PATH, 'w', encoding='utf-8', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=CSV_FIELDS)
            writer.writeheader()
            writer.writerows(rows)
        
        return jsonify({'status': 'success', 'message': f'Данные ученика ID {student_id} обновлены'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/students/upload-csv', methods=['POST'])
def upload_csv():
    """
    Полностью заменяет датасет новым CSV-файлом с проверкой структуры.
    
    Процесс:
        1. Сохраняем загруженный файл во временный файл
        2. Проверяем наличие всех обязательных колонок
        3. Проверяем, что файл не пустой
        4. Проверяем обязательные поля в каждой строке
        5. Если все проверки пройдены, заменяем основной файл
    """
    try:
        # Проверяем, что файл был передан
        if 'file' not in request.files:
            return jsonify({'error': 'Файл не найден'}), 400
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'Файл не выбран'}), 400
        
        # Проверяем расширение файла
        if not file.filename.endswith('.csv'):
            return jsonify({'error': 'Поддерживаются только CSV файлы'}), 400
        
        # Сохраняем во временный файл для проверки
        temp_path = DATASET_PATH + '.tmp'
        file.save(temp_path)
        
        with open(temp_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            
            # Проверяем наличие всех обязательных колонок
            required_fields = ['user_id', 'last_name', 'first_name', 'wk_solved_task_count', 
                              'wk_points', 'wk_max_task_count', 'wk_max_points', 'grade', 
                              'period_type', 'period_number', 'period_year', 'favorite_day',
                              'activity_type', 'total_events', 'total_minutes']
            
            missing_fields = [field for field in required_fields if field not in reader.fieldnames]
            
            if missing_fields:
                os.remove(temp_path)
                return jsonify({
                    'error': f'Неверная структура датасета: отсутствуют колонки: {", ".join(missing_fields)}'
                }), 400
            
            # Проверяем, что файл не пустой
            rows = list(reader)
            if len(rows) == 0:
                os.remove(temp_path)
                return jsonify({'error': 'CSV файл пуст'}), 400
            
            # Проверяем обязательные поля в каждой строке
            for i, row in enumerate(rows):
                if not row.get('user_id') or not row.get('period_year') or not row.get('grade'):
                    os.remove(temp_path)
                    return jsonify({
                        'error': f'Неверная структура датасета: строка {i+1} содержит пустые обязательные поля (user_id, period_year, grade)'
                    }), 400
        
        # Если все проверки пройдены, заменяем основной файл
        os.replace(temp_path, DATASET_PATH)
        
        return jsonify({'status': 'success', 'message': f'Загружено {len(rows)} записей', 'count': len(rows)})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ===================================================================================================================
#                                                API эндпоинты для генерации сертификатов
# ===================================================================================================================

@app.route('/api/share/generate', methods=['POST'])
def generate_share_token():
    """
    Генерирует уникальную ссылку на сертификат для указанного ученика и периода.
    
    Процесс:
        1. Проверяем наличие обязательных полей в запросе
        2. Загружаем данные ученика из датасета
        3. Сохраняем все данные в базу данных (фиксируем снимок)
        4. Генерируем UUID-токен
        5. Возвращаем ссылку вида /share/{token}
    """
    try:
        data = request.json
        
        # Проверяем наличие обязательных полей
        required_fields = ['id', 'period_type', 'period_number', 'period_year']
        
        for field in required_fields:
            if field not in data:
                return jsonify({'error': f'Отсутствует обязательное поле: {field}'}), 400
        
        student_id = data['id']
        period_type = data['period_type']
        period_number = data['period_number']
        period_year = data['period_year']
        
        # Валидация типа периода
        if period_type not in ['year', 'trimester']:
            return jsonify({'error': 'Тип периода должен быть "year" или "trimester"'}), 400
        
        # Загружаем данные ученика из датасета
        student_data = load_student_from_dataset(student_id, period_type, period_number, period_year)
        
        # Обработка случаев, когда данные не найдены
        if student_data is None:
            return jsonify({'error': f'Данные за период {period_type} {period_number} {period_year} не найдены'}), 404
        
        # Обработка ошибки структуры датасета
        if isinstance(student_data, dict) and 'error' in student_data:
            return jsonify({'error': student_data['error']}), 400
        
        grade = student_data['grade']
        last_name = student_data['last_name']
        first_name = student_data['first_name']
        
        # Формируем полное имя ученика (если есть, иначе "Ученик {ID}")
        if last_name and first_name:
            student_full_name = f"{first_name} {last_name}"
        else:
            student_full_name = f"Ученик {student_id}"
        
        # Подготавливаем данные для сохранения в БД (фиксированный снимок)
        student_info = {
            'user_id': student_id,
            'last_name': last_name,
            'first_name': first_name,
            'grade': grade,
            'wk_solved_task_count': student_data['wk_solved_task_count'],
            'wk_points': student_data['wk_points'],
            'wk_max_task_count': student_data['wk_max_task_count'],
            'wk_max_points': student_data['wk_max_points'],
            'favorite_day': student_data['favorite_day'],
            'activity_type': student_data['activity_type'],
            'total_events': student_data['total_events'],
            'total_minutes': student_data['total_minutes'],
            'period_type': period_type,
            'period_number': period_number,
            'period_year': period_year
        }
        
        # Генерируем уникальный UUID-токен
        share_token = str(uuid.uuid4())
        period_name = get_period_name(period_type, period_number, period_year)
        
        # Сохраняем токен и данные в базу данных
        db = SessionLocal()
        new_token = ShareToken(
            token=share_token,
            student_name=student_full_name,
            student_data_json=json.dumps(student_info, ensure_ascii=False),
            period_type=period_type,
            period_number=period_number,
            period_year=period_year,
            age_group=determine_age_group(grade),
            grade=grade,
            is_active=True
        )
        db.add(new_token)
        db.commit()
        db.close()
        
        # Формируем полную ссылку
        share_link = f"{request.host_url}share/{share_token}"
        return jsonify({'status': 'success', 'share_link': share_link})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ===================================================================================================================
#                                                Публичные страницы
# ===================================================================================================================

@app.route('/share/<token>')
def view_shared_certificate(token):
    """
    Страница просмотра сертификата.
    
    Процесс:
        1. Ищем токен в базе данных
        2. Проверяем, активна ли ссылка
        3. Восстанавливаем данные ученика из JSON
        4. Генерируем отчёт (или берём из кеша)
        5. Отдаём HTML-страницу с PNG и кнопками
    """
    db = SessionLocal()
    try:
        # Ищем токен в базе данных
        share_record = db.query(ShareToken).filter(ShareToken.token == token).first()
        
        # Проверка существования токена
        if not share_record:
            return "Ссылка не найдена", 404
        
        # Проверка, не отозвана ли ссылка администратором
        if not share_record.is_active:
            return "Ссылка отозвана", 403
        
        # Восстанавливаем данные ученика из JSON
        student_data = json.loads(share_record.student_data_json)
        student_data['student_name'] = share_record.student_name
        student_data['grade'] = share_record.grade
        
        period_name = get_period_name(share_record.period_type, share_record.period_number, share_record.period_year)
        
        # Генерируем отчёт (или берём из кеша, если уже генерировали)
        png_path, pdf_path = report_gen.generate_report(student_data, share_record.age_group, period_name)
        report_gen.cache_paths[token] = (png_path, pdf_path)
        
        pdf_url = f"/api/download-pdf/{token}"
        png_filename = os.path.basename(png_path)
        
        # HTML-страница с отчётом и кнопками шеринга
        return render_template_string(f'''
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Твой отчёт — {share_record.student_name}</title>
            <style>
                * {{ margin: 0; padding: 0; box-sizing: border-box; }}
                body {{
                    background: #0F172A;
                    display: flex;
                    justify-content: center;
                    padding: 40px 20px;
                    font-family: 'Segoe UI', Arial, sans-serif;
                }}
                .container {{ max-width: 900px; width: 100%; }}
                .report-image {{
                    width: 100%;
                    border-radius: 24px;
                    box-shadow: 0 20px 40px rgba(0,0,0,0.4);
                    margin-bottom: 30px;
                }}
                .btn-group {{
                    display: flex;
                    flex-wrap: wrap;
                    gap: 12px;
                    justify-content: center;
                    background: #1E293B;
                    padding: 24px;
                    border-radius: 24px;
                    margin-bottom: 20px;
                }}
                button {{
                    padding: 12px 24px;
                    font-size: 16px;
                    font-weight: bold;
                    border: none;
                    border-radius: 40px;
                    cursor: pointer;
                    transition: 0.3s;
                }}
                button:hover {{ transform: translateY(-2px); }}
                .btn-png {{ background: #10B981; color: white; }}
                .btn-pdf {{ background: #DC2626; color: white; }}
                .btn-vk {{ background: #0077FF; color: white; }}
                .btn-telegram {{ background: #0088cc; color: white; }}
                .btn-whatsapp {{ background: #25D366; color: white; }}
                .btn-email {{ background: #EA4335; color: white; }}
                .btn-copy {{ background: #6B7280; color: white; }}
                .share-link-box {{
                    background: #1E293B;
                    border-radius: 16px;
                    padding: 16px;
                    display: flex;
                    gap: 12px;
                }}
                .share-link-box input {{
                    flex: 1;
                    padding: 12px;
                    background: #0F172A;
                    border: 1px solid #334155;
                    border-radius: 12px;
                    color: white;
                }}
                .success-message {{
                    background: #10B981;
                    color: white;
                    padding: 12px;
                    border-radius: 12px;
                    margin-top: 16px;
                    text-align: center;
                    display: none;
                    font-weight: bold;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <img src="/static/reports/{png_filename}" class="report-image" alt="Отчёт">
                <div class="btn-group">
                    <button class="btn-png" onclick="downloadPNG()">Скачать PNG</button>
                    <button class="btn-pdf" onclick="downloadPDF()">Скачать PDF</button>
                    <button class="btn-vk" onclick="shareVK()">ВКонтакте</button>
                    <button class="btn-telegram" onclick="shareTelegram()">Telegram</button>
                    <button class="btn-whatsapp" onclick="shareWhatsApp()">WhatsApp</button>
                    <button class="btn-email" onclick="shareEmail()">Email</button>
                    <button class="btn-copy" onclick="copyLink()">Копировать ссылку</button>
                </div>
                <div class="share-link-box">
                    <input type="text" id="shareUrl" value="{request.url}" readonly>
                    <button class="btn-copy" onclick="copyLink()">Копировать</button>
                </div>
                <div id="successMsg" class="success-message">✅ Ссылка скопирована!</div>
            </div>
            <script>
                const shareUrl = document.getElementById('shareUrl').value;
                const pdfUrl = "{pdf_url}";
                const studentName = "{share_record.student_name}";
                function downloadPDF() {{ window.location.href = pdfUrl; }}
                function downloadPNG() {{
                    const img = document.querySelector('img');
                    const link = document.createElement('a');
                    link.href = img.src;
                    link.download = 'report.png';
                    link.click();
                }}
                function shareVK() {{
                    window.open('https://vk.com/share.php?url=' + encodeURIComponent(shareUrl) + '&title=' + encodeURIComponent('Мой отчёт'), '_blank');
                }}
                function shareTelegram() {{
                    window.open('https://t.me/share/url?url=' + encodeURIComponent(shareUrl) + '&text=' + encodeURIComponent('Посмотри мой отчёт!'), '_blank');
                }}
                function shareWhatsApp() {{
                    window.open('https://wa.me/?text=' + encodeURIComponent('Посмотри мой отчёт! Ссылка: ' + shareUrl), '_blank');
                }}
                function shareEmail() {{
                    window.location.href = 'mailto:?subject=' + encodeURIComponent('Мой отчёт') + '&body=' + encodeURIComponent('Посмотри мой отчёт! Ссылка: ' + shareUrl + ' С уважением, ' + studentName);
                }}
                function copyLink() {{
                    navigator.clipboard.writeText(shareUrl).then(() => {{
                        const msg = document.getElementById('successMsg');
                        msg.style.display = 'block';
                        setTimeout(() => msg.style.display = 'none', 2000);
                    }});
                }}
            </script>
        </body>
        </html>
        ''')
    finally:
        db.close()


@app.route('/api/download-pdf/<token>')
def download_pdf(token):
    """Скачивание PDF-версии отчёта."""
    # Проверяем, есть ли отчёт в кеше
    if token in report_gen.cache_paths:
        pdf_path = report_gen.cache_paths[token][1]
        return send_file(pdf_path, as_attachment=True,
                        download_name=f"report_{token}.pdf",
                        mimetype='application/pdf')
    return "Файл не найден", 404


@app.route('/static/reports/<filename>')
def serve_report_image(filename):
    """Отдача PNG-изображений отчётов (виртуальный маршрут, файлы берутся из share_cache/)."""
    from flask import send_from_directory
    return send_from_directory('share_cache/', filename)


# ===================================================================================================================
#                                                Главная и тестовая страницы
# ===================================================================================================================

@app.route('/')
def index():
    """Главная страница с описанием проекта и мотивационными блоками."""
    return render_template_string('''
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Certify Real</title>
        <style>
            * { margin: 0; padding: 0; box-sizing: border-box; }
            body {
                font-family: 'Segoe UI', Arial, sans-serif;
                background: linear-gradient(135deg, #0F172A 0%, #1E293B 100%);
                min-height: 100vh;
            }
            .header {
                background: rgba(15, 23, 42, 0.95);
                padding: 20px 40px;
                border-bottom: 1px solid #334155;
            }
            .header-content {
                max-width: 1200px;
                margin: 0 auto;
                display: flex;
                justify-content: space-between;
                align-items: center;
                flex-wrap: wrap;
                gap: 20px;
            }
            .logo {
                font-size: 28px;
                font-weight: bold;
                color: #38BDF8;
            }
            .logo span { color: #F97316; }
            .nav a {
                color: #94A3B8;
                text-decoration: none;
                margin-left: 30px;
            }
            .nav a:hover { color: #38BDF8; }
            .container { max-width: 1200px; margin: 0 auto; padding: 40px; }
            .hero {
                text-align: center;
                margin-bottom: 60px;
            }
            .hero h1 {
                font-size: 48px;
                color: #F1F5F9;
                margin-bottom: 20px;
            }
            .hero p {
                font-size: 20px;
                color: #94A3B8;
            }
            .stats-grid {
                display: grid;
                grid-template-columns: repeat(4, 1fr);
                gap: 24px;
                margin-bottom: 60px;
            }
            .stat-card {
                background: #1E293B;
                border-radius: 20px;
                padding: 28px 24px;
                text-align: center;
                border: 1px solid #334155;
            }
            .stat-title {
                font-size: 24px;
                font-weight: bold;
                margin-bottom: 20px;
                color: #38BDF8;
            }
            .stat-text {
                color: #94A3B8;
                font-size: 15px;
                line-height: 1.6;
            }
            .age-stats {
                display: grid;
                grid-template-columns: repeat(2, 1fr);
                gap: 24px;
                margin-bottom: 60px;
            }
            .age-card {
                background: #1E293B;
                border-radius: 20px;
                padding: 24px;
                text-align: center;
                border: 1px solid #334155;
            }
            .age-card.primary { border-top: 4px solid #10B981; }
            .age-card.senior { border-top: 4px solid #F97316; }
            .age-title {
                font-size: 20px;
                font-weight: bold;
                margin-bottom: 16px;
            }
            .age-title.primary { color: #10B981; }
            .age-title.senior { color: #F97316; }
            .age-desc {
                color: #94A3B8;
                font-size: 14px;
                line-height: 1.5;
            }
            .action-card {
                background: #1E293B;
                border-radius: 20px;
                padding: 40px;
                text-align: center;
                border: 1px solid #334155;
            }
            .action-card h3 { color: #F1F5F9; font-size: 24px; margin-bottom: 16px; }
            .action-card p { color: #94A3B8; margin-bottom: 24px; }
            .btn-test {
                background: #38BDF8;
                color: #0F172A;
                padding: 12px 32px;
                border-radius: 40px;
                text-decoration: none;
                font-weight: bold;
                display: inline-block;
            }
            .btn-test:hover { background: #F97316; }
            .footer {
                text-align: center;
                padding: 40px;
                color: #64748B;
                border-top: 1px solid #334155;
                margin-top: 60px;
            }
            @media (max-width: 768px) {
                .stats-grid { grid-template-columns: repeat(2, 1fr); }
                .age-stats { grid-template-columns: 1fr; }
            }
        </style>
    </head>
    <body>
        <div class="header">
            <div class="header-content">
                <div class="logo">Certify<span>Real</span></div>
                <div class="nav">
                    <a href="/">Главная</a>
                    <a href="/test">Тестовая страница</a>
                    <a href="/api/students">API</a>
                </div>
            </div>
        </div>
        
        <div class="container">
            <div class="hero">
                <h1>Certify Real</h1>
                <p>Персонализированные отчёты на основе реальных метрик</p>
            </div>
            
            <div class="stats-grid">
                <div class="stat-card">
                    <div class="stat-title">Знания открывают двери</div>
                    <div class="stat-text">Каждый новый навык делает тебя увереннее и расширяет твои возможности в будущем.</div>
                </div>
                <div class="stat-card">
                    <div class="stat-title">Учёба развивает мышление</div>
                    <div class="stat-text">Решение задач тренирует мозг, учит анализировать и находить нестандартные решения.</div>
                </div>
                <div class="stat-card">
                    <div class="stat-title">Знания = свобода выбора</div>
                    <div class="stat-text">Чем больше ты знаешь, тем больше профессий и путей тебе открыто.</div>
                </div>
                <div class="stat-card">
                    <div class="stat-title">Успех начинается сегодня</div>
                    <div class="stat-text">Маленькие шаги каждый день приводят к большим результатам в будущем.</div>
                </div>
            </div>
            
            <div class="age-stats">
                <div class="age-card primary">
                    <div class="age-title primary">Путь динозаврика Дино</div>
                    <div class="age-desc">Приключение начинается! Каждое задание — новый шаг вперёд. Учись, играй и расти вместе с Дино!</div>
                </div>
                <div class="age-card senior">
                    <div class="age-title senior">Школа — это только стартовая площадка</div>
                    <div class="age-desc">Твои знания и навыки сегодня — фундамент для великих достижений завтра. Продолжай учиться и мечтать!</div>
                </div>
            </div>
            
            <div class="action-card">
                <h3>Создать сертификат</h3>
                <p>Перейдите на тестовую страницу, чтобы создать сертификат для любого ученика</p>
                <a href="/test" class="btn-test">Перейти к тесту →</a>
            </div>
        </div>
        
        <div class="footer">
            <p>Certify Real — персонализированные отчёты на основе реальных метрик</p>
        </div>
    </body>
    </html>
    ''')


@app.route('/test')
def test_page():
    """
    Тестовая страница для ручной генерации сертификатов (только для разработчиков).
    Позволяет выбрать ученика, год и период, и получить ссылку на отчёт.
    """
    students = get_all_students_list()
    
    return render_template_string('''
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Создание отчёта - Certify Real</title>
        <style>
            * { margin: 0; padding: 0; box-sizing: border-box; }
            body {
                font-family: 'Segoe UI', Arial, sans-serif;
                background: linear-gradient(135deg, #0F172A 0%, #1E293B 100%);
                min-height: 100vh;
            }
            .header {
                background: rgba(15, 23, 42, 0.95);
                padding: 20px 40px;
                border-bottom: 1px solid #334155;
            }
            .header-content {
                max-width: 1200px;
                margin: 0 auto;
                display: flex;
                justify-content: space-between;
                align-items: center;
            }
            .logo {
                font-size: 28px;
                font-weight: bold;
                color: #38BDF8;
            }
            .logo span { color: #F97316; }
            .nav a {
                color: #94A3B8;
                text-decoration: none;
                margin-left: 30px;
            }
            .container { max-width: 600px; margin: 0 auto; padding: 40px 20px; }
            .card {
                background: #1E293B;
                border-radius: 24px;
                padding: 32px;
                border: 1px solid #334155;
            }
            .card h1 { color: #F1F5F9; font-size: 28px; margin-bottom: 8px; }
            .card .subtitle { color: #94A3B8; margin-bottom: 24px; }
            .form-group { margin-bottom: 20px; }
            label { 
                display: block; 
                color: #94A3B8; 
                margin-bottom: 8px;
                font-weight: bold;
            }
            select, input {
                width: 100%;
                padding: 12px;
                background: #0F172A;
                border: 1px solid #334155;
                border-radius: 12px;
                color: white;
                font-size: 16px;
            }
            input[type="text"] {
                -moz-appearance: textfield;
            }
            select:disabled, input:disabled {
                opacity: 0.5;
                cursor: not-allowed;
            }
            button {
                width: 100%;
                padding: 14px;
                background: #38BDF8;
                border: none;
                border-radius: 40px;
                font-weight: bold;
                cursor: pointer;
                font-size: 16px;
                margin-top: 20px;
            }
            button:hover:not(:disabled) { background: #F97316; }
            button:disabled {
                opacity: 0.5;
                cursor: not-allowed;
            }
            .result {
                margin-top: 24px;
                padding: 20px;
                background: #0F172A;
                border-radius: 16px;
                word-break: break-all;
                color: #F1F5F9;
            }
            .result a { color: #38BDF8; }
            .result strong { color: #10B981; }
            .error {
                color: #EF4444;
                background: rgba(239, 68, 68, 0.1);
                padding: 12px;
                border-radius: 12px;
                margin-top: 16px;
            }
            .student-list {
                background: #0F172A;
                border-radius: 16px;
                padding: 16px;
                margin-bottom: 24px;
            }
            .student-item {
                padding: 8px;
                border-bottom: 1px solid #334155;
                color: #94A3B8;
            }
            .footer {
                text-align: center;
                padding: 40px;
                color: #64748B;
                border-top: 1px solid #334155;
                margin-top: 40px;
            }
        </style>
    </head>
    <body>
        <div class="header">
            <div class="header-content">
                <div class="logo">Certify<span>Real</span></div>
                <div class="nav">
                    <a href="/">Главная</a>
                    <a href="/test">Создать отчёт</a>
                </div>
            </div>
        </div>
        
        <div class="container">
            <div class="card">
                <h1>Создать отчёт</h1>
                <div class="subtitle">Выберите ученика и период обучения</div>
                
                <div class="student-list">
                    <div style="color: #F1F5F9; margin-bottom: 8px;">Доступные ученики:</div>
                    {% for student in students %}
                    <div class="student-item">ID {{ student.user_id }} — {{ student.first_name }} {{ student.last_name }}</div>
                    {% endfor %}
                </div>
                
                <form id="certForm">
                    <div class="form-group">
                        <label>👨‍🎓 ID ученика</label>
                        <input type="text" id="studentId" placeholder="Введите ID ученика (например, 1)" required inputmode="numeric" pattern="[0-9]*">
                    </div>
                    
                    <div class="form-group">
                        <label>📅 Учебный год</label>
                        <select id="periodYear" required disabled>
                            <option value="">Сначала выберите ученика</option>
                        </select>
                    </div>
                    
                    <div class="form-group">
                        <label>📚 Период обучения</label>
                        <select id="periodSelect" required disabled>
                            <option value="">Сначала выберите год</option>
                        </select>
                    </div>
                    
                    <button type="submit" id="submitBtn" disabled>Создать отчёт</button>
                </form>
                
                <div id="result" class="result" style="display: none;"></div>
            </div>
        </div>
        
        <div class="footer">
            <p>Certify Real — персонализированные отчёты</p>
        </div>
        
        <script>
            let availablePeriods = {};
            let currentStudentId = null;
            let currentYear = null;
            
            async function loadAvailablePeriods(studentId) {
                try {
                    const response = await fetch(`/api/student-available-periods/${studentId}`);
                    const data = await response.json();
                    
                    if (response.ok && data.status === 'success') {
                        availablePeriods = data;
                        
                        const yearSelect = document.getElementById('periodYear');
                        yearSelect.innerHTML = '<option value="">Выберите учебный год</option>';
                        
                        if (data.years && data.years.length > 0) {
                            data.years.forEach(year => {
                                const option = document.createElement('option');
                                option.value = year;
                                option.textContent = `${year} учебный год`;
                                yearSelect.appendChild(option);
                            });
                            yearSelect.disabled = false;
                            yearSelect.value = '';
                        } else {
                            yearSelect.innerHTML = '<option value="">Нет данных за периоды</option>';
                            yearSelect.disabled = true;
                        }
                        
                        document.getElementById('periodSelect').disabled = true;
                        document.getElementById('periodSelect').innerHTML = '<option value="">Сначала выберите год</option>';
                        document.getElementById('submitBtn').disabled = true;
                    } else {
                        throw new Error(data.error || 'Не удалось загрузить периоды');
                    }
                } catch (error) {
                    console.error('Ошибка:', error);
                    const yearSelect = document.getElementById('periodYear');
                    yearSelect.innerHTML = `<option value="">Ошибка: ${error.message}</option>`;
                    yearSelect.disabled = true;
                }
            }
            
            function updatePeriodsByYear(year) {
                const periodSelect = document.getElementById('periodSelect');
                
                if (!year || !availablePeriods.periods_by_year || !availablePeriods.periods_by_year[year]) {
                    periodSelect.innerHTML = '<option value="">Нет данных за выбранный год</option>';
                    periodSelect.disabled = true;
                    document.getElementById('submitBtn').disabled = true;
                    return;
                }
                
                const yearData = availablePeriods.periods_by_year[year];
                periodSelect.innerHTML = '';
                
                let hasAnyPeriod = false;
                
                if (yearData.year) {
                    const option = document.createElement('option');
                    option.value = JSON.stringify({type: 'year', number: 1});
                    option.textContent = '📖 Весь учебный год';
                    periodSelect.appendChild(option);
                    hasAnyPeriod = true;
                }
                
                if (yearData.trimesters && yearData.trimesters.length > 0) {
                    yearData.trimesters.forEach(trimester => {
                        const option = document.createElement('option');
                        option.value = JSON.stringify({type: 'trimester', number: trimester});
                        let trimesterText = '';
                        if (trimester === 1) trimesterText = '1 триместр';
                        else if (trimester === 2) trimesterText = '2 триместр';
                        else trimesterText = `${trimester} триместр`;
                        option.textContent = `📚 ${trimesterText}`;
                        periodSelect.appendChild(option);
                        hasAnyPeriod = true;
                    });
                }
                
                if (hasAnyPeriod) {
                    periodSelect.disabled = false;
                    document.getElementById('submitBtn').disabled = false;
                } else {
                    periodSelect.innerHTML = '<option value="">Нет доступных периодов</option>';
                    periodSelect.disabled = true;
                    document.getElementById('submitBtn').disabled = true;
                }
            }
            
            document.getElementById('studentId').addEventListener('change', async (e) => {
                const studentId = parseInt(e.target.value);
                if (studentId && !isNaN(studentId)) {
                    currentStudentId = studentId;
                    await loadAvailablePeriods(studentId);
                } else {
                    document.getElementById('periodYear').disabled = true;
                    document.getElementById('periodSelect').disabled = true;
                    document.getElementById('submitBtn').disabled = true;
                }
            });
            
            document.getElementById('periodYear').addEventListener('change', (e) => {
                currentYear = e.target.value;
                if (currentYear) {
                    updatePeriodsByYear(currentYear);
                } else {
                    document.getElementById('periodSelect').disabled = true;
                    document.getElementById('submitBtn').disabled = true;
                }
            });
            
            document.getElementById('certForm').addEventListener('submit', async (e) => {
                e.preventDefault();
                
                const studentId = document.getElementById('studentId').value;
                const year = document.getElementById('periodYear').value;
                const periodValue = document.getElementById('periodSelect').value;
                
                if (!studentId || !year || !periodValue) {
                    alert('Пожалуйста, заполните все поля');
                    return;
                }
                
                let periodData;
                try {
                    periodData = JSON.parse(periodValue);
                } catch (error) {
                    alert('Ошибка при выборе периода');
                    return;
                }
                
                const resultDiv = document.getElementById('result');
                resultDiv.style.display = 'block';
                resultDiv.innerHTML = '<div class="loading">Генерация отчёта...</div>';
                
                try {
                    const response = await fetch('/api/share/generate', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({
                            id: parseInt(studentId),
                            period_type: periodData.type,
                            period_number: parseInt(periodData.number),
                            period_year: parseInt(year)
                        })
                    });
                    
                    const data = await response.json();
                    
                    if (response.ok) {
                        resultDiv.innerHTML = `<strong>✅ Готово!</strong><br><a href="${data.share_link}" target="_blank">${data.share_link}</a>`;
                    } else {
                        resultDiv.innerHTML = `<div class="error"><strong>❌ Ошибка:</strong> ${data.error}</div>`;
                    }
                } catch (error) {
                    resultDiv.innerHTML = `<div class="error"><strong>❌ Ошибка:</strong> ${error.message}</div>`;
                }
            });
        </script>
    </body>
    </html>
    ''', students=students)


# ===================================================================================================================
#                                                Запуск сервера
# ===================================================================================================================

if __name__ == '__main__':
    # Получаем порт из переменной окружения (для Render.com) или используем 5001 по умолчанию
    port = int(os.environ.get('PORT', 5001))
    print("\n" + "="*50)
    print(f"Сервер запущен: http://localhost:{port}")
    print(f"Тест: http://localhost:{port}/test")
    print("="*50)
    app.run(host='0.0.0.0', port=port, debug=True)