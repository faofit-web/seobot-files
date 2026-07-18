import aiohttp
import json
import os
import base64

WP_URL = "https://seopi.ru"
WP_USER = "aleks33"
WP_PASS = "AnL1 Jo7E NwWx pX0O yI9n Fb7z"

async def check_duplicate(topic: str) -> dict:
    """Проверяет наличие похожих статей в WordPress."""
    try:
        credentials = base64.b64encode(f"{WP_USER}:{WP_PASS}".encode()).decode()
        headers = {"Authorization": f"Basic {credentials}"}
        
        # Ищем по ключевым словам темы
        search_query = topic[:50]
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{WP_URL}/wp-json/wp/v2/posts",
                headers=headers,
                params={"search": search_query, "per_page": 5, "_fields": "id,title,link,status"},
                timeout=aiohttp.ClientTimeout(total=15)
            ) as resp:
                posts = await resp.json()
                
        if not posts or not isinstance(posts, list):
            return {"duplicate": False, "similar": []}
        
        similar = []
        topic_lower = topic.lower()
        topic_words = set(topic_lower.split())
        
        for post in posts:
            post_title = post.get("title", {}).get("rendered", "").lower()
            post_words = set(post_title.split())
            
            # Точное совпадение
            if topic_lower in post_title or post_title in topic_lower:
                similar.append({
                    "title": post.get("title", {}).get("rendered", ""),
                    "url": post.get("link", ""),
                    "match": "exact"
                })
                continue
            
            # Похожесть — больше 60% общих слов
            if len(topic_words) > 2:
                common = topic_words & post_words
                similarity = len(common) / len(topic_words)
                if similarity >= 0.6:
                    similar.append({
                        "title": post.get("title", {}).get("rendered", ""),
                        "url": post.get("link", ""),
                        "match": f"similar ({int(similarity*100)}%)"
                    })
        
        has_exact = any(s["match"] == "exact" for s in similar)
        return {"duplicate": has_exact, "similar": similar}
        
    except Exception as e:
        return {"duplicate": False, "similar": [], "error": str(e)}



# Карта меню — тема → ID меню и родительского пункта
MENU_MAP = {
    # Блог — основные статьи
    "blog": {
        "keywords": ["seo", "продвижение", "оптимизация", "контент", "семантика", 
                     "ключевые", "трафик", "позиции", "яндекс", "google", "индексация",
                     "ссылки", "аудит", "скорость", "загрузка", "мобильн", "robots",
                     "дубли", "title", "description", "h1", "микроразметка", "canonical"],
        "menu_slug": "blog",
        "label": "Блог"
    },
    # Кейсы
    "cases": {
        "keywords": ["кейс", "результат", "рост", "увеличение", "клиент", 
                     "было стало", "пример", "история", "проект"],
        "menu_slug": "cases", 
        "label": "Кейсы"
    },
    # Инструменты
    "tools": {
        "keywords": ["инструмент", "чек-лист", "шаблон", "калькулятор", "проверка",
                     "анализатор", "сервис", "инструкция", "руководство"],
        "menu_slug": "tools",
        "label": "Блог → Инструменты"
    },
    # SEO для начинающих
    "beginners": {
        "keywords": ["начинающ", "основы", "что такое", "как работает", "первый",
                     "введение", "старт", "базов"],
        "menu_slug": "beginners",
        "label": "Блог → SEO для начинающих"
    },
    # Техническая оптимизация
    "technical": {
        "keywords": ["техническ", "robots.txt", "sitemap", "404", "500", "редирект",
                     "скорость", "core web vitals", "pagespeed", "кэш"],
        "menu_slug": "technical",
        "label": "Услуги → Техническая оптимизация"
    },
}

# WordPress меню ID (получаем динамически)
MENU_LOCATIONS = {
    "blog": 3,      # ID меню Блог
    "cases": 4,     # ID меню Кейсы  
    "tools": 3,     # Подменю Инструменты в Блоге
    "beginners": 3, # Подменю SEO для начинающих
    "technical": 2, # Подменю в Услугах
}

def detect_menu_section(topic: str) -> dict:
    """Определяет в какой раздел меню добавить статью."""
    topic_lower = topic.lower()
    
    best_match = None
    best_score = 0
    
    for section, data in MENU_MAP.items():
        score = sum(1 for kw in data["keywords"] if kw in topic_lower)
        if score > best_score:
            best_score = score
            best_match = section
    
    if not best_match or best_score == 0:
        best_match = "blog"  # По умолчанию в Блог
    
    return {
        "section": best_match,
        "label": MENU_MAP[best_match]["label"],
        "menu_id": MENU_LOCATIONS.get(best_match, 3)
    }

async def get_wp_menus() -> list:
    """Получает список меню из WordPress."""
    try:
        credentials = base64.b64encode(f"{WP_USER}:{WP_PASS}".encode()).decode()
        headers = {"Authorization": f"Basic {credentials}"}
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{WP_URL}/wp-json/wp/v2/menus",
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=15)
            ) as resp:
                if resp.status == 200:
                    return await resp.json()
                return []
    except Exception:
        return []

async def add_to_menu(post_id: int, post_title: str, post_url: str, topic: str) -> dict:
    """Добавляет опубликованную статью в нужный раздел меню."""
    try:
        section_info = detect_menu_section(topic)
        credentials = base64.b64encode(f"{WP_USER}:{WP_PASS}".encode()).decode()
        headers = {
            "Authorization": f"Basic {credentials}",
            "Content-Type": "application/json",
        }
        
        # Пробуем через WP REST API v2 menus
        menu_item_data = {
            "title": post_title,
            "url": post_url,
            "status": "publish",
            "menus": section_info["menu_id"],
            "object": "post",
            "object_id": post_id,
            "type": "post",
        }
        
        async with aiohttp.ClientSession() as session:
            # Создаём пункт меню
            async with session.post(
                f"{WP_URL}/wp-json/wp/v2/menu-items",
                headers=headers,
                json=menu_item_data,
                timeout=aiohttp.ClientTimeout(total=15)
            ) as resp:
                result = await resp.json()
                if resp.status in (200, 201):
                    return {
                        "ok": True,
                        "section": section_info["label"],
                        "menu_item_id": result.get("id"),
                    }
                else:
                    return {
                        "ok": False,
                        "section": section_info["label"],
                        "error": str(result),
                    }
    except Exception as e:
        return {"ok": False, "error": str(e), "section": detect_menu_section(topic)["label"]}

async def set_post_category(post_id: int, topic: str) -> dict:
    """Назначает категорию статье по теме."""
    try:
        # Карта категорий WordPress
        CATEGORY_MAP = {
            "технич": "Техническое SEO",
            "контент": "Контент и тексты", 
            "аудит": "SEO-аудит",
            "кейс": "Кейсы",
            "семантик": "Семантика",
            "аналитик": "Аналитика",
            "скорост": "Скорость сайта",
            "мобильн": "Мобильное SEO",
            "local": "Локальное SEO",
            "магазин": "SEO для магазинов",
        }
        
        topic_lower = topic.lower()
        category_name = "SEO"  # По умолчанию
        
        for keyword, cat in CATEGORY_MAP.items():
            if keyword in topic_lower:
                category_name = cat
                break
        
        credentials = base64.b64encode(f"{WP_USER}:{WP_PASS}".encode()).decode()
        headers = {
            "Authorization": f"Basic {credentials}",
            "Content-Type": "application/json",
        }
        
        async with aiohttp.ClientSession() as session:
            # Ищем категорию
            async with session.get(
                f"{WP_URL}/wp-json/wp/v2/categories",
                headers=headers,
                params={"search": category_name, "per_page": 3},
                timeout=aiohttp.ClientTimeout(total=10)
            ) as resp:
                cats = await resp.json()
            
            cat_id = None
            if cats and isinstance(cats, list):
                cat_id = cats[0].get("id")
            
            # Если категории нет — создаём
            if not cat_id:
                async with session.post(
                    f"{WP_URL}/wp-json/wp/v2/categories",
                    headers=headers,
                    json={"name": category_name},
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as resp:
                    new_cat = await resp.json()
                    cat_id = new_cat.get("id")
            
            # Назначаем категорию посту
            if cat_id:
                async with session.post(
                    f"{WP_URL}/wp-json/wp/v2/posts/{post_id}",
                    headers=headers,
                    json={"categories": [cat_id]},
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as resp:
                    if resp.status == 200:
                        return {"ok": True, "category": category_name, "cat_id": cat_id}
            
            return {"ok": False, "error": "Category not set"}
    except Exception as e:
        return {"ok": False, "error": str(e)}

async def setup_post_seo(post_id: int, topic: str, content: str) -> dict:
    """Настраивает SEO мета-данные поста через Yoast SEO."""
    try:
        import re
        
        # Извлекаем мета из HTML контента
        title_match = re.search(r'<title>(.*?)</title>', content, re.DOTALL)
        desc_match = re.search(r'<meta name="description" content="(.*?)"', content)
        
        seo_title = title_match.group(1).strip() if title_match else topic
        seo_desc = desc_match.group(1).strip() if desc_match else ""
        
        credentials = base64.b64encode(f"{WP_USER}:{WP_PASS}".encode()).decode()
        headers = {
            "Authorization": f"Basic {credentials}",
            "Content-Type": "application/json",
        }
        
        # Обновляем Yoast SEO мета через кастомные поля
        yoast_data = {
            "meta": {
                "_yoast_wpseo_title": seo_title,
                "_yoast_wpseo_metadesc": seo_desc,
                "_yoast_wpseo_focuskw": topic,
            }
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{WP_URL}/wp-json/wp/v2/posts/{post_id}",
                headers=headers,
                json=yoast_data,
                timeout=aiohttp.ClientTimeout(total=10)
            ) as resp:
                if resp.status == 200:
                    return {"ok": True, "title": seo_title, "desc": seo_desc[:80] + "..."}
                return {"ok": False}
    except Exception as e:
        return {"ok": False, "error": str(e)}

ARTICLE_TYPES = {
    "weekly": "LSI-статья (экспертность, поведенческие факторы)",
    "biweekly": "Кейс или технический регламент (время на сайте)",
    "monthly": "Pillar Content (фундаментальная статья, E-E-A-T)",
}

SYSTEM_PROMPT = """Ты — профессиональный SEO-копирайтер. Пишешь статьи для блога seopi.ru.

АВТОР: Александр Филимонов, SEO-эксперт, Санкт-Петербург, самозанятый (НПД).
АУДИТОРИЯ: Предприниматели РФ, малый бизнес, маркетологи.
СТИЛЬ: Деловой, конкретный, с цифрами и чек-листами. Без воды.

ЗАПРЕЩЁННЫЕ СЛОВА: ошибка, нарушение, проблема, штраф, провал.
ЗАМЕНЫ: зона роста, расхождение, точка оптимизации, этап верификации.

ВНУТРЕННИЕ ССЫЛКИ (использовать 3-5 релевантных):
/besplatnyj-seo-audit/ /tehnicheskaya-seo-optimizacziya/
/semantika-i-klyuchevye-slova/ /analitika-i-metriki/
/ux-yuzabiliti/ /kejsy/ /prajs-list/ /konsultaciya/
/roi-seo-pochemu-eto-dolgaya-no-nadyozhnaya-investicziya/
/avtomatizacziya-sistem/ /vyyavlenie-slabyh-mest/

CTA: всегда добавляй блок со ссылкой https://t.me/seopi_seo_bot?start=audit

ФОРМАТ ВЫВОДА: чистый HTML без DOCTYPE и html/body тегов.
Структура:
1. Мета-теги (title, description, canonical, og, twitter, schema.org)
2. <style> блок (копируй стили из примера)
3. <article class="article-content"> с полным контентом
4. H1 → лид → оглавление → 5-7 H2 разделов → FAQ (4 вопроса) → CTA → автор

ДЛИНА: 2500-3500 слов.

ОБЯЗАТЕЛЬНЫЕ ТРЕБОВАНИЯ К КАЖДОЙ СТАТЬЕ:

1. ПРАКТИЧЕСКИЙ ИНСТРУМЕНТ — в каждой статье должен быть один из:
   - Чек-лист (минимум 7 пунктов с ✅/❌)
   - Шаблон ТЗ или таблица сравнения
   - Калькулятор или формула расчёта (например, ROI, CPL)
   Оформить в блок .card с заголовком и списком.

2. ЗАПРЕЩЁННЫЕ СЛОВА и их замены:
   - «ошибка» → «точка роста» или «зона оптимизации»
   - «проблема» → «расхождение» или «зона верификации»
   - «нарушение» → «несоответствие» или «этап корректировки»
   - «провал» → «зона для доработки»
   - «штраф» → «санкция поисковика»
   ПРОВЕРЬ текст перед выводом и замени все запрещённые слова.

3. УНИКАЛЬНОСТЬ — пиши оригинальный текст, не копируй формулировки из других статей.
   Используй реальные цифры, кейсы из российского SEO-рынка 2025-2026.

4. ФОРМА ОБРАТНОЙ СВЯЗИ (152-ФЗ) — в CTA блоке обязательно добавь:
   <p style="font-size:0.85rem;color:#64748b;margin-top:12px;">
   Нажимая кнопку, вы соглашаетесь с 
   <a href="https://seopi.ru/politika-konfidenczialnosti/">политикой обработки персональных данных (152-ФЗ)</a>.
   Исполнитель: Александр Филимонов, самозанятый (НПД), ИНН 463403817128.
   </p>

5. ВНУТРЕННЯЯ ПЕРЕЛИНКОВКА — обязательно включи ссылки на коммерческие страницы:
   - https://seopi.ru/prajs-list/ — страница цен (анкор: «стоимость SEO-аудита», «цены на продвижение»)
   - https://seopi.ru/konsultaciya/ — консультация (анкор: «бесплатная консультация», «получить разбор сайта»)
   - Дополнительно 2-3 ссылки из банка внутренних ссылок (релевантные теме)
   
СООТВЕТСТВИЕ 152-ФЗ: в формах сбора заявок обязательно упоминай согласие на обработку ПД."""

async def generate_article(topic: str, article_type: str = "weekly") -> str:
    """Генерирует SEO-статью через GigaChat."""
    from gigachat import GigaChat
    from gigachat.models import Chat, Messages, MessagesRole
    
    gigachat_key = os.getenv("GIGACHAT_KEY", "")
    
    type_label = ARTICLE_TYPES.get(article_type, ARTICLE_TYPES["weekly"])
    
    user_prompt = f"""Напиши SEO-статью для блога seopi.ru.

ТЕМА: {topic}
ТИП: {type_label}
URL СТАТЬИ: https://seopi.ru/{topic.lower().replace(' ', '-').replace('/', '-')}/

Требования:
1. Title 50-65 символов с ключевым словом
2. Description 120-155 символов с призывом
3. Schema.org: Article + FAQPage + BreadcrumbList
4. H1 отличается от Title
5. Оглавление с якорными ссылками
6. Таблицы сравнения где уместно
7. Чек-листы с ✅ и ❌
8. Блоки .tip-box с советами эксперта
9. 4 FAQ вопроса в конце
10. CTA блок с кнопкой в Telegram-бот
11. Блок автора с фото

Верни ТОЛЬКО HTML код без пояснений."""

    try:
        with GigaChat(credentials=gigachat_key, verify_ssl_certs=False) as giga:
            response = giga.chat(Chat(
                messages=[
                    Messages(role=MessagesRole.SYSTEM, content=SYSTEM_PROMPT),
                    Messages(role=MessagesRole.USER, content=user_prompt)
                ],
                max_tokens=8000
            ))
            return response.choices[0].message.content
    except Exception as e:
        return f"Зона верификации генерации: {str(e)}"

async def publish_to_wordpress(title: str, content: str, status: str = "draft") -> dict:
    """Публикует статью в WordPress через REST API."""
    try:
        credentials = base64.b64encode(f"{WP_USER}:{WP_PASS}".encode()).decode()
        headers = {
            "Authorization": f"Basic {credentials}",
            "Content-Type": "application/json",
        }
        data = {
            "title": title,
            "content": content,
            "status": status,
            "categories": [],
            "tags": [],
            "meta": {
                "description": "",
            }
        }
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{WP_URL}/wp-json/wp/v2/posts",
                headers=headers,
                json=data,
                timeout=aiohttp.ClientTimeout(total=30)
            ) as resp:
                result = await resp.json()
                if resp.status in (200, 201):
                    return {
                        "ok": True,
                        "id": result.get("id"),
                        "url": result.get("link"),
                        "status": result.get("status"),
                    }
                else:
                    return {"ok": False, "error": str(result)}
    except Exception as e:
        return {"ok": False, "error": str(e)}
