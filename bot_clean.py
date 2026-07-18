import asyncio
import os
import uuid
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, types
from aiogram.filters import CommandStart, Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from gigachat import GigaChat

load_dotenv("/home/seobot/.env")
BOT_TOKEN = os.getenv("BOT_TOKEN")
GIGACHAT_KEY = os.getenv("GIGACHAT_KEY")
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
audit_data = {}

def load_prompt():
    with open("/home/seobot/seo/core.md", "r", encoding="utf-8") as f:
        return f.read()

async def ask_gigachat(system, user_text):
    try:
        from gigachat.models import Chat, Messages, MessagesRole
        with GigaChat(credentials=GIGACHAT_KEY, verify_ssl_certs=False) as giga:
            r = giga.chat(Chat(messages=[
                Messages(role=MessagesRole.SYSTEM, content=system),
                Messages(role=MessagesRole.USER, content=user_text)
            ], max_tokens=4000))
            return r.choices[0].message.content
    except Exception as e:
        return "Зона верификации: " + str(e)

async def send_long(message, text):
    for chunk in [text[i:i+4000] for i in range(0, len(text), 4000)]:
        await message.answer(chunk)
        await asyncio.sleep(0.3)

@dp.message(CommandStart())
async def cmd_start(message: types.Message):
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    args = message.text.split()
    # Если пришёл с сайта через ?start=audit
    if len(args) > 1 and args[1] == "audit":
        audit_data["waiting_url_" + str(message.from_user.id)] = True
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✅ Проверить страницу — бесплатно", callback_data="hint_page")],
            [InlineKeyboardButton(text="🌐 Весь сайт — 4 900 ₽", callback_data="hint_site")],
        ])
        await message.answer(
            "👋 Привет! Я SEO-бот Александра Филимонова.\n\n"
            "🔍 Проверю ваш сайт по 15 параметрам и покажу что мешает получать клиентов из поиска.\n\n"
            "Выберите тариф:\n"
            "✅ Проверка страницы — бесплатно\n"
            "🌐 Весь сайт (до 50 стр.) — 4 900 ₽\n"
            "🛠 Детальный отчёт по проблеме — 90 ₽\n\n"
            "Введите адрес вашего сайта:",
            reply_markup=kb
        )
        return
    # Обычный старт — для Александра (полное меню)
    if str(message.from_user.id) == "8335951518":
        await message.answer(
            "Система Seo активирована.\n\n"
            "Команды:\n"
            "/lending — продающая страница\n"
            "/statya — SEO-статья\n"
            "/audit — SEO-аудит сайта\n"
            "/semantika — семантика\n"
            "/otchet — отчёт было/стало\n"
            "/new — сбросить контекст\n\n"
            "Или напишите задачу свободным текстом."
        )
    else:
        # Для клиентов — только аудит
        await message.answer(
            "👋 Привет! Я SEO-бот Александра Филимонова.\n\n"
            "🔍 Проверю ваш сайт по 15 параметрам за 30 секунд и покажу что мешает получать клиентов из поиска.\n\n"
            "Тарифы:\n"
            "📄 Одна страница — 490 ₽\n"
            "🌐 Весь сайт (до 50 стр.) — 4 900 ₽\n"
            "🛠 Отчёт по одной проблеме — 100-300 ₽\n\n"
            "Напишите /audit чтобы начать проверку.\n\n"
            "По всем вопросам: @Aleksseopiru"
        )

@dp.callback_query(lambda c: c.data and c.data.startswith("hint_"))
async def audit_hint(call: types.CallbackQuery):
    await call.answer()
    await call.message.answer(
        "Введите адрес вашего сайта в чат\n"
        "Например: https://seopi.ru"
    )
    audit_data["waiting_url_" + str(call.from_user.id)] = True

@dp.message(Command("new"))
async def cmd_new(message: types.Message):
    await message.answer("Контекст очищен.")

@dp.message(Command("lending"))
async def cmd_lending(message: types.Message):
    await message.answer("Обрабатываю...")
    await send_long(message, await ask_gigachat(load_prompt() + "\nЗАДАЧА: Продающая страница.", "Жду тему."))

@dp.message(Command("statya"))
async def cmd_statya(message: types.Message):
    await message.answer("Обрабатываю...")
    await send_long(message, await ask_gigachat(load_prompt() + "\nЗАДАЧА: SEO-статья.", "Жду ключ."))

@dp.message(Command("semantika"))
async def cmd_semantika(message: types.Message):
    await message.answer("Обрабатываю...")
    await send_long(message, await ask_gigachat(load_prompt() + "\nЗАДАЧА: Семантика.", "Жду тему."))

@dp.message(Command("otchet"))
async def cmd_otchet(message: types.Message):
    await message.answer("Обрабатываю...")
    await send_long(message, await ask_gigachat(load_prompt() + "\nЗАДАЧА: Отчёт было/стало.", "Жду данные."))

@dp.message(Command("audit"))
async def cmd_audit(message: types.Message):
    args = message.text.split()
    if len(args) < 2 or args[1] != "2244":
        await message.answer(
            "Формат: /audit 2244\n\n"
            "Тарифы:\n"
            "✅ Проверка страницы — бесплатно\n"
            "🌐 Весь сайт до 50 стр. — 4 900 ₽\n"
            "🛠 Отчёт по проблеме — 90 ₽"
        )
        return
    # Если URL уже передан в команде
    if len(args) >= 3:
        url = args[2]
        if not url.startswith("http"):
            url = "https://" + url
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✅ Проверить страницу — бесплатно", callback_data="ap|" + url)],
            [InlineKeyboardButton(text="🌐 Весь сайт — 4 900 ₽", callback_data="as|" + url)],
        ])
        await message.answer("🔍 Что проверяем на " + url + "?", reply_markup=kb)
    else:
        # Спросить адрес сайта
        audit_data["waiting_url_" + str(message.from_user.id)] = True
        await message.answer(
            "🔍 Введите адрес сайта для аудита\n\n"
            "Например: https://seopi.ru\n\n"
            "Тарифы:\n"
            "📄 Одна страница — 490 ₽\n"
            "🌐 Весь сайт до 50 стр. — 4 900 ₽"
        )

@dp.callback_query(lambda c: c.data and (c.data.startswith("ap|") or c.data.startswith("as|")))
async def audit_start(call: types.CallbackQuery):
    url = call.data[3:]
    await call.answer()
    await call.message.answer("⏳ Проверяю " + url + "... Подождите 30-60 секунд.")
    from audit_v2 import audit_page
    result = audit_page(url)
    score = result["score"]
    total = result["total"]
    pct = round(score / total * 100) if total > 0 else 0
    if pct >= 80:
        verdict = "🟢 Хорошо"
    elif pct >= 60:
        verdict = "🟡 Требует доработки"
    else:
        verdict = "🔴 Критические зоны роста"
    uid = str(call.from_user.id)
    audit_data["res_" + uid] = {"url": url, "result": result}
    await call.message.answer(
        "🔍 SEO-аудит: " + url + "\n"
        "📊 Оценка: " + str(score) + "/" + str(total) + " (" + str(pct) + "%) " + verdict + "\n"
        "📦 Размер: " + str(result["size_kb"]) + " КБ\n\n"
        "Нажмите на пункт для подробностей:"
    )
    buttons = [
        [InlineKeyboardButton(
            text=("✅ " if c["ok"] else "❌ ") + c["name"],
            callback_data="ai|" + uid + "|" + c["name"]
        )]
        for c in result["checks"]
    ]
    await call.message.answer("📋 Список проверок:", reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))

@dp.callback_query(lambda c: c.data and c.data.startswith("ai|"))
async def audit_item(call: types.CallbackQuery):
    parts = call.data.split("|", 2)
    uid = parts[1]
    check_name = parts[2]
    await call.answer()
    key = "res_" + uid
    if key not in audit_data:
        await call.message.answer("Данные не найдены. Запустите /audit снова.")
        return
    result = audit_data[key]["result"]
    check = next((c for c in result["checks"] if c["name"] == check_name), None)
    if not check:
        return
    if check["ok"]:
        await call.message.answer("✅ " + check_name + "\n\nЭтот параметр в норме. Действий не требуется.")
        return
    price = check["price"]
    from audit_v2 import get_instruction
    instr = get_instruction(check_name)
    text = (
        "❌ " + check_name + "\n\n"
        "📌 Проблема: " + instr["problem"] + "\n\n"
        "📈 Почему важно:\n" + instr["impact"] + "\n\n"
        "💡 Что даст исправление:\n" + instr["result"] + "\n\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "Хотите пошаговую инструкцию по исправлению?\n"
        "Стоимость: 90 ₽ — пошаговый отчёт придёт на вашу почту."
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="🛠 Получить инструкцию — 90 ₽",
            callback_data="pay|" + uid + "|" + check_name + "|" + str(price)
        )],
        [InlineKeyboardButton(text="◀️ Назад к списку", callback_data="bk|" + uid)],
    ])
    await call.message.answer(text, reply_markup=kb)

@dp.callback_query(lambda c: c.data and c.data.startswith("pay|"))
async def audit_pay(call: types.CallbackQuery):
    parts = call.data.split("|")
    uid = parts[1]
    check_name = parts[2]
    price = parts[3]
    await call.answer()
    audit_data["pending_" + uid] = {"check_name": check_name, "price": int(price)}
    await call.message.answer(
        "📧 Введите ваш email\n\n"
        "После оплаты " + price + " ₽ пошаговая инструкция придёт автоматически на вашу почту."
    )

@dp.callback_query(lambda c: c.data and c.data.startswith("bk|"))
async def audit_back(call: types.CallbackQuery):
    uid = call.data[3:]
    await call.answer()
    key = "res_" + uid
    if key not in audit_data:
        await call.message.answer("Запустите /audit снова.")
        return
    buttons = [
        [InlineKeyboardButton(
            text=("✅ " if c["ok"] else "❌ ") + c["name"],
            callback_data="ai|" + uid + "|" + c["name"]
        )]
        for c in audit_data[key]["result"]["checks"]
    ]
    await call.message.answer("📋 Список проверок:", reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))


@dp.message(Command("speed"))
async def cmd_speed(message: types.Message):
    args = message.text.split()
    if len(args) < 2:
        audit_data["waiting_speed_" + str(message.from_user.id)] = True
        await message.answer(
            "⚡ Проверка скорости PageSpeed\n\n"
            "Введите адрес сайта:"
        )
        return
    url = args[1]
    if not url.startswith("http"):
        url = "https://" + url
    await message.answer("⏳ Проверяю скорость " + url + "...\nПодождите 30-60 секунд.")
    from pagespeed_funcs import check_pagespeed, format_pagespeed_report
    result = check_pagespeed(url, "mobile")
    await send_long(message, format_pagespeed_report(result))
    result_d = check_pagespeed(url, "desktop")
    await send_long(message, format_pagespeed_report(result_d))

@dp.message()
async def free_text(message: types.Message):
    uid = str(message.from_user.id)
    # Ожидание URL для аудита
    # Ожидание URL для проверки скорости
    skey = "waiting_speed_" + uid
    if skey in audit_data:
        del audit_data[skey]
        url = message.text.strip()
        if not url.startswith("http"):
            url = "https://" + url
        await message.answer("⏳ Проверяю скорость " + url + "...")
        from pagespeed_funcs import check_pagespeed, format_pagespeed_report
        result = check_pagespeed(url, "mobile")
        await send_long(message, format_pagespeed_report(result))
        result_d = check_pagespeed(url, "desktop")
        await send_long(message, format_pagespeed_report(result_d))
        return

    wkey = "waiting_url_" + uid
    if wkey in audit_data:
        del audit_data[wkey]
        url = message.text.strip()
        if not url.startswith("http"):
            url = "https://" + url
        if "." not in url:
            await message.answer("Введите корректный адрес сайта, например: https://seopi.ru")
            audit_data[wkey] = True
            return
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✅ Проверить страницу — бесплатно", callback_data="ap|" + url)],
            [InlineKeyboardButton(text="🌐 Весь сайт — 4 900 ₽", callback_data="as|" + url)],
        ])
        await message.answer("🔍 Что проверяем на " + url + "?", reply_markup=kb)
        return
    pkey = "pending_" + uid
    if pkey in audit_data:
        email = message.text.strip()
        if "@" in email and "." in email:
            pending = audit_data.pop(pkey)
            check_name = pending["check_name"]
            price = pending["price"]
            url = audit_data.get("res_" + uid, {}).get("url", "сайт")
            try:
                from yookassa import Configuration, Payment
                Configuration.account_id = os.getenv("YOOKASSA_SHOP_ID")
                Configuration.secret_key = os.getenv("YOOKASSA_SECRET_KEY")
                p = Payment.create({
                    "amount": {"value": str(price) + ".00", "currency": "RUB"},
                    "confirmation": {"type": "redirect", "return_url": "https://t.me/seopi_seo_bot"},
                    "capture": True,
                    "description": "SEO-отчёт: " + check_name,
                    "metadata": {"email": email, "check_name": check_name, "url": url, "user_id": uid},
                }, str(uuid.uuid4()))
                pay_url = p.confirmation.confirmation_url
                audit_data["pay_" + p.id] = {"email": email, "check_name": check_name, "url": url}
                kb = InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="💳 Оплатить 90 ₽", url=pay_url)]
                ])
                await message.answer(
                    "✅ Email принят: " + email + "\n\n"
                    "После оплаты 90 ₽ отчёт придёт автоматически.\n"
                    "Исполнитель: Александр Филимонов (Самозанятый, НПД).\n"
                    "Персональные данные обрабатываются по 152-ФЗ.",
                    reply_markup=kb
                )
                try:
                    from audit_v2 import get_instruction
                    from mailer import send_report
                    instr = get_instruction(check_name)
                    sent = await send_report(email, url, check_name, instr, price)
                    if sent:
                        await message.answer("📧 Отчёт отправлен на " + email + "\nПроверьте папку Входящие и Спам.")
                    else:
                        await message.answer("⚠️ Не удалось отправить отчёт. Напишите @Aleksseopiru.")
                except Exception as email_err:
                    await message.answer("⚠️ Зона верификации email: " + str(email_err))
            except Exception as e:
                await message.answer("Зона верификации: " + str(e))
        else:
            await message.answer("Введите корректный email, например: ivan@mail.ru")
        return
    await message.answer("Обрабатываю...")
    await send_long(message, await ask_gigachat(load_prompt(), message.text))

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
