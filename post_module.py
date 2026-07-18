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

ARTICLE_CSS = """<style>
:root{
  --primary:#0f172a;--accent:#2563eb;--accent-h:#1d4ed8;
  --green:#10b981;--tg:#229ED9;--tg-h:#1a86b8;
  --amber:#f59e0b;--red:#ef4444;
  --bg:#ffffff;--bg-soft:#f8fafc;--bg-blue:#eff6ff;
  --text:#334155;--muted:#64748b;--border:#e2e8f0;
  --r:14px;--r-sm:8px;
}
*{box-sizing:border-box;margin:0;padding:0}
html{scroll-behavior:smooth}
body{font-family:system-ui,-apple-system,sans-serif;background:var(--bg);color:var(--text);font-size:17px;line-height:1.75;-webkit-text-size-adjust:100%}
a{color:var(--accent);text-decoration:none;transition:.2s}
a:hover{color:var(--accent-h);text-decoration:underline}
img{max-width:100%;height:auto;display:block}
.aw{max-width:820px;margin:0 auto;padding:48px 20px 64px}
h1{font-size:clamp(26px,5vw,40px);font-weight:800;color:var(--primary);line-height:1.15;letter-spacing:-.02em;margin-bottom:18px}
h2{font-size:clamp(20px,4vw,28px);font-weight:800;color:var(--primary);line-height:1.2;margin:52px 0 18px;padding-bottom:10px;border-bottom:2px solid var(--border)}
h3{font-size:18px;font-weight:700;color:var(--accent);margin:28px 0 10px}
p{color:var(--muted);margin-bottom:18px;max-width:68ch;line-height:1.8}
.lead{font-size:19px;color:var(--text);line-height:1.7;margin-bottom:28px;max-width:72ch}
strong{color:var(--primary);font-weight:600}
.bc{font-size:13px;color:var(--muted);margin-bottom:20px;display:flex;flex-wrap:wrap;gap:6px;align-items:center}
.bc a{color:var(--accent)}
.bc span{opacity:.5}
.badges{display:flex;flex-wrap:wrap;gap:8px;margin:16px 0 28px}
.badge{background:var(--bg-soft);border:1px solid var(--border);border-radius:20px;padding:5px 13px;font-size:13px;color:var(--muted);font-weight:500;white-space:nowrap}
.toc{background:var(--bg-soft);border:1px solid var(--border);border-radius:var(--r);padding:18px 22px;margin:28px 0}
.toc-h{font-weight:700;color:var(--primary);font-size:15px;margin-bottom:10px}
.toc ol{margin:0;padding-left:18px}
.toc li{margin-bottom:6px;font-size:14px;color:var(--muted)}
.toc a{color:var(--accent)}
.grid{display:grid;gap:16px;grid-template-columns:repeat(auto-fit,minmax(240px,1fr));margin:20px 0}
.card{background:#fff;border:1px solid var(--border);border-radius:var(--r);padding:22px 20px;transition:box-shadow .25s,border-color .25s,transform .25s}
.card:hover{box-shadow:0 8px 24px rgba(0,0,0,.09);border-color:var(--accent);transform:translateY(-3px)}
.card-icon{font-size:28px;margin-bottom:10px}
.card-title{font-weight:700;color:var(--primary);font-size:16px;margin-bottom:8px}
.card p{font-size:14px;margin:0}
.card-blue{background:linear-gradient(135deg,#eff6ff,#dbeafe);border-color:#bfdbfe}
.card-green{background:linear-gradient(135deg,#f0fdf4,#dcfce7);border-color:#bbf7d0}
.card-amber{background:linear-gradient(135deg,#fffbeb,#fef3c7);border-color:#fde68a}
.card-purple{background:linear-gradient(135deg,#faf5ff,#ede9fe);border-color:#ddd6fe}
.cl{list-style:none;padding:0;margin:14px 0}
.cl li{padding:6px 0 6px 30px;position:relative;font-size:15px;color:var(--muted);line-height:1.6}
.cl li+li{border-top:1px solid var(--border)}
.cl li.ok::before{content:"✅";position:absolute;left:0}
.cl li.no::before{content:"❌";position:absolute;left:0}
.cl li.tip::before{content:"💡";position:absolute;left:0}
.cl li.arr::before{content:"→";position:absolute;left:0;color:var(--accent);font-weight:700}
table{width:100%;border-collapse:collapse;margin:20px 0;font-size:15px;border-radius:var(--r);overflow:hidden;border:1px solid var(--border)}
th{background:var(--bg-soft);font-weight:700;color:var(--primary);padding:12px 16px;text-align:left;border-bottom:2px solid var(--border)}
td{padding:11px 16px;border-bottom:1px solid var(--border);color:var(--muted)}
tr:last-child td{border-bottom:none}
tr:nth-child(even){background:var(--bg-soft)}
.box{padding:18px 20px;border-radius:var(--r);margin:20px 0;border-left:4px solid var(--accent);background:var(--bg-blue)}
.box.ok{background:#f0fdf4;border-color:var(--green)}
.box.warn{background:#fffbeb;border-color:var(--amber)}
.box.err{background:#fef2f2;border-color:var(--red)}
.box-title{font-weight:700;color:var(--primary);margin-bottom:6px;font-size:15px}
.box p{margin:0;font-size:15px}
.cta{background:linear-gradient(135deg,var(--tg) 0%,var(--tg-h) 100%);border-radius:20px;padding:36px 32px;text-align:center;margin:48px 0}
.cta h3{color:#fff;font-size:22px;margin-bottom:10px}
.cta p{color:rgba(255,255,255,.9);margin:0 auto 20px;max-width:560px;font-size:16px}
.btn{display:inline-flex;align-items:center;justify-content:center;padding:14px 28px;border-radius:50px;font-weight:700;font-size:16px;transition:.2s}
.btn-white{background:#fff;color:var(--tg)}
.btn-white:hover{background:#f0f9ff;transform:translateY(-2px);box-shadow:0 6px 20px rgba(0,0,0,.15);text-decoration:none}
.cta-note{font-size:12px;color:rgba(255,255,255,.7);margin-top:12px}
.cta-note a{color:rgba(255,255,255,.9)}
.faq{margin:40px 0}
.faq-item{border:1px solid var(--border);border-radius:var(--r-sm);margin-bottom:10px;overflow:hidden}
.faq-q{padding:16px 20px;font-weight:700;color:var(--primary);font-size:15px;background:var(--bg-soft)}
.faq-a{padding:12px 20px 16px;font-size:15px;color:var(--muted);line-height:1.7}
.author{background:var(--bg-soft);border:1px solid var(--border);border-radius:var(--r);padding:22px;margin:48px 0;display:flex;align-items:center;gap:18px}
.author img{width:68px;height:68px;border-radius:50%;object-fit:cover;border:3px solid #fff;box-shadow:0 2px 8px rgba(0,0,0,.1);flex-shrink:0}
.author-name{font-weight:700;color:var(--primary);font-size:15px;margin-bottom:4px}
.author p{font-size:13px;margin:0}
.related{margin:36px 0}
.related-title{font-size:13px;font-weight:600;color:var(--muted);text-transform:uppercase;letter-spacing:.06em;margin-bottom:12px}
.related-grid{display:flex;flex-wrap:wrap;gap:8px}
.rel-link{display:inline-flex;align-items:center;gap:6px;padding:8px 14px;background:var(--bg-soft);border-radius:20px;border:1px solid var(--border);color:var(--text);font-size:13px;font-weight:500;transition:.2s;white-space:nowrap}
.rel-link::before{content:"→";color:var(--accent);font-size:12px}
.rel-link:hover{background:var(--bg-blue);border-color:var(--accent);color:var(--accent);text-decoration:none;transform:translateY(-1px)}
@media(max-width:480px){.related-grid{flex-direction:column}.rel-link{white-space:normal}}
@media(max-width:768px){
  .aw{padding:20px 16px 48px}
  .grid{grid-template-columns:1fr}
  .author{flex-direction:column;text-align:center}
  table{font-size:13px}
  th,td{padding:9px 12px}
  .cta{padding:24px 18px}
  h2{margin-top:36px}
  .related-grid{grid-template-columns:1fr}
}
</style>"""

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

ИСПОЛЬЗУЙ ТОЛЬКО ЭТИ CSS КЛАССЫ:
- .aw — обёртка статьи (НЕ article-wrap)
- .lead — лид-абзац
- .bc — хлебные крошки (НЕ breadcrumb)
- .badges и .badge — бейджи
- .toc и .toc-h — оглавление
- .grid — сетка карточек
- .card + .card-icon + .card-title — карточки
- .card-blue / .card-green / .card-amber / .card-purple — цветные карточки
- .cl с li.ok / li.no / li.tip / li.arr — чек-листы
- table, th, td — таблицы
- .box / .box.ok / .box.warn / .box.err + .box-title — блоки советов
- .cta с .btn .btn-white — CTA блок
- .cta-note — подпись под CTA
- .faq + .faq-item + .faq-q + .faq-a — аккордеон FAQ
- .author + .author-name — блок автора
- .related + .related-grid + .rel-link — похожие статьи

Структура HTML:
1. Мета-теги (title, description, canonical, og, twitter, robots)
2. Schema.org JSON-LD (Article + FAQPage + BreadcrumbList)
3. <div class="aw">
   - <nav class="bc"> хлебные крошки
   - <h1> заголовок (только ОДИН в начале статьи)
   - <p class="lead"> лид (2-3 предложения)
   - <div class="badges"> бейджи: 📄 Договор НПД / 🛡 152-ФЗ / ✅ Без серых схем / 🤖 Аудит за 30 сек
   - <div class="toc"> оглавление
   - 5-7 разделов H2 с контентом (.card с цветами, table, .cl, .box)
   - <div class="cta"> CTA блок (БЕЗ заголовка H2/H3 перед ним — только сам блок)
   - <div class="faq"> 4 вопроса (НЕ добавлять H2 "Итог" или "Заключение" после FAQ)
   - <div class="related"> компактные ссылки в виде пилюль:
     <div class="related">
       <div class="related-title">Полезные материалы</div>
       <div class="related-grid">
         <a href="URL" class="rel-link">Название статьи</a>
         ... (3-4 ссылки максимум)
       </div>
     </div>

ВАЖНО: НЕ добавлять в конце статьи:
- Большие заголовки H2/H3 типа "Итог", "Заключение", "Вывод", "Резюме"
- Повторный призыв к действию после .cta блока
- Блок .author (автор статьи) — не добавлять совсем
- Дополнительные блоки после .related
Статья заканчивается на блоке .related

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

4. CTA БЛОК — используй класс .cta с кнопкой .btn-white:
   <div class="cta">
     <h3>Проверьте ваш сайт прямо сейчас</h3>
     <p>Бесплатная проверка 15 параметров за 30 секунд. Без регистрации.</p>
     <a href="https://t.me/seopi_seo_bot?start=audit" class="btn btn-white">🤖 Запустить бесплатный аудит</a>
     <p class="cta-note">Исполнитель: Александр Филимонов (Самозанятый, НПД) · 
     <a href="https://seopi.ru/politika-konfidenczialnosti/">152-ФЗ</a></p>
   </div>
   НЕ добавляй текст "Получите бесплатный SEO-аудит вашего сайта" отдельно от CTA блока.

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

ИСПОЛЬЗУЙ СТРОГО ЭТОТ CSS (уже подключён на сайте, не меняй классы):
{ARTICLE_CSS}


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
            article_html = response.choices[0].message.content
            # Если CSS не включён в ответ — добавляем
            if "<style>" not in article_html:
                article_html = ARTICLE_CSS + "\n" + article_html
            return article_html
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
