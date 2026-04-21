# Импорт библиотек и модулей
from flask import Flask, request, send_file, render_template_string, jsonify
from datetime import datetime, timedelta
import json
import uuid
import csv
import os
from database import SessionLocal, ShareToken
from certificate_generator import ReportGenerator

# Инициализация приложения Flask и зависимостей
app = Flask(__name__)
report_gen = ReportGenerator()

# Конфигурация путей и директорий
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATASET_PATH = os.path.join(BASE_DIR, 'students.csv')

os.makedirs('share_cache', exist_ok=True)
os.makedirs('templates', exist_ok=True)

# Определение структуры CSV (поля)
CSV_FIELDS = ['id', 'name', 'grade', 'gender', 'period_type', 'period_number',
              'total_hours', 'avg_score', 'most_time_topic', 'avg_attempts', 'homework_completion',
              'regularity_score', 'streak_days', 'badges_count']

# ===================================================================================================================
#                                                Функции для работы с данными
# ===================================================================================================================
def _extract_student_data(row):
    return {
        'student_name': row['name'],
        'course_name': '',
        'grade': int(row['grade']),
        'gender': row.get('gender', 'male'),
        'total_hours': float(row.get('total_hours', 0)),
        'avg_score': int(row.get('avg_score', 0)),
        'streak_days': int(row.get('streak_days', 0)),
        'most_time_topic': row.get('most_time_topic', ''),
        'avg_attempts': float(row.get('avg_attempts', 1)),
        'homework_completion': int(row.get('homework_completion', 0)),
        'regularity_score': int(row.get('regularity_score', 0)),
        'badges_count': int(row.get('badges_count', 0))
    }

def load_student_from_dataset(student_id, period_type='year', period_number=None):
    try:
        if not os.path.exists(DATASET_PATH):
            return None
        
        with open(DATASET_PATH, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            
            for row in reader:
                if int(row['id']) == student_id:
                    row_period_type = row.get('period_type', 'year')
                    row_period_number = row.get('period_number', '')
                    
                    if period_type == 'year':
                        if row_period_type == 'year' and str(row_period_number) == str(period_number):
                            return _extract_student_data(row)
                    else:
                        if (row_period_type == period_type and 
                            str(row_period_number) == str(period_number)):
                            return _extract_student_data(row)
            
            return None
    except Exception as e:
        print(f"Ошибка: {e}")
        return None

def get_all_students_list():
    try:
        if not os.path.exists(DATASET_PATH):
            return []
        
        students_dict = {}
        with open(DATASET_PATH, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                student_id = int(row['id'])
                if student_id not in students_dict:
                    students_dict[student_id] = {
                        'id': student_id,
                        'name': row['name']
                    }
        return list(students_dict.values())
    except:
        return []

def get_next_student_id():
    students = get_all_students_list()
    if not students:
        return 1
    return max([s['id'] for s in students]) + 1

# Определение возрастной группы
def determine_age_group(grade):
    if grade <= 4:
        return 'primary'
    else:
        return 'senior'

# Получение периода дат по типу и номеру
def get_period_dates(period_type, period_number, period_year):
    if period_type == 'quarter':
        quarters = {1: (9, 1, 11, 30), 2: (12, 1, 2, 28), 3: (3, 1, 5, 31)}
        if period_number in quarters:
            start_m, start_d, end_m, end_d = quarters[period_number]
            start_date = datetime(period_year, start_m, start_d)
            if period_number == 2:
                end_date = datetime(period_year + 1, end_m, end_d)
            else:
                end_date = datetime(period_year, end_m, end_d)
        else:
            start_date = datetime(period_year, 9, 1)
            end_date = datetime(period_year + 1, 5, 31)
    elif period_type == 'trimester':
        trimesters = {1: (9, 1, 11, 30), 2: (12, 1, 2, 28), 3: (3, 1, 5, 31)}
        if period_number in trimesters:
            start_m, start_d, end_m, end_d = trimesters[period_number]
            start_date = datetime(period_year, start_m, start_d)
            if period_number == 2:
                end_date = datetime(period_year + 1, end_m, end_d)
            else:
                end_date = datetime(period_year, end_m, end_d)
        else:
            start_date = datetime(period_year, 9, 1)
            end_date = datetime(period_year + 1, 5, 31)
    else:
        start_date = datetime(period_year, 9, 1)
        end_date = datetime(period_year + 1, 5, 31)
    return start_date, end_date

#Расчёт локации динозаврика по XP
def calculate_dino_location(xp):
    if xp < 100: return 0
    elif xp < 300: return 1
    elif xp < 600: return 2
    elif xp < 1000: return 3
    elif xp < 1500: return 4
    elif xp < 2100: return 5
    return 6

# Получение активности студента (метрики + XP)
def get_activity_data(student_id, period_type, period_number):
    student_data = load_student_from_dataset(student_id, period_type, period_number)
    if not student_data:
        return None
    
    metrics = {
        'total_hours': student_data.get('total_hours', 0),
        'avg_score': student_data.get('avg_score', 0),
        'streak_days': student_data.get('streak_days', 0),
        'most_time_topic': student_data.get('most_time_topic', ''),
        'avg_attempts': student_data.get('avg_attempts', 1),
        'homework_completion': student_data.get('homework_completion', 0),
        'regularity_score': student_data.get('regularity_score', 0),
        'badges_count': student_data.get('badges_count', 0),
        'gender': student_data.get('gender', 'male')
    }
    
    xp = metrics['total_hours'] * 10 + metrics['badges_count'] * 50 + metrics['avg_attempts'] * 20
    dino_location = calculate_dino_location(xp)
    
    return {
        'metrics': metrics,
        'dino_location': dino_location,
        'grade': student_data['grade'],
        'gender': metrics['gender']
    }

# Названия периода
def get_period_name(period_type, period_number, period_year):
    if period_type == 'quarter':
        return f"{period_year} учебный год, {period_number} четверть"
    elif period_type == 'trimester':
        return f"{period_year} учебный год, {period_number} триместр"
    else:
        return f"{period_year} учебный год"
# ================================================================================================================================
#                                                    API-эндпоинты для работы со студентами
# ================================================================================================================================
@app.route('/api/students', methods=['GET'])
def get_students():
    students = get_all_students_list()
    return jsonify({'status': 'success', 'count': len(students), 'students': students})

@app.route('/api/student/<int:student_id>', methods=['GET'])
def get_student(student_id):
    student = load_student_from_dataset(student_id, 'year', 1)
    if not student:
        return jsonify({'error': 'Ученик не найден'}), 404
    return jsonify({'status': 'success', 'student': student})

@app.route('/api/students/add', methods=['POST'])
def add_student():
    try:
        data = request.json
        if not data.get('name'):
            return jsonify({'error': 'Не указано имя'}), 400
        
        student_id = data.get('id', get_next_student_id())
        grade = data.get('grade', 5)
        
        new_student = {
            'id': student_id,
            'name': data['name'],
            'grade': grade,
            'gender': data.get('gender', 'male'),
            'period_type': data.get('period_type', 'year'),
            'period_number': data.get('period_number', ''),
            'total_hours': data.get('total_hours', 0),
            'avg_score': data.get('avg_score', 0),
            'streak_days': data.get('streak_days', 0),
            'most_time_topic': data.get('most_time_topic', ''),
            'avg_attempts': data.get('avg_attempts', 1),
            'homework_completion': data.get('homework_completion', 0),
            'regularity_score': data.get('regularity_score', 0),
            'badges_count': data.get('badges_count', 0)
        }
        
        file_exists = os.path.exists(DATASET_PATH) and os.path.getsize(DATASET_PATH) > 0
        with open(DATASET_PATH, 'a', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=CSV_FIELDS)
            if not file_exists:
                writer.writeheader()
            writer.writerow(new_student)
        
        return jsonify({'status': 'success', 'message': f'Ученик {data["name"]} добавлен'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/students/update/<int:student_id>', methods=['PUT'])
def update_student(student_id):
    try:
        data = request.json
        rows = []
        found = False
        with open(DATASET_PATH, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            rows = list(reader)
        
        for row in rows:
            if int(row['id']) == student_id:
                found = True
                for key, value in data.items():
                    if key in row:
                        row[key] = value
                break
        
        if not found:
            return jsonify({'error': 'Ученик не найден'}), 404
        
        with open(DATASET_PATH, 'w', encoding='utf-8', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=CSV_FIELDS)
            writer.writeheader()
            writer.writerows(rows)
        
        return jsonify({'status': 'success', 'message': f'Ученик ID {student_id} обновлён'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    
# ===================================================================================================================================   
#                                                    API-эндпоинт для генерации шеринг-ссылки
# ===================================================================================================================================
@app.route('/api/students/upload-csv', methods=['POST'])
def upload_csv():
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'Файл не найден'}), 400
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'Файл не выбран'}), 400
        file.save(DATASET_PATH)
        with open(DATASET_PATH, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            count = len(list(reader))
        return jsonify({'status': 'success', 'message': f'Загружено {count} записей', 'count': count})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/share/generate', methods=['POST'])
def generate_share_token():
    try:
        data = request.json
        if not data.get('id'):
            return jsonify({'error': 'Не передан ID ученика'}), 400
        
        if not data.get('period_type'):
            return jsonify({'error': 'Не указан тип периода (period_type)'}), 400
        
        student_id = data['id']
        period_type = data['period_type']
        period_number = data.get('period_number')
        period_year = datetime.now().year
        
        if period_type == 'year':
            if period_number is None or period_number == '':
                return jsonify({'error': 'Для учебного года необходимо указать номер периода'}), 400
        
        if period_type != 'year' and (period_number is None or period_number == ''):
            return jsonify({'error': f'Для периода "{period_type}" необходимо указать номер периода'}), 400
        
        activity_data = get_activity_data(student_id, period_type, period_number)
        if not activity_data:
            return jsonify({'error': f'Данные за период {period_type} {period_number} не найдены'}), 404
        
        metrics = activity_data['metrics']
        student_base = load_student_from_dataset(student_id, period_type, period_number)
        
        if not student_base:
            return jsonify({'error': 'Ученик не найден'}), 404
        
        student_info = {
            'id': student_id,
            'student_name': student_base['student_name'],
            'course_name': '',
            'grade': activity_data['grade'],
            'gender': activity_data['gender'],
            'total_hours': metrics['total_hours'],
            'avg_score': metrics['avg_score'],
            'streak_days': metrics['streak_days'],
            'most_time_topic': metrics['most_time_topic'],
            'avg_attempts': metrics['avg_attempts'],
            'homework_completion': metrics['homework_completion'],
            'regularity_score': metrics['regularity_score'],
            'badges_count': metrics['badges_count'],
            'dino_location': activity_data['dino_location']
        }
        
        share_token = str(uuid.uuid4())
        period_name = get_period_name(period_type, period_number, period_year)
        
        db = SessionLocal()
        new_token = ShareToken(
            token=share_token,
            student_name=student_base['student_name'],
            course_name='',
            student_data_json=json.dumps(student_info, ensure_ascii=False),
            period_type=period_type,
            period_number=period_number,
            period_year=period_year,
            age_group=determine_age_group(activity_data['grade']),
            grade=activity_data['grade'],
            is_active=True
        )
        db.add(new_token)
        db.commit()
        db.close()
        
        share_link = f"{request.host_url}share/{share_token}"
        return jsonify({'status': 'success', 'share_link': share_link, 'token': share_token,
                       'period_name': period_name, 'age_group': determine_age_group(activity_data['grade']),
                       'student_name': student_base['student_name'], 'course_name': ''})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/share/<token>')
def view_shared_certificate(token):
    db = SessionLocal()
    try:
        share_record = db.query(ShareToken).filter(ShareToken.token == token).first()
        if not share_record:
            return "Ссылка не найдена", 404
        if not share_record.is_active:
            return "Ссылка отозвана", 403
        
        student_data = json.loads(share_record.student_data_json)
        student_data['student_name'] = share_record.student_name
        student_data['grade'] = share_record.grade
        
        period_name = get_period_name(share_record.period_type, share_record.period_number, share_record.period_year)
        
        png_path, pdf_path = report_gen.generate_report(student_data, share_record.age_group, period_name)
        report_gen.cache_paths[token] = (png_path, pdf_path)
        
        share_url = request.url
        pdf_url = f"/api/download-pdf/{token}"
        png_filename = os.path.basename(png_path)
        
        # =========================================================================================================================
        #                                           Веб-страница просмотра сертификата по токену
        # =========================================================================================================================
        return render_template_string('''
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Твой отчёт — ''' + share_record.student_name + '''</title>
            <style>
                * { margin: 0; padding: 0; box-sizing: border-box; }
                body {
                    background: #0F172A;
                    display: flex;
                    justify-content: center;
                    padding: 40px 20px;
                    font-family: 'Segoe UI', Arial, sans-serif;
                }
                .container { max-width: 900px; width: 100%; }
                .report-image {
                    width: 100%;
                    border-radius: 24px;
                    box-shadow: 0 20px 40px rgba(0,0,0,0.4);
                    margin-bottom: 30px;
                }
                .btn-group {
                    display: flex;
                    flex-wrap: wrap;
                    gap: 12px;
                    justify-content: center;
                    background: #1E293B;
                    padding: 24px;
                    border-radius: 24px;
                    margin-bottom: 20px;
                }
                button {
                    padding: 12px 24px;
                    font-size: 16px;
                    font-weight: bold;
                    border: none;
                    border-radius: 40px;
                    cursor: pointer;
                    transition: all 0.3s;
                }
                .btn-png { background: #10B981; color: white; }
                .btn-pdf { background: #DC2626; color: white; }
                .btn-vk { background: #0077FF; color: white; }
                .btn-telegram { background: #0088cc; color: white; }
                .btn-whatsapp { background: #25D366; color: white; }
                .btn-email { background: #EA4335; color: white; }
                .btn-copy { background: #6B7280; color: white; }
                button:hover { transform: translateY(-2px); box-shadow: 0 5px 15px rgba(0,0,0,0.2); }
                .share-link-box {
                    background: #1E293B;
                    border-radius: 16px;
                    padding: 16px;
                    display: flex;
                    gap: 12px;
                }
                .share-link-box input {
                    flex: 1;
                    padding: 12px;
                    border: 1px solid #334155;
                    border-radius: 12px;
                    background: #0F172A;
                    color: #F1F5F9;
                }
                .success-message {
                    background: #065F46;
                    color: #D1FAE5;
                    padding: 12px;
                    border-radius: 12px;
                    margin-top: 16px;
                    text-align: center;
                    display: none;
                }
            </style>
        </head>
        <body>
            <div class="container">
                <img src="/static/reports/''' + png_filename + '''" class="report-image" alt="Отчёт">
                
                <div class="btn-group">
                    <button class="btn-png" onclick="downloadPNG()">🖼️ Скачать PNG</button>
                    <button class="btn-pdf" onclick="downloadPDF()">📥 Скачать PDF</button>
                    <button class="btn-vk" onclick="shareVK()">📱 ВКонтакте</button>
                    <button class="btn-telegram" onclick="shareTelegram()">📱 Telegram</button>
                    <button class="btn-whatsapp" onclick="shareWhatsApp()">💬 WhatsApp</button>
                    <button class="btn-email" onclick="shareEmail()">✉️ Email</button>
                    <button class="btn-copy" onclick="copyLink()">🔗 Копировать ссылку</button>
                </div>
                
                <div class="share-link-box">
                    <input type="text" id="shareUrl" value="''' + share_url + '''" readonly>
                    <button class="btn-copy" onclick="copyLink()">Копировать</button>
                </div>
                <div id="successMsg" class="success-message">✅ Ссылка скопирована!</div>
            </div>
            
            <script>
                const shareUrl = document.getElementById('shareUrl').value;
                const pdfUrl = "''' + pdf_url + '''";
                const studentName = "''' + share_record.student_name + '''";
                
                function downloadPDF() { window.location.href = pdfUrl; }
                
                function downloadPNG() {
                    const img = document.querySelector('.report-image');
                    if (!img) {
                        alert('Изображение не найдено');
                        return;
                    }
                    const link = document.createElement('a');
                    link.href = img.src;
                    link.download = 'certificate.png';
                    link.click();
                }
                
                function shareVK() {
                    window.open('https://vk.com/share.php?url=' + encodeURIComponent(shareUrl) + '&title=' + encodeURIComponent('Мой отчёт'), '_blank');
                }
                
                function shareTelegram() {
                    window.open('https://t.me/share/url?url=' + encodeURIComponent(shareUrl) + '&text=' + encodeURIComponent('Посмотри мой отчёт!'), '_blank');
                }
                
                function shareWhatsApp() {
                    window.open('https://wa.me/?text=' + encodeURIComponent('Посмотри мой отчёт! Ссылка: ' + shareUrl), '_blank');
                }
                
                function shareEmail() {
                    window.location.href = 'mailto:?subject=' + encodeURIComponent('Мой отчёт') + '&body=' + encodeURIComponent('Посмотри мой отчёт! Ссылка: ' + shareUrl + ' С уважением, ' + studentName);
                }
                
                function copyLink() {
                    navigator.clipboard.writeText(shareUrl).then(() => {
                        const msg = document.getElementById('successMsg');
                        msg.style.display = 'block';
                        setTimeout(() => msg.style.display = 'none', 2000);
                    });
                }
            </script>
        </body>
        </html>
        ''')
    finally:
        db.close()

# ==================================================================================================================================
#                                                       API-эндпоинт для скачивания PDF
# ==================================================================================================================================
@app.route('/api/download-pdf/<token>')
def download_pdf(token):
    if token in report_gen.cache_paths:
        pdf_path = report_gen.cache_paths[token][1]
        return send_file(pdf_path, as_attachment=True,
                        download_name=f"certificate_{token}.pdf",
                        mimetype='application/pdf')
    return "Файл не найден", 404

# ==================================================================================================================================
#                                                       Маршрут для статических файлов отчётов
# ==================================================================================================================================
@app.route('/static/reports/<filename>')
def serve_report_image(filename):
    from flask import send_from_directory
    return send_from_directory('share_cache/', filename)


# Главная страница
@app.route('/')
def index():
    return render_template_string('''
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Certify Dashboard</title>
        <style>
            * { margin: 0; padding: 0; box-sizing: border-box; }
            body {
                font-family: 'Segoe UI', Arial, sans-serif;
                background: linear-gradient(135deg, #0F172A 0%, #1E293B 100%);
                min-height: 100vh;
            }
            .header {
                background: rgba(15, 23, 42, 0.95);
                backdrop-filter: blur(10px);
                padding: 20px 40px;
                border-bottom: 1px solid #334155;
                position: sticky;
                top: 0;
                z-index: 100;
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
                transition: color 0.3s;
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
                max-width: 600px;
                margin: 0 auto;
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
                transition: transform 0.3s, border-color 0.3s;
            }
            .stat-card:hover {
                transform: translateY(-5px);
                border-color: #38BDF8;
            }
            .stat-title {
                font-size: 24px;
                font-weight: bold;
                margin-bottom: 20px;
            }
            .stat-title.primary { color: #10B981; }
            .stat-title.secondary { color: #38BDF8; }
            .stat-title.accent { color: #F97316; }
            .stat-title.purple { color: #8B5CF6; }
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
                background: linear-gradient(135deg, #1E293B 0%, #0F172A 100%);
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
                background: linear-gradient(135deg, #1E293B 0%, #0F172A 100%);
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
                transition: all 0.3s;
                display: inline-block;
            }
            .btn-test:hover {
                background: #F97316;
                transform: translateY(-2px);
                box-shadow: 0 5px 15px rgba(249,115,22,0.3);
            }
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
                .header-content { flex-direction: column; text-align: center; }
                .nav a { margin: 0 15px; }
                .hero h1 { font-size: 32px; }
            }
        </style>
    </head>
    <body>
        <div class="header">
            <div class="header-content">
                <div class="logo">Certify<span>Hub</span></div>
                <div class="nav">
                    <a href="/">Главная</a>
                    <a href="/test">Тестовая страница</a>
                    <a href="/api/students">API</a>
                </div>
            </div>
        </div>
        
        <div class="container">
            <div class="hero">
                <h1>🎓 Генерация сертификатов</h1>
                <p>Персонализированные отчёты об успеваемости учеников с возможностью шеринга в соцсетях</p>
            </div>
            
            <div class="stats-grid">
                <div class="stat-card">
                    <div class="stat-title primary">ВНИМАТЕЛЬНОСТЬ</div>
                    <div class="stat-text">Умение замечать детали, не пропускать важное и доводить начатое до конца — ключ к глубокому пониманию материала.</div>
                </div>
                <div class="stat-card">
                    <div class="stat-title secondary">УСЕРДИЕ</div>
                    <div class="stat-text">Настойчивость в достижении цели, готовность пробовать снова и снова, даже когда что-то не получается с первого раза.</div>
                </div>
                <div class="stat-card">
                    <div class="stat-title accent">ПРИЛЕЖНОСТЬ</div>
                    <div class="stat-text">Регулярные занятия, системный подход и дисциплина — основа стабильного прогресса и высоких результатов.</div>
                </div>
                <div class="stat-card">
                    <div class="stat-title purple">ПЕРФЕКЦИОНИЗМ</div>
                    <div class="stat-text">Стремление к идеалу, выполнение заданий на высоком уровне и внимание к качеству каждой детали.</div>
                </div>
            </div>
            
            <div class="age-stats">
                <div class="age-card primary">
                    <div class="age-title primary">🦕 Путь динозаврика Дино</div>
                    <div class="age-desc">Приключение начинается! Каждое задание — новый шаг вперёд. Учись, играй и расти вместе с Дино!</div>
                </div>
                <div class="age-card senior">
                    <div class="age-title senior">🚀 Школа — это только стартовая площадка</div>
                    <div class="age-desc">Твои знания и навыки сегодня — фундамент для великих достижений завтра. Продолжай учиться и мечтать!</div>
                </div>
            </div>
            
            <div class="action-card">
                <h3>🚀 Создать сертификат</h3>
                <p>Перейдите на тестовую страницу, чтобы создать сертификат для любого ученика</p>
                <a href="/test" class="btn-test">🧪 Перейти к тесту →</a>
            </div>
        </div>
        
        <div class="footer">
            <p>Certify Service — генерация персонализированных образовательных отчётов</p>
            <p style="font-size: 12px; margin-top: 10px;">© 2026 Цифриум | Хакатон ADA</p>
        </div>
    </body>
    </html>
    ''')

# Тестовая страница 
@app.route('/test')
def test_page():
    students = get_all_students_list()
    
    return render_template_string('''
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Тестовая страница</title>
        <style>
            * { margin: 0; padding: 0; box-sizing: border-box; }
            body {
                font-family: 'Segoe UI', Arial, sans-serif;
                background: linear-gradient(135deg, #0F172A 0%, #1E293B 100%);
                min-height: 100vh;
            }
            .header {
                background: rgba(15, 23, 42, 0.95);
                backdrop-filter: blur(10px);
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
                transition: color 0.3s;
            }
            .nav a:hover { color: #38BDF8; }
            .container { max-width: 600px; margin: 0 auto; padding: 40px 20px; }
            .card {
                background: #1E293B;
                border-radius: 24px;
                padding: 32px;
                border: 1px solid #334155;
            }
            .card h1 {
                color: #F1F5F9;
                font-size: 28px;
                margin-bottom: 8px;
            }
            .card .subtitle {
                color: #94A3B8;
                margin-bottom: 24px;
                font-size: 14px;
            }
            .form-group {
                margin-bottom: 20px;
            }
            label {
                display: block;
                color: #94A3B8;
                margin-bottom: 8px;
                font-weight: 500;
            }
            input, select {
                width: 100%;
                padding: 12px 16px;
                background: #0F172A;
                border: 1px solid #334155;
                border-radius: 12px;
                color: #F1F5F9;
                font-size: 16px;
                transition: border-color 0.3s;
            }
            input:focus, select:focus {
                outline: none;
                border-color: #38BDF8;
            }
            button {
                width: 100%;
                padding: 14px;
                background: #38BDF8;
                border: none;
                border-radius: 40px;
                color: #0F172A;
                font-size: 16px;
                font-weight: bold;
                cursor: pointer;
                transition: all 0.3s;
                margin-top: 10px;
            }
            button:hover {
                background: #F97316;
                transform: translateY(-2px);
                box-shadow: 0 5px 15px rgba(249,115,22,0.3);
            }
            .result {
                margin-top: 24px;
                padding: 20px;
                background: #0F172A;
                border-radius: 16px;
                border-left: 4px solid #10B981;
                word-break: break-all;
                color: #F1F5F9;
            }
            .result a {
                color: #38BDF8;
                text-decoration: none;
            }
            .result a:hover {
                text-decoration: underline;
            }
            .student-list {
                background: #0F172A;
                border-radius: 16px;
                padding: 16px;
                margin-bottom: 24px;
                max-height: 200px;
                overflow-y: auto;
            }
            .student-item {
                padding: 8px 12px;
                border-bottom: 1px solid #334155;
                color: #94A3B8;
                font-size: 14px;
            }
            .student-item:last-child { border-bottom: none; }
            .student-id { color: #38BDF8; font-weight: bold; }
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
                <div class="logo">Certify<span>Hub</span></div>
                <div class="nav">
                    <a href="/">Главная</a>
                    <a href="/test">Тестовая страница</a>
                    <a href="/api/students">API</a>
                </div>
            </div>
        </div>
        
        <div class="container">
            <div class="card">
                <h1>🧪 Создать сертификат</h1>
                <div class="subtitle">Введите данные ученика и период обучения</div>
                
                <div class="student-list">
                    <div style="color: #F1F5F9; margin-bottom: 8px; font-weight: bold;">📋 Доступные ученики:</div>
                    {% for s in students %}
                    <div class="student-item">
                        <span class="student-id">ID {{ s.id }}</span> — {{ s.name }}
                    </div>
                    {% endfor %}
                </div>
                
                <div class="form-group">
                    <label>🔢 ID ученика</label>
                    <input type="number" id="studentId" placeholder="Например: 1" value="1">
                </div>
                
                <div class="form-group">
                    <label>📅 Тип периода</label>
                    <select id="periodType">
                        <option value="year">📆 Учебный год</option>
                        <option value="quarter">📚 Четверть</option>
                        <option value="trimester">📖 Триместр</option>
                    </select>
                </div>
                
                <div class="form-group">
                    <label>🔢 Номер периода</label>
                    <input type="number" id="periodNumber" placeholder="Для года, четверти или триместра">
                </div>
                
                <button onclick="generate()">🔗 Создать ссылку</button>
                
                <div id="result" class="result" style="display: none;"></div>
            </div>
        </div>
        
        <div class="footer">
            <p>Certify Service — генерация персонализированных образовательных отчётов</p>
        </div>
        
        <script>
            async function generate() {
                const studentId = document.getElementById('studentId').value;
                const periodType = document.getElementById('periodType').value;
                const periodNumber = document.getElementById('periodNumber').value;
                
                const resultDiv = document.getElementById('result');
                resultDiv.style.display = 'block';
                resultDiv.innerHTML = '⏳ Создание ссылки...';
                resultDiv.style.borderLeftColor = '#38BDF8';
                
                if (!periodType) {
                    resultDiv.innerHTML = `<div style="color: #EF4444; font-weight: bold;">❌ Ошибка:</div> Не указан тип периода`;
                    resultDiv.style.borderLeftColor = '#EF4444';
                    return;
                }
                
                if (!periodNumber || periodNumber.trim() === '') {
                    resultDiv.innerHTML = `<div style="color: #EF4444; font-weight: bold;">❌ Ошибка:</div> Не указан номер периода`;
                    resultDiv.style.borderLeftColor = '#EF4444';
                    return;
                }
                
                const requestBody = {
                    id: parseInt(studentId),
                    period_type: periodType,
                    period_number: parseInt(periodNumber)
                };
                
                try {
                    const response = await fetch('/api/share/generate', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify(requestBody)
                    });
                    
                    const data = await response.json();
                    
                    if (data.status === 'success') {
                        resultDiv.innerHTML = `
                            <div style="color: #10B981; font-weight: bold; margin-bottom: 12px;">✅ Ссылка создана!</div>
                            <div style="margin-bottom: 8px;"><strong>👤 Ученик:</strong> ${data.student_name}</div>
                            <div style="margin-bottom: 12px;"><strong>📅 Период:</strong> ${data.period_name}</div>
                            <div style="margin-bottom: 12px;"><strong>🔗 Ссылка:</strong><br>
                            <a href="${data.share_link}" target="_blank">${data.share_link}</a></div>
                            <button onclick="window.open('${data.share_link}', '_blank')" style="background: #10B981; margin-top: 0; width: auto; padding: 8px 20px;">🎓 Открыть отчёт</button>
                            <button onclick="navigator.clipboard.writeText('${data.share_link}')" style="background: #6B7280; margin-top: 0; width: auto; padding: 8px 20px;">📋 Копировать</button>
                        `;
                        resultDiv.style.borderLeftColor = '#10B981';
                    } else {
                        resultDiv.innerHTML = `<div style="color: #EF4444; font-weight: bold;">❌ Ошибка:</div> ${data.error}`;
                        resultDiv.style.borderLeftColor = '#EF4444';
                    }
                } catch (error) {
                    resultDiv.innerHTML = `<div style="color: #EF4444; font-weight: bold;">❌ Ошибка:</div> ${error.message}`;
                    resultDiv.style.borderLeftColor = '#EF4444';
                }
            }
        </script>
    </body>
    </html>
    ''', students=students)

# Запуск сервера
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    print("\n" + "="*60)
    print(f"СЕРВЕР ЗАПУЩЕН! http://localhost:{port}")
    print(f"Тест: http://localhost:{port}/test")
    print("="*60)
    app.run(host='0.0.0.0', port=port, debug=False)