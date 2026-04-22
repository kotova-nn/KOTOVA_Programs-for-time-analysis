# ===================================================================================================================
#                                                Импорт библиотек
# ===================================================================================================================

from PIL import Image, ImageDraw, ImageFont
import os
import re
from datetime import datetime
import platform
import csv


# ===================================================================================================================
#                                                Класс генератора отчётов
# ===================================================================================================================

class ReportGenerator:
    """
    Основной класс для генерации PNG и PDF отчётов.
    
    Поддерживает два типа отчётов:
        - Начальная школа (1-4 класс): игровой отчёт «Путь динозаврика Дино»
        - Старшая школа (5-11 класс): аналитический дашборд с титулами по дням недели
    """
    
    def __init__(self):
        """Инициализация: создание папок, загрузка шрифтов, настройка путей."""
        self.template_dir = 'templates/'
        self.output_dir = 'share_cache/'
        self.cache_paths = {}
        
        # Создаём папки, если их нет
        os.makedirs(self.template_dir, exist_ok=True)
        os.makedirs(self.output_dir, exist_ok=True)
        
        # Загружаем шрифты
        self._load_fonts()
        
        # Путь к файлу датасета (нужен для чтения favorite_day, но фактически не используется)
        self.dataset_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'students.csv')
    
    
    # ===============================================================================================================
    #                                                Работа со шрифтами
    # ===============================================================================================================
    
    def _get_font_path(self):
        """
        Определяет путь к системному шрифту в зависимости от операционной системы.
        
        Windows: C:/Windows/Fonts/arial.ttf
        Linux: /usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf
        macOS: /System/Library/Fonts/Arial.ttf
        
        Returns:
            str: путь к шрифту или None, если шрифт не найден
        """
        system = platform.system()
        if system == "Windows":
            return "C:/Windows/Fonts/arial.ttf"
        elif system == "Linux":
            possible_paths = [
                "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
                "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            ]
            for path in possible_paths:
                if os.path.exists(path):
                    return path
            return None
        elif system == "Darwin":  # macOS
            return "/System/Library/Fonts/Arial.ttf"
        else:
            return None
    
    def _load_fonts(self):
        """
        Загружает шрифты разных размеров.
        
        Если системный шрифт не найден, использует стандартный шрифт Pillow (менее красивый).
        Размеры шрифтов:
            - font_large (56px) - для больших цифр (минуты)
            - font_medium (32px) - для класса и года
            - font_title (48px) - для имени ученика
            - font_desc (28px) - для описаний локаций и слоганов
            - font_small (24px) - для подписей под рамками
            - font_tiny (18px) - для очень длинных текстов (запасной)
            - font_boss (36px) - для титулов в оранжевой рамке
            - font_footer (16px) - для подвала "До встречи! Твой Цифриум"
        """
        font_path = self._get_font_path()
        
        if font_path and os.path.exists(font_path):
            # Загружаем красивые системные шрифты
            self.font_large = ImageFont.truetype(font_path, 56)
            self.font_medium = ImageFont.truetype(font_path, 32)
            self.font_title = ImageFont.truetype(font_path, 48)
            self.font_desc = ImageFont.truetype(font_path, 28)
            self.font_small = ImageFont.truetype(font_path, 24)
            self.font_tiny = ImageFont.truetype(font_path, 18)
            self.font_boss = ImageFont.truetype(font_path, 36)
            self.font_footer = ImageFont.truetype(font_path, 16)
            print(f"Шрифт загружен: {font_path}")
        else:
            # Fallback: стандартный шрифт Pillow
            self.font_large = ImageFont.load_default()
            self.font_medium = ImageFont.load_default()
            self.font_title = ImageFont.load_default()
            self.font_desc = ImageFont.load_default()
            self.font_small = ImageFont.load_default()
            self.font_tiny = ImageFont.load_default()
            self.font_boss = ImageFont.load_default()
            self.font_footer = ImageFont.load_default()
            print("Шрифт не найден, используется стандартный")
    
    
    # ===============================================================================================================
    #                                                Функции отрисовки текста
    # ===============================================================================================================
    
    def draw_text_centered(self, draw, text, rect, font, fill):
        """
        Рисует текст по центру прямоугольника.
        
        Особенности:
            - Текст выравнивается по центру как по горизонтали, так и по вертикали
            - Если текст не помещается по ширине, автоматически уменьшает размер шрифта
            - Минимальный размер шрифта — 8px
        
        Параметры:
            draw: объект ImageDraw
            text: текст для отрисовки
            rect: кортеж (x1, y1, x2, y2) — границы прямоугольника
            font: начальный шрифт
            fill: цвет текста (HEX или название, например "#EF4444")
        """
        x1, y1, x2, y2 = rect
        cx = (x1 + x2) // 2  # центр по X
        cy = (y1 + y2) // 2  # центр по Y
        
        # Проверяем, помещается ли текст по ширине
        bbox = draw.textbbox((0, 0), text, font=font)
        tw = bbox[2] - bbox[0]
        max_w = (x2 - x1) - 40  # оставляем отступы по 20px с каждой стороны
        
        current_font = font
        if tw > max_w:
            # Уменьшаем шрифт с шагом 2px, пока текст не поместится
            for sz in range(56, 8, -2):
                try:
                    font_path = self._get_font_path()
                    if font_path:
                        smaller_font = ImageFont.truetype(font_path, sz)
                    else:
                        smaller_font = ImageFont.load_default()
                except:
                    smaller_font = ImageFont.load_default()
                bb = draw.textbbox((0, 0), text, font=smaller_font)
                if bb[2] - bb[0] <= max_w:
                    current_font = smaller_font
                    break
        
        draw.text((cx, cy), text, fill=fill, font=current_font, anchor='mm')
    
    def draw_text_in_rect(self, draw, text, rect, initial_font, fill, line_spacing=5, fill_color=None, outline_color=None, outline_width=3):
        """
        Рисует текст внутри прямоугольника с автоматическим переносом строк.
        
        Особенности:
            - Разбивает длинный текст на строки по словам
            - Если текст не помещается по высоте, уменьшает размер шрифта
            - Может заливать прямоугольник цветом и рисовать обводку
        
        Параметры:
            draw: объект ImageDraw
            text: текст для отрисовки
            rect: кортеж (x1, y1, x2, y2) — границы прямоугольника
            initial_font: начальный шрифт
            fill: цвет текста
            line_spacing: межстрочный интервал (пикселей)
            fill_color: цвет заливки фона (опционально)
            outline_color: цвет обводки (опционально)
            outline_width: толщина обводки
        """
        x1, y1, x2, y2 = rect
        rect_width = x2 - x1
        rect_height = y2 - y1
        
        # Рисуем заливку и обводку, если они указаны
        if fill_color:
            draw.rectangle(rect, fill=fill_color)
        if outline_color:
            draw.rectangle(rect, outline=outline_color, width=outline_width)
        
        # Разбиваем текст на строки по словам
        words = text.split()
        lines = []
        current_line = []
        
        for word in words:
            test_line = ' '.join(current_line + [word])
            bbox = draw.textbbox((0, 0), test_line, font=initial_font)
            if bbox[2] - bbox[0] <= rect_width - 20:
                current_line.append(word)
            else:
                if current_line:
                    lines.append(' '.join(current_line))
                current_line = [word]
        if current_line:
            lines.append(' '.join(current_line))
        
        if not lines:
            lines = [text]
        
        # Подбираем размер шрифта, чтобы текст поместился по высоте
        temp_font = initial_font
        font_size = initial_font.size if hasattr(initial_font, 'size') else 36
        
        for sz in range(font_size, 8, -2):
            try:
                font_path = self._get_font_path()
                if font_path:
                    test_font = ImageFont.truetype(font_path, sz)
                else:
                    test_font = ImageFont.load_default()
            except:
                test_font = ImageFont.load_default()
            
            total_height = 0
            line_heights = []
            max_line_width = 0
            
            for line in lines:
                bbox = draw.textbbox((0, 0), line, font=test_font)
                line_width = bbox[2] - bbox[0]
                line_height = bbox[3] - bbox[1]
                line_heights.append(line_height)
                total_height += line_height + line_spacing
                if line_width > max_line_width:
                    max_line_width = line_width
            
            total_height -= line_spacing
            
            if total_height <= rect_height and max_line_width <= rect_width - 20:
                temp_font = test_font
                break
        
        # Вычисляем начальную Y-координату для вертикального центрирования
        total_height = 0
        line_heights = []
        for line in lines:
            bbox = draw.textbbox((0, 0), line, font=temp_font)
            line_height = bbox[3] - bbox[1]
            line_heights.append(line_height)
            total_height += line_height + line_spacing
        total_height -= line_spacing
        
        current_y = y1 + (rect_height - total_height) // 2
        
        # Рисуем каждую строку
        for i, line in enumerate(lines):
            bbox = draw.textbbox((0, 0), line, font=temp_font)
            line_width = bbox[2] - bbox[0]
            x = x1 + (rect_width - line_width) // 2
            draw.text((x, current_y), line, fill=fill, font=temp_font)
            current_y += line_heights[i] + line_spacing
        
        return current_y
    
    def draw_wrapped_text(self, draw, text, start_x, start_y, max_width, font, fill, line_spacing=10):
        """
        Рисует текст с переносом строк, НО НЕ меняет размер шрифта.
        
        Используется для описаний локаций в начальной школе, где текст уже помещается
        по ширине, но может быть длинным.
        
        Параметры:
            draw: объект ImageDraw
            text: текст для отрисовки
            start_x: начальная X координата
            start_y: начальная Y координата
            max_width: максимальная ширина строки
            font: шрифт (фиксированного размера)
            fill: цвет текста
            line_spacing: межстрочный интервал
        """
        if not text:
            return start_y
        
        # Разбиваем текст на строки по словам
        words = text.split()
        lines = []
        current_line = []
        
        for word in words:
            test_line = ' '.join(current_line + [word])
            bbox = draw.textbbox((0, 0), test_line, font=font)
            if bbox[2] <= max_width:
                current_line.append(word)
            else:
                if current_line:
                    lines.append(' '.join(current_line))
                current_line = [word]
        if current_line:
            lines.append(' '.join(current_line))
        
        # Рисуем каждую строку
        current_y = start_y
        for line in lines:
            draw.text((start_x, current_y), line, fill=fill, font=font)
            bbox = draw.textbbox((0, 0), line, font=font)
            current_y += bbox[3] + line_spacing
        
        return current_y
    
    
    # ===============================================================================================================
    #                                                Расчёт уровня (для начальной школы)
    # ===============================================================================================================
    
    def calculate_level(self, student_data):
        """
        Рассчитывает уровень ученика (1, 2 или 3) для начальной школы.
        
        Формула расчёта XP:
            XP = (процент задач × 40) + (процент баллов × 40) + (бонус за дни × 10) + (бонус за минуты × 10)
        
        Бонус за дни и минуты:
            - Рассчитывается как процент от целевых значений (зависят от класса и периода)
            - Максимум 10 баллов за дни и 10 баллов за минуты
        
        Дополнительные условия для уровней:
            - Для уровня 3: XP ≥ 66% И дни ≥ порога И минуты ≥ порога
            - Для уровня 2: XP ≥ 33% И дни ≥ порога И минуты ≥ порога
        
        Пороги зависят от периода (год / триместр):
            - Год: уровень 2 → 10 дней / 150 мин, уровень 3 → 25 дней / 400 мин
            - Триместр: уровень 2 → 4 дня / 50 мин, уровень 3 → 9 дней / 140 мин
        
        Returns:
            tuple: (level, total_xp) где level — 1, 2 или 3, total_xp — 0-100
        """
        grade = student_data['grade']
        period_type = student_data['period_type']
        
        # Коэффициент периода: год = 1.0, триместр = 0.33
        if period_type == 'trimester':
            period_coef = 0.33
        else:
            period_coef = 1.0
        
        # Проценты успеваемости
        task_percent = student_data['wk_solved_task_count'] / student_data['wk_max_task_count'] if student_data['wk_max_task_count'] > 0 else 0
        score_percent = student_data['wk_points'] / student_data['wk_max_points'] if student_data['wk_max_points'] > 0 else 0
        total_events = student_data['total_events']
        total_minutes = student_data['total_minutes']
        
        # Базовые целевые значения для 1 класса
        base_events = 20
        base_minutes = 300
        
        # Бонус за класс: чем старше класс, тем выше требования
        grade_bonus = (grade - 1) * 10
        grade_bonus_minutes = (grade - 1) * 100
        
        # Целевые значения с учётом класса и периода
        events_target = (base_events + grade_bonus) * period_coef
        minutes_target = (base_minutes + grade_bonus_minutes) * period_coef
        
        # XP за успеваемость (80% веса)
        academic_xp = (task_percent * 40 + score_percent * 40)
        
        # XP за активность (20% веса)
        events_xp = min(total_events / events_target, 1) * 20 if events_target > 0 else 0
        minutes_xp = min(total_minutes / minutes_target, 1) * 20 if minutes_target > 0 else 0
        
        activity_xp = events_xp + minutes_xp
        total_xp = min(academic_xp + activity_xp, 100)
        
        # Пороги для уровней (зависят только от периода, не от класса!)
        if period_coef == 0.33:
            level2_events, level2_minutes = 4, 50
            level3_events, level3_minutes = 9, 140
        else:
            level2_events, level2_minutes = 10, 150
            level3_events, level3_minutes = 25, 400
        
        # Проверка на уровень 3 (нужно XP ≥ 66% и выполнение обоих условий)
        can_be_level3 = False
        if total_xp >= 66:
            conditions_met = 0
            if total_events >= level3_events:
                conditions_met += 1
            if total_minutes >= level3_minutes:
                conditions_met += 1
            if conditions_met >= 2:
                can_be_level3 = True
        
        # Проверка на уровень 2 (нужно XP ≥ 33% и выполнение обоих условий)
        can_be_level2 = False
        if total_xp >= 33:
            conditions_met = 0
            if total_events >= level2_events:
                conditions_met += 1
            if total_minutes >= level2_minutes:
                conditions_met += 1
            if conditions_met >= 2:
                can_be_level2 = True
        
        # Определяем итоговый уровень
        if can_be_level3:
            level = 3
        elif can_be_level2:
            level = 2
        else:
            level = 1
        
        return level, total_xp
    
    
    # ===============================================================================================================
    #                                                Пути к шаблонам
    # ===============================================================================================================
    
    def get_background_path(self, grade, level):
        """
        Возвращает путь к шаблону для начальной школы.
        
        Формат имени: templates/grade{grade}_level{level}.png
        Пример: templates/grade1_level1.png, templates/grade4_level3.png
        """
        return os.path.join(self.template_dir, f'grade{grade}_level{level}.png')
    
    def get_senior_background_path(self):
        """
        Возвращает путь к единому шаблону для старшей школы.
        
        Формат имени: templates/senior_base.png
        """
        return os.path.join(self.template_dir, 'senior_base.png')
    
    
    # ===============================================================================================================
    #                                                Тексты для локаций и титулов
    # ===============================================================================================================
    
    def get_location_info(self, grade, level):
        """
        Возвращает название и описание локации для начальной школы.
        
        Локации по классам и уровням:
            1 класс: Опушка → Тропинка → Полянка
            2 класс: Ручей → Болото → Пещера
            3 класс: Барханы → Пирамиды → Оазис в пустыне
            4 класс: Предгорье → Перевал → Вершина
        
        Returns:
            dict: {'name': 'Название локации', 'description': 'Описание локации'}
        """
        locations = {
            1: {
                1: {'name': 'Опушка', 'description': 'Ты только начинаешь свой путь! Здесь ты познакомишься с основами и сделаешь первые шаги к большим открытиям.'},
                2: {'name': 'Тропинка', 'description': 'Ты уже на верном пути! Продолжай двигаться вперёд, и скоро ты достигнешь новых высот.'},
                3: {'name': 'Полянка', 'description': 'Ты добрался до уютной полянки знаний! Здесь тебя ждут интересные открытия и новые друзья.'}
            },
            2: {
                1: {'name': 'Ручей', 'description': 'Ты у ручья знаний! Вода здесь чистая и прозрачная, как твои мысли. Продолжай в том же духе!'},
                2: {'name': 'Болото', 'description': 'Ты прошёл через болото сомнений и не сдался! Теперь ты знаешь, что трудности делают тебя сильнее.'},
                3: {'name': 'Пещера', 'description': 'Ты добрался до таинственной пещеры! Здесь спрятаны древние знания. Открой их и стань мудрее!'}
            },
            3: {
                1: {'name': 'Барханы', 'description': 'Ты идёшь по барханам знаний. Пусть песок времени заметает твои ошибки, а впереди ждёт оазис успеха!'},
                2: {'name': 'Пирамиды', 'description': 'Ты у подножия великих пирамид! Древняя мудрость ждёт тебя. Поднимись на вершину и увидишь новые горизонты.'},
                3: {'name': 'Оазис в пустыне', 'description': 'Ты нашёл оазис в пустыне знаний! Это место силы и вдохновения. Отдохни и продолжай своё удивительное путешествие!'}
            },
            4: {
                1: {'name': 'Предгорье', 'description': 'Ты у подножия горы знаний. Впереди — захватывающее восхождение к вершинам мастерства!'},
                2: {'name': 'Перевал', 'description': 'Ты преодолел перевал сложностей! Позади остались трудности, впереди — новые горизонты и великие открытия.'},
                3: {'name': 'Вершина', 'description': 'Ты достиг вершины! Поздравляем! Ты покорил гору знаний. Теперь перед тобой открываются бескрайние возможности.'}
            }
        }
        # Прямое обращение без fallback — если данных нет, будет ошибка KeyError
        return locations[grade][level]
    
    def format_number_display(self, value, max_value):
        """
        Форматирует число для отображения в рамке.
        
        Правила:
            - Если число целое: "15 из 50"
            - Если число дробное: "25%" (округляется до целого)
        
        Примеры:
            - 15, 50 → "15 из 50"
            - 12.5, 50 → "25%"
        """
        if value == int(value):
            return f"{int(value)} из {int(max_value)}"
        else:
            percent = (value / max_value * 100) if max_value > 0 else 0
            return f"{round(percent)}%"
    
    
    # ===============================================================================================================
    #                                                Генерация отчётов (главный метод)
    # ===============================================================================================================
    
    def generate_report(self, student_data, age_group='senior', period_name=''):
        """
        Главный метод генерации отчёта.
        
        Выбирает тип отчёта в зависимости от возрастной группы:
            - 'primary' → начальная школа (1-4 класс)
            - 'senior' → старшая школа (5-11 класс)
        
        Параметры:
            student_data (dict): словарь с данными ученика (из БД)
            age_group (str): 'primary' или 'senior'
            period_name (str): название периода (например, "2026 учебный год")
        
        Returns:
            tuple: (путь_к_PNG, путь_к_PDF)
        """
        if age_group == 'primary':
            return self._generate_primary_report(student_data, period_name)
        else:
            return self._generate_senior_report(student_data, period_name)
    
    
    # ===============================================================================================================
    #                                                Отчёт для старшей школы
    # ===============================================================================================================
    
    def _generate_senior_report(self, student_data, period_name):
        """
        Генерирует отчёт для старшей школы (5-11 класс).
        
        Структура отчёта:
            1. Имя и класс ученика вверху по центру
            2. Три рамки с цифрами: минуты, текущий балл, решённые задачи
            3. Подписи под рамками: "МИНУТ", "текущий балл", "решено задач"
            4. Оранжевая рамка с титулом (по дню недели или по типу активности)
            5. Рамка со слоганом (мотивирующий текст)
            6. Футер "До встречи! Твой Цифриум" в левом нижнем углу
        
        Титулы для одного активного дня:
            - Понедельник → «Энерджайзер»: "Задаёшь тон неделе. Заряжаешься с понедельника."
            - Вторник/Среда → «Дзен-мастер»: "Середина недели — твоя зона комфорта. Работаешь без стресса."
            - Четверг → «Финишный ускоритель»: "Разгоняешься к концу недели. Главные дела — в четверг."
            - Пятница → «Финальный босс»: "В пятницу становишься легендой. Побеждаешь главные вызовы недели."
            - Суббота/Воскресенье → «Уикенд-воин»: "Выходные — твоя боевая готовность. Главные битвы в субботу/воскресенье."
        
        Титулы для нескольких активных дней (из колонки activity_type):
            - Король будней → «Король будней»: "Ты в тонусе в учебные дни. Ритм недели — твоя суперсила!"
            - Гибкий поток → «Гибкий поток»: "Учишься когда захочешь. График не властен над тобой!"
        """
        try:
            # Извлекаем все обязательные поля из данных ученика
            user_id = student_data['user_id']
            last_name = student_data['last_name']
            first_name = student_data['first_name']
            grade = student_data['grade']
            period_type = student_data['period_type']
            wk_solved_task_count = float(student_data['wk_solved_task_count'])
            wk_max_task_count = float(student_data['wk_max_task_count'])
            wk_points = float(student_data['wk_points'])
            wk_max_points = float(student_data['wk_max_points'])
            total_minutes = int(student_data['total_minutes'])
            favorite_day = student_data['favorite_day']
            activity_type = student_data['activity_type']
        except KeyError as e:
            # Если какого-то поля нет — это ошибка в данных
            raise ValueError(f"Отсутствует обязательное поле в данных ученика: {e}")
        except (ValueError, TypeError) as e:
            raise ValueError(f"Неверный формат данных: {e}")
        
        # Формируем полное имя ученика
        if last_name and first_name:
            student_full_name = f"{first_name} {last_name}"
        else:
            student_full_name = f"Ученик {user_id}"
        
        # Форматируем цифры для отображения в рамках
        tasks_display = self.format_number_display(wk_solved_task_count, wk_max_task_count)
        score_display = self.format_number_display(wk_points, wk_max_points)
        time_display = str(total_minutes)  # просто число, без "мин" (подпись под рамкой)
        
        grade_text = f"{grade} класс"
        year_text = period_name.replace(f"{grade_text} • ", "") if period_name else "2025-2026"
        
        # Словарь слоганов для разных типов активности (при нескольких днях)
        activity_slogans = {
            'Король будней': 'Ты в тонусе в учебные дни. Ритм недели — твоя суперсила!',
            'Гибкий поток': 'Учишься когда захочешь. График не властен над тобой!'
        }
        
        # Определяем титул и слоган в зависимости от количества активных дней
        if ',' in str(favorite_day):
            # Несколько активных дней — используем activity_type
            boss_title = f"«{activity_type}»"
            slogan = activity_slogans[activity_type]
        else:
            # Один активный день — используем day_type_map
            day_type_map = {
                'Понедельник': ('Энерджайзер', 'Задаёшь тон неделе. Заряжаешься с понедельника.'),
                'Вторник': ('Дзен-мастер', 'Середина недели — твоя зона комфорта. Работаешь без стресса.'),
                'Среда': ('Дзен-мастер', 'Середина недели — твоя зона комфорта. Работаешь без стресса.'),
                'Четверг': ('Финишный ускоритель', 'Разгоняешься к концу недели. Главные дела — в четверг.'),
                'Пятница': ('Финальный босс', 'В пятницу становишься легендой. Побеждаешь главные вызовы недели.'),
                'Суббота': ('Уикенд-воин', 'Выходные — твоя боевая готовность. Главные битвы в субботу.'),
                'Воскресенье': ('Уикенд-воин', 'Выходные — твоя боевая готовность. Главные битвы в воскресенье.')
            }
            boss_title, slogan = day_type_map[favorite_day]
            boss_title = f"«{boss_title}»"
        
        # Загружаем единый фоновый шаблон для старшей школы
        template_path = self.get_senior_background_path()
        
        if os.path.exists(template_path):
            background = Image.open(template_path).resize((1200, 1700))
            img = background.copy()
        else:
            # Если шаблон не найден, создаём чёрный фон
            img = Image.new('RGB', (1200, 1700), color='#0F172A')
            print(f"Предупреждение: не найден шаблон {template_path}")
        
        draw = ImageDraw.Draw(img)
        W, H = img.size
        
        # Цвета
        color_red = "#EF4444"      # красный для текста
        color_orange = "#F97316"   # оранжевый для рамок
        color_white = "#FFFFFF"    # белый для текста в оранжевой рамке
        fill_orange = "#F97316"    # оранжевая заливка для рамки с титулом
        
        # 1. Рисуем имя ученика (по центру вверху)
        self.draw_text_centered(draw, student_full_name, (0, 140, W, 220), self.font_title, color_red)
        
        # 2. Рисуем класс и год (под именем)
        self.draw_text_centered(draw, f"{grade_text} • {year_text}", (0, 230, W, 290), self.font_medium, color_red)
        
        # 3. Три рамки с цифрами
        center_rect = (450, 360, 750, 540)   # центральная рамка (минуты)
        left_rect = (120, 430, 350, 570)     # левая рамка (баллы)
        right_rect = (850, 430, 1080, 570)   # правая рамка (задачи)
        
        draw.rectangle(center_rect, outline=color_orange, width=3)
        draw.rectangle(left_rect, outline=color_orange, width=3)
        draw.rectangle(right_rect, outline=color_orange, width=3)
        
        self.draw_text_centered(draw, time_display, center_rect, self.font_large, color_red)
        self.draw_text_centered(draw, score_display, left_rect, self.font_medium, color_red)
        self.draw_text_centered(draw, tasks_display, right_rect, self.font_medium, color_red)
        
        # 4. Подписи под рамками
        label_center_y = 570
        label_left_y = 600
        label_right_y = 600
        
        self.draw_text_centered(draw, "МИНУТ", (center_rect[0], label_center_y, center_rect[2], label_center_y + 30), self.font_small, color_red)
        self.draw_text_centered(draw, "ты провел c", (center_rect[0], label_center_y + 35, center_rect[2], label_center_y + 65), self.font_small, color_red)
        self.draw_text_centered(draw, "Цифриум", (center_rect[0], label_center_y + 70, center_rect[2], label_center_y + 100), self.font_small, color_red)
        
        self.draw_text_centered(draw, "текущий балл", (left_rect[0], label_left_y, left_rect[2], label_left_y + 40), self.font_small, color_red)
        self.draw_text_centered(draw, "решено задач", (right_rect[0], label_right_y, right_rect[2], label_right_y + 40), self.font_small, color_red)
        
        # 5. Оранжевая рамка с титулом
        boss_rect = (350, 680, 950, 780)
        self.draw_text_in_rect(draw, boss_title, boss_rect, self.font_boss, color_white, 5, fill_orange, color_orange, 3)
        
        # 6. Рамка со слоганом
        slogan_rect = (180, 760, 1050, 890)
        draw.rectangle(slogan_rect, outline=color_orange, width=3)
        
        # Разбиваем длинный слоган на строки, если нужно
        slogan_lines = []
        if len(slogan) > 60:
            words = slogan.split()
            line1 = ' '.join(words[:len(words)//2])
            line2 = ' '.join(words[len(words)//2:])
            slogan_lines = [line1, line2]
        else:
            slogan_lines = [slogan]
        
        slogan_text = '\n'.join(slogan_lines)
        self.draw_text_in_rect(draw, slogan_text, slogan_rect, self.font_desc, color_red, 8)
        
        # 7. Футер "До встречи! Твой Цифриум"
        footer_text = "До встречи! Твой Цифриум"
        footer_font = self.font_footer
        footer_color = "#EF4444"
        
        bbox = draw.textbbox((0, 0), footer_text, font=footer_font)
        footer_width = bbox[2] - bbox[0]
        
        footer_x = 200
        footer_y = H - 160
        draw.text((footer_x, footer_y), footer_text, fill=footer_color, font=footer_font)
        
        # 8. Сохраняем PNG и PDF
        png_path = os.path.join(self.output_dir, f"report_{user_id}.png")
        img.save(png_path)
        pdf_path = png_path.replace('.png', '.pdf')
        img.convert('RGB').save(pdf_path)
        
        return png_path, pdf_path
    
    
    # ===============================================================================================================
    #                                                Отчёт для начальной школы
    # ===============================================================================================================
    
    def _generate_primary_report(self, student_data, period_name):
        """
        Генерирует отчёт для начальной школы (1-4 класс).
        
        Структура отчёта:
            1. Имя и класс ученика вверху по центру
            2. Три рамки с цифрами: минуты, текущий балл, решённые задачи
            3. Подписи под рамками: "МИНУТ", "текущий балл", "решено задач"
            4. Рамка с локацией (название)
            5. Описание локации
            6. Футер "До встречи! Твой Цифриум" по центру внизу
        
        Локация определяется на основе XP и дополнительных условий.
        """
        try:
            # Извлекаем все обязательные поля из данных ученика
            user_id = student_data['user_id']
            last_name = student_data['last_name']
            first_name = student_data['first_name']
            grade = student_data['grade']
            period_type = student_data['period_type']
            wk_solved_task_count = float(student_data['wk_solved_task_count'])
            wk_max_task_count = float(student_data['wk_max_task_count'])
            wk_points = float(student_data['wk_points'])
            wk_max_points = float(student_data['wk_max_points'])
            total_minutes = int(student_data['total_minutes'])
        except KeyError as e:
            raise ValueError(f"Отсутствует обязательное поле в данных ученика: {e}")
        except (ValueError, TypeError) as e:
            raise ValueError(f"Неверный формат данных: {e}")
        
        # Рассчитываем уровень и получаем XP
        level, total_xp = self.calculate_level(student_data)
        
        # Загружаем шаблон для соответствующего класса и уровня
        background_path = self.get_background_path(grade, level)
        location_info = self.get_location_info(grade, level)
        
        # Формируем полное имя ученика
        if last_name and first_name:
            student_full_name = f"{first_name} {last_name}"
        else:
            student_full_name = f"Ученик {user_id}"
        
        # Форматируем цифры для отображения в рамках
        tasks_display = self.format_number_display(wk_solved_task_count, wk_max_task_count)
        score_display = self.format_number_display(wk_points, wk_max_points)
        time_display = str(total_minutes)
        
        grade_text = f"{grade} класс"
        year_text = period_name.replace(f"{grade_text} • ", "") if period_name else "2025-2026"
        
        color_red = "#EF4444"
        color_orange = "#F97316"
        
        # Загружаем фоновый шаблон
        if os.path.exists(background_path):
            background = Image.open(background_path).resize((1200, 1700))
            img = background.copy()
        else:
            img = Image.new('RGB', (1200, 1700), color='#0F172A')
            print(f"Предупреждение: не найден шаблон {background_path}")
        
        draw = ImageDraw.Draw(img)
        W, H = img.size
        
        # 1. Рисуем имя ученика (по центру вверху)
        self.draw_text_centered(draw, student_full_name, (0, 40, W, 120), self.font_title, color_red)
        
        # 2. Рисуем класс и год (под именем)
        self.draw_text_centered(draw, f"{grade_text} • {year_text}", (0, 130, W, 190), self.font_medium, color_red)
        
        # 3. Три рамки с цифрами
        center_rect = (450, 260, 750, 440)
        left_rect = (120, 330, 350, 470)
        right_rect = (850, 330, 1080, 470)
        
        draw.rectangle(center_rect, outline=color_orange, width=3)
        draw.rectangle(left_rect, outline=color_orange, width=3)
        draw.rectangle(right_rect, outline=color_orange, width=3)
        
        self.draw_text_centered(draw, time_display, center_rect, self.font_large, color_red)
        self.draw_text_centered(draw, score_display, left_rect, self.font_medium, color_red)
        self.draw_text_centered(draw, tasks_display, right_rect, self.font_medium, color_red)
        
        # 4. Подписи под рамками
        label_center_y = 470
        label_left_y = 500
        label_right_y = 500
        
        self.draw_text_centered(draw, "МИНУТ", (center_rect[0], label_center_y, center_rect[2], label_center_y + 30), self.font_small, color_red)
        self.draw_text_centered(draw, "ты провел c", (center_rect[0], label_center_y + 35, center_rect[2], label_center_y + 65), self.font_small, color_red)
        self.draw_text_centered(draw, "Цифриум", (center_rect[0], label_center_y + 70, center_rect[2], label_center_y + 100), self.font_small, color_red)
        
        self.draw_text_centered(draw, "текущий балл", (left_rect[0], label_left_y, left_rect[2], label_left_y + 40), self.font_small, color_red)
        self.draw_text_centered(draw, "решено задач", (right_rect[0], label_right_y, right_rect[2], label_right_y + 40), self.font_small, color_red)
        
        # 5. Рамка с локацией
        location_rect = (120, 600, 1080, 850)
        draw.rectangle(location_rect, outline=color_orange, width=3)
        
        # Заголовок локации (в верхней части рамки)
        location_text = f"Твоя локация: {location_info['name']}"
        title_rect = (location_rect[0], location_rect[1], location_rect[2], location_rect[1] + 60)
        self.draw_text_in_rect(draw, location_text, title_rect, self.font_medium, color_red, 5)
        
        # Фраза о достижении локации (для годового отчёта)
        if period_type == 'year':
            year_phrase = f'В этом году Дино добрался до локации "{location_info["name"]}"!'
            self.draw_text_centered(draw, year_phrase, (location_rect[0], location_rect[1] + 70, location_rect[2], location_rect[1] + 110), self.font_small, color_red)
            description_y = location_rect[1] + 125
        else:
            description_y = location_rect[1] + 70
        
        # 6. Описание локации
        self.draw_wrapped_text(draw, location_info['description'], location_rect[0] + 30, description_y, location_rect[2] - location_rect[0] - 60, self.font_desc, color_red, 12)
        
        # 7. Футер "До встречи! Твой Цифриум" (по центру внизу)
        footer_text = "До встречи! Твой Цифриум"
        footer_font = self.font_footer
        footer_color = "#EF4444"
        
        bbox = draw.textbbox((0, 0), footer_text, font=footer_font)
        footer_width = bbox[2] - bbox[0]
        
        footer_x = (W - footer_width) // 2
        footer_y = H - 60
        draw.text((footer_x, footer_y), footer_text, fill=footer_color, font=footer_font)
        
        # 8. Сохраняем PNG и PDF
        png_path = os.path.join(self.output_dir, f"report_{user_id}.png")
        img.save(png_path)
        pdf_path = png_path.replace('.png', '.pdf')
        img.convert('RGB').save(pdf_path)
        
        return png_path, pdf_path