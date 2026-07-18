import aiosmtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import os

SMTP_HOST = "smtp.yandex.ru"
SMTP_PORT = 465
SMTP_EMAIL = os.getenv("SMTP_EMAIL", "filiusx33@yandex.ru")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
ADMIN_EMAIL = "filiusx33@yandex.ru"

async def send_report(to_email: str, url: str, check_name: str, instruction: dict) -> bool:
    html = """<!DOCTYPE html>
<html><head><meta charset="utf-8">
<style>
body{font-family:Arial,sans-serif;max-width:600px;margin:0 auto;padding:20px;color:#333}
.h{background:#1a73e8;color:white;padding:24px;border-radius:12px 12px 0 0}
.h h1{margin:0;font-size:20px}
.h p{margin:6px 0 0;opacity:.85;font-size:13px}
.s{background:white;padding:20px;border:1px solid #eee;margin-top:-1px}
.s h2{color:#1a73e8;font-size:15px;margin-top:0;border-bottom:2px solid #e8f0fe;padding-bottom:8px}
.hl{background:#e8f5e9;border-left:4px solid #34a853;padding:12px 16px;border-radius:4px;margin:12px 0}
.steps{background:#f8f9fa;padding:16px;border-radius:8px;white-space:pre-wrap;font-size:14px;line-height:1.6}
.result{background:#e3f2fd;border:1px solid #1a73e8;padding:16px;border-radius:8px;margin:12px 0}
.footer{background:#f8f9fa;padding:16px;border-radius:0 0 12px 12px;text-align:center;font-size:12px;color:#666;border:1px solid #eee;margin-top:-1px}
</style></head><body>
<div class="h">
<h1>SEO-отчёт: """ + check_name + """</h1>
<p>Сайт: """ + url + """</p>
</div>
<div class="s">
<h2>Выявленная зона роста</h2>
<p>""" + instruction.get("problem", "") + """</p>
</div>
<div class="s">
<h2>Почему это важно</h2>
<div class="hl">""" + instruction.get("impact", "") + """</div>
</div>
<div class="s">
<h2>Пошаговая инструкция по исправлению</h2>
<div class="steps">""" + instruction.get("how_to_fix", "").replace("\n", "<br>") + """</div>
</div>
<div class="s">
<h2>Что даст исправление</h2>
<div class="result">""" + instruction.get("result", "") + """</div>
</div>
<div class="s">
<h2>Нужна помощь с исправлением?</h2>
<p>Напишите в Telegram: <a href="https://t.me/Aleksseopiru" style="color:#1a73e8;">@Aleksseopiru</a></p>
<p>Сайт: <a href="https://seopi.ru" style="color:#1a73e8;">seopi.ru</a></p>
</div>
<div class="footer">
<p><strong>Александр Филимонов</strong> — SEO-эксперт | seopi.ru</p>
<p>Самозанятый, НПД. Чек через «Мой налог». Без НДС.</p>
<p style="color:#aaa">Обработка персональных данных по 152-ФЗ</p>
</div>
</body></html>"""

    msg = MIMEMultipart("alternative")
    msg["Subject"] = "SEO-отчёт: " + check_name + " | " + url
    msg["From"] = "Александр SEO <" + SMTP_EMAIL + ">"
    msg["To"] = to_email
    msg.attach(MIMEText(html, "html", "utf-8"))

    try:
        await aiosmtplib.send(
            msg,
            hostname=SMTP_HOST,
            port=SMTP_PORT,
            use_tls=True,
            username=SMTP_EMAIL,
            password=SMTP_PASSWORD,
        )
        # Копия администратору
        msg2 = MIMEMultipart("alternative")
        msg2["Subject"] = "[Копия] Отчёт отправлен: " + to_email + " | " + check_name
        msg2["From"] = "Александр SEO <" + SMTP_EMAIL + ">"
        msg2["To"] = ADMIN_EMAIL
        body2 = "<p><b>Клиент:</b> " + to_email + "</p><p><b>Сайт:</b> " + url + "</p><p><b>Проблема:</b> " + check_name + "</p>"
        msg2.attach(MIMEText(body2, "html", "utf-8"))
        await aiosmtplib.send(
            msg2,
            hostname=SMTP_HOST,
            port=SMTP_PORT,
            use_tls=True,
            username=SMTP_EMAIL,
            password=SMTP_PASSWORD,
        )
        return True
    except Exception as e:
        print("Email error: " + str(e))
        return False
