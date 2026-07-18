import requests

PAGESPEED_API = "https://www.googleapis.com/pagespeedonline/v5/runPagespeed"

def check_pagespeed(url: str, strategy: str = "mobile") -> dict:
    """
    Проверяет скорость страницы через Google PageSpeed Insights API.
    strategy: 'mobile' или 'desktop'
    Возвращает dict с метриками или dict с ошибкой.
    """
    try:
        params = {
            "url": url,
            "strategy": strategy,
            "category": "performance",
        }
        r = requests.get(PAGESPEED_API, params=params, timeout=30)
        data = r.json()

        lhr = data.get("lighthouseResult", {})
        cats = lhr.get("categories", {})
        audits = lhr.get("audits", {})

        score = int((cats.get("performance", {}).get("score", 0) or 0) * 100)

        def metric(key):
            a = audits.get(key, {})
            return a.get("displayValue", "—")

        fcp  = metric("first-contentful-paint")
        lcp  = metric("largest-contentful-paint")
        tbt  = metric("total-blocking-time")
        cls  = metric("cumulative-layout-shift")
        si   = metric("speed-index")
        tti  = metric("interactive")

        opportunities = []
        for key, audit in audits.items():
            if audit.get("details", {}).get("type") == "opportunity":
                savings = audit.get("details", {}).get("overallSavingsMs", 0)
                if savings and savings > 200:
                    opportunities.append({
                        "title": audit.get("title", key),
                        "savings_ms": int(savings),
                    })

        opportunities.sort(key=lambda x: x["savings_ms"], reverse=True)

        return {
            "ok": True,
            "score": score,
            "strategy": strategy,
            "url": url,
            "metrics": {
                "FCP": fcp,
                "LCP": lcp,
                "TBT": tbt,
                "CLS": cls,
                "SI":  si,
                "TTI": tti,
            },
            "opportunities": opportunities[:5],
        }

    except Exception as e:
        return {"ok": False, "error": str(e), "url": url}


def format_pagespeed_report(result: dict) -> str:
    """Форматирует результат в текст для Telegram."""
    if not result.get("ok"):
        return "Зона верификации PageSpeed: " + result.get("error", "неизвестная ошибка")

    score = result["score"]
    strategy_label = "📱 Мобильные" if result["strategy"] == "mobile" else "🖥 Десктоп"

    if score >= 90:
        verdict = "🟢 Отлично"
    elif score >= 50:
        verdict = "🟡 Требует оптимизации"
    else:
        verdict = "🔴 Критически медленно"

    m = result["metrics"]
    lines = [
        f"⚡ PageSpeed: {result['url']}",
        f"{strategy_label} · Оценка: {score}/100 — {verdict}",
        "",
        "📊 Ключевые метрики:",
        f"  FCP (первый контент): {m['FCP']}",
        f"  LCP (главный контент): {m['LCP']}",
        f"  TBT (блокировка): {m['TBT']}",
        f"  CLS (стабильность): {m['CLS']}",
        f"  SI (индекс скорости): {m['SI']}",
        f"  TTI (время отклика): {m['TTI']}",
    ]

    opps = result.get("opportunities", [])
    if opps:
        lines.append("")
        lines.append("🛠 Зоны оптимизации:")
        for o in opps:
            ms = o["savings_ms"]
            lines.append(f"  • {o['title']} (−{ms} мс)")

    lines += [
        "",
        "━━━━━━━━━━━━━━━━━━━━",
        "Нужна помощь с ускорением? Отчёт — 90 ₽",
        "Пишите: @Aleksseopiru",
    ]

    return "\n".join(lines)


def get_pagespeed_instruction() -> dict:
    """Инструкция по исправлению медленной загрузки для mailer."""
    return {
        "problem": "Страница загружается медленно — PageSpeed Score ниже нормы",
        "impact": (
            "Скорость загрузки — прямой фактор ранжирования в Google и Яндексе. "
            "Страница медленнее 3 секунд теряет до 40% мобильных посетителей. "
            "Google снижает позиции медленных сайтов в mobile-first индексации."
        ),
        "code_location": (
            "<!-- Проверьте через PageSpeed Insights: -->\n"
            "<!-- pagespeed.web.dev -->\n"
            "<!-- Введите URL вашего сайта и получите детальный отчёт -->\n"
            "<!-- Основные причины: тяжёлые картинки, неминифицированный CSS/JS, нет кэша -->"
        ),
        "how_to_fix": (
            "Оптимизируйте изображения — конвертируйте в формат WebP\n"
            "Включите GZIP сжатие на сервере\n"
            "Подключите бесплатный CDN Cloudflare (cloudflare.com)\n"
            "Минифицируйте CSS и JS файлы\n"
            "Включите кэширование браузера\n"
            "Цель: PageSpeed Score 80+ на мобильных\n\n"
            "WordPress: плагин WP Rocket или LiteSpeed Cache\n"
            "Tilda: Настройки → Оптимизация → Сжатие\n"
            "Bitrix: Настройки → Производительность → Кэширование\n"
            "Для всех: подключите Cloudflare как CDN"
        ),
        "result": (
            "Ускорение сайта до 2-3 секунд загрузки даёт рост позиций "
            "на 5-15% и снижение показателя отказов на 20-30%."
        ),
        "metrics": ["+5-15% позиций", "Снижение отказов на 20%", "PageSpeed 80+"],
    }
