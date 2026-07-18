import aiohttp
import json
import os
import base64

WP_URL = "https://seopi.ru"
WP_USER = "aleks33"
WP_PASS = "AnL1 Jo7E NwWx pX0O yI9n Fb7z"

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
