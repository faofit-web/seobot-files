import aiosmtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import os
from datetime import datetime

SMTP_HOST = "smtp.yandex.ru"
SMTP_PORT = 465
SMTP_EMAIL = os.getenv("SMTP_EMAIL", "filiusx33@yandex.ru")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
ADMIN_EMAIL = "filiusx33@yandex.ru"

async def send_report(to_email: str, url: str, check_name: str, instruction: dict, price: int = 0) -> bool:
    date_str = datetime.now().strftime("%d.%m.%Y %H:%M")

    html = """<!DOCTYPE html>
<html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width">
<style>
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:Arial,sans-serif;background:#f4f6f9;color:#333;padding:20px}
.wrap{max-width:640px;margin:0 auto;background:white;border-radius:16px;overflow:hidden;box-shadow:0 4px 20px rgba(0,0,0,.1)}
.header{background:linear-gradient(135deg,#1a73e8,#0d47a1);color:white;padding:28px 24px}
.header h1{font-size:22px;margin-bottom:8px}
.header .meta{opacity:.85;font-size:13px;line-height:1.8}
.header .meta span{display:inline-block;margin-right:16px}
.badge{display:inline-block;background:rgba(255,255,255,.2);padding:3px 10px;border-radius:20px;font-size:12px;margin-top:8px}
.section{padding:20px 24px;border-bottom:1px solid #f0f0f0}
.section:last-child{border-bottom:none}
.section h2{font-size:15px;color:#1a73e8;margin-bottom:12px;display:flex;align-items:center;gap:8px}
.section h2::before{content:'';display:inline-block;width:4px;height:18px;background:#1a73e8;border-radius:2px}
.highlight{background:#fff8e1;border-left:4px solid #ffc107;padding:12px 16px;border-radius:4px;font-size:14px;line-height:1.6}
.impact{background:#e8f5e9;border-left:4px solid #34a853;padding:12px 16px;border-radius:4px;font-size:14px;line-height:1.6}
.code-block{background:#263238;color:#aed581;padding:16px;border-radius:8px;font-family:monospace;font-size:13px;line-height:1.8;overflow-x:auto;white-space:pre-wrap;margin:12px 0}
.steps{counter-reset:steps}
.step{display:flex;gap:12px;margin:10px 0;align-items:flex-start}
.step-num{background:#1a73e8;color:white;width:24px;height:24px;border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:12px;font-weight:700;flex-shrink:0;margin-top:1px}
.step-text{font-size:14px;line-height:1.6;flex:1}
.result-box{background:#e3f2fd;border:1px solid #1a73e8;padding:16px;border-radius:8px;font-size:14px;line-height:1.6}
.result-box .metric{display:inline-block;background:#1a73e8;color:white;padding:2px 10px;border-radius:12px;font-size:12px;font-weight:700;margin:4px 2px}
.price-box{background:#f3e5f5;border:1px solid #9c27b0;padding:16px 24px;display:flex;justify-content:space-between;align-items:center}
.price-box .label{font-size:14px;color:#666}
.price-box .amount{font-size:24px;font-weight:700;color:#9c27b0}
.cta{background:#1a73e8;color:white;padding:20px 24px;text-align:center}
.cta a{color:white;text-decoration:none;font-weight:700;font-size:16px}
.cta p{font-size:13px;opacity:.85;margin-top:6px}
.footer{background:#f8f9fa;padding:16px 24px;text-align:center;font-size:12px;color:#888;line-height:1.8}
</style></head><body>
<div class="wrap">

<div class="header">
  <h1>SEO-отчёт: """ + check_name + """</h1>
  <div class="meta">
    <span>🌐 Сайт: <strong>""" + url + """</strong></span><br>
    <span>📅 Дата: """ + date_str + """</span>
    <span>📧 Получатель: """ + to_email + """</span>
  </div>
  <div class="badge">Исполнитель: Александр Филимонов · Самозанятый, НПД</div>
</div>

<div class="section">
  <h2>Выявленная зона роста</h2>
  <div class="highlight">
    <strong>""" + instruction.get("problem", "") + """</strong>
  </div>
</div>

<div class="section">
  <h2>Почему это важно для вашего сайта</h2>
  <div class="impact">""" + instruction.get("impact", "") + """</div>
</div>

<div class="section">
  <h2>Где найти в коде сайта</h2>
  <p style="font-size:14px;margin-bottom:10px;">Откройте исходный код страницы <strong>""" + url + """</strong> (Ctrl+U в браузере) и найдите:</p>
  <div class="code-block">""" + instruction.get("code_location", "<!-- Смотрите в разделе <head> страницы -->") + """</div>
</div>

<div class="section">
  <h2>Пошаговая инструкция по исправлению</h2>
  <div class="steps">""" + "".join([
    '<div class="step"><div class="step-num">' + str(i+1) + '</div><div class="step-text">' + step.strip() + '</div></div>'
    for i, step in enumerate([s for s in instruction.get("how_to_fix", "").split("\n") if s.strip()])
  ]) + """</div>
</div>

<div class="section">
  <h2>Что улучшится после исправления</h2>
  <div class="result-box">
    """ + instruction.get("result", "") + """<br><br>
    """ + "".join(['<span class="metric">' + m + '</span>' for m in instruction.get("metrics", [])]) + """
  </div>
</div>

<div class="price-box">
  <div>
    <div class="label">Стоимость данного отчёта</div>
    <div style="font-size:12px;color:#999;margin-top:4px">Чек выдаётся через «Мой налог» · Без НДС</div>
  </div>
  <div class="amount">""" + str(price) + """ ₽</div>
</div>

<div class="cta">
  <a href="https://t.me/Aleksseopiru">💬 Написать Александру в Telegram</a>
  <p>Помогу внедрить исправление или отвечу на вопросы</p>
</div>

<div class="footer">
  <strong>Александр Филимонов</strong> — SEO-эксперт · <a href="https://seopi.ru" style="color:#1a73e8">seopi.ru</a><br>
  Самозанятый, НПД · ИНН: по запросу · Чек через «Мой налог»<br>
  Персональные данные обрабатываются в соответствии с 152-ФЗ<br>
  <span style="color:#bbb">© """ + str(datetime.now().year) + """ Александр Филимонов</span>
</div>

</div>
</body></html>"""

    msg = MIMEMultipart("alternative")
    msg["Subject"] = "SEO-отчёт: " + check_name + " | " + url
    msg["From"] = SMTP_EMAIL
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
        msg2["Subject"] = "[Копия] SEO-отчёт: " + check_name + " | " + to_email
        msg2["From"] = SMTP_EMAIL
        msg2["To"] = ADMIN_EMAIL
        body2 = (
            "<p><b>Клиент:</b> " + to_email + "</p>"
            "<p><b>Сайт:</b> " + url + "</p>"
            "<p><b>Проблема:</b> " + check_name + "</p>"
            "<p><b>Сумма:</b> " + str(price) + " ₽</p>"
            "<p><b>Дата:</b> " + date_str + "</p>"
        )
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
