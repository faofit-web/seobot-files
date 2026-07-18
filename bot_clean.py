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
        return "Zona verifikacii: " + str(e)

async def send_long(message, text):
    for chunk in [text[i:i+4000] for i in range(0, len(text), 4000)]:
        await message.answer(chunk)
        await asyncio.sleep(0.3)

@dp.message(CommandStart())
async def cmd_start(message: types.Message):
    await message.answer(
        "Sistema Seo aktivirovana.\n\n"
        "/lending\n/statya\n/audit\n/semantika\n/otchet\n/new"
    )

@dp.message(Command("new"))
async def cmd_new(message: types.Message):
    await message.answer("Kontekst ochishchen.")

@dp.message(Command("lending"))
async def cmd_lending(message: types.Message):
    await message.answer("Obrabatyvayu...")
    await send_long(message, await ask_gigachat(load_prompt() + "\nZADACHA: Prodayushchaya stranitsa.", "Zhdu temu."))

@dp.message(Command("statya"))
async def cmd_statya(message: types.Message):
    await message.answer("Obrabatyvayu...")
    await send_long(message, await ask_gigachat(load_prompt() + "\nZADACHA: SEO-statya.", "Zhdu klyuch."))

@dp.message(Command("semantika"))
async def cmd_semantika(message: types.Message):
    await message.answer("Obrabatyvayu...")
    await send_long(message, await ask_gigachat(load_prompt() + "\nZADACHA: Semantika.", "Zhdu temu."))

@dp.message(Command("otchet"))
async def cmd_otchet(message: types.Message):
    await message.answer("Obrabatyvayu...")
    await send_long(message, await ask_gigachat(load_prompt() + "\nZADACHA: Otchet bylo/stalo.", "Zhdu dannye."))

@dp.message(Command("audit"))
async def cmd_audit(message: types.Message):
    args = message.text.split()
    if len(args) < 3 or args[1] != "2244":
        await message.answer("Format: /audit 2244 https://site.ru\n\nOdna stranitsa 490 rub\nVes sait 4900 rub")
        return
    url = args[2]
    if not url.startswith("http"):
        url = "https://" + url
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Odna stranitsa 490 rub", callback_data="ap|" + url)],
        [InlineKeyboardButton(text="Ves sait 4900 rub", callback_data="as|" + url)],
    ])
    await message.answer("Chto proveryaem na " + url + "?", reply_markup=kb)

@dp.callback_query(lambda c: c.data and (c.data.startswith("ap|") or c.data.startswith("as|")))
async def audit_start(call: types.CallbackQuery):
    url = call.data[3:]
    await call.answer()
    await call.message.answer("Proveryayu " + url + "...")
    from audit_v2 import audit_page
    result = audit_page(url)
    score = result["score"]
    total = result["total"]
    pct = round(score / total * 100) if total > 0 else 0
    if pct >= 80:
        verdict = "Horosho"
    elif pct >= 60:
        verdict = "Trebuet dorabotki"
    else:
        verdict = "Kriticheskie zony"
    uid = str(call.from_user.id)
    audit_data["res_" + uid] = {"url": url, "result": result}
    await call.message.answer(
        "SEO-audit: " + url + "\n"
        "Ocenka: " + str(score) + "/" + str(total) + " (" + str(pct) + "%) " + verdict + "\n"
        "Razmer: " + str(result["size_kb"]) + " KB\n\n"
        "Nazhite na punkt dlya podrobnostei:"
    )
    buttons = [
        [InlineKeyboardButton(
            text=("OK " if c["ok"] else "ERR ") + c["name"],
            callback_data="ai|" + uid + "|" + c["name"]
        )]
        for c in result["checks"]
    ]
    await call.message.answer("Spisok proverok:", reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))

@dp.callback_query(lambda c: c.data and c.data.startswith("ai|"))
async def audit_item(call: types.CallbackQuery):
    parts = call.data.split("|", 2)
    uid = parts[1]
    check_name = parts[2]
    await call.answer()
    key = "res_" + uid
    if key not in audit_data:
        await call.message.answer("Zapustite /audit snova.")
        return
    result = audit_data[key]["result"]
    check = next((c for c in result["checks"] if c["name"] == check_name), None)
    if not check:
        return
    if check["ok"]:
        await call.message.answer("OK: " + check_name + " - parametr v norme.")
        return
    price = check["price"]
    from audit_v2 import get_instruction
    instr = get_instruction(check_name)
    text = (
        "ERR: " + check_name + "\n\n"
        + instr["problem"] + "\n\n"
        + instr["impact"] + "\n\n"
        + instr["result"] + "\n\n"
        + "Hotite poshagovuyu instrukciyu?\n"
        + "Stoimost: " + str(price) + " rub."
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="Oplatit " + str(price) + " rub",
            callback_data="pay|" + uid + "|" + check_name + "|" + str(price)
        )],
        [InlineKeyboardButton(text="Nazad k spisku", callback_data="bk|" + uid)],
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
        "Vvedite vash email:\n\n"
        "Posle oplaty " + price + " rub otchet pridet avtomaticheski na vash email."
    )

@dp.callback_query(lambda c: c.data and c.data.startswith("bk|"))
async def audit_back(call: types.CallbackQuery):
    uid = call.data[3:]
    await call.answer()
    key = "res_" + uid
    if key not in audit_data:
        await call.message.answer("Zapustite /audit snova.")
        return
    buttons = [
        [InlineKeyboardButton(
            text=("OK " if c["ok"] else "ERR ") + c["name"],
            callback_data="ai|" + uid + "|" + c["name"]
        )]
        for c in audit_data[key]["result"]["checks"]
    ]
    await call.message.answer("Spisok proverok:", reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))

@dp.message()
async def free_text(message: types.Message):
    uid = str(message.from_user.id)
    pkey = "pending_" + uid
    if pkey in audit_data:
        email = message.text.strip()
        if "@" in email and "." in email:
            pending = audit_data.pop(pkey)
            check_name = pending["check_name"]
            price = pending["price"]
            url = audit_data.get("res_" + uid, {}).get("url", "sait")
            try:
                from yookassa import Configuration, Payment
                Configuration.account_id = os.getenv("YOOKASSA_SHOP_ID")
                Configuration.secret_key = os.getenv("YOOKASSA_SECRET_KEY")
                p = Payment.create({
                    "amount": {"value": str(price) + ".00", "currency": "RUB"},
                    "confirmation": {"type": "redirect", "return_url": "https://t.me/seopi_seo_bot"},
                    "capture": True,
                    "description": "SEO: " + check_name,
                    "metadata": {"email": email, "check_name": check_name, "url": url, "user_id": uid},
                }, str(uuid.uuid4()))
                pay_url = p.confirmation.confirmation_url
                audit_data["pay_" + p.id] = {"email": email, "check_name": check_name, "url": url}
                kb = InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="Oplatit " + str(price) + " rub", url=pay_url)]
                ])
                await message.answer(
                    "Email: " + email + "\n"
                    "Posle oplaty otchet pridet avtomaticheski.\n"
                    "Obrabotka personalnyh dannyh po 152-FZ.",
                    reply_markup=kb
                )
            except Exception as e:
                await message.answer("Zona verifikacii: " + str(e))
        else:
            await message.answer("Vvedite korektny email, naprimer: ivan@mail.ru")
        return
    await message.answer("Obrabatyvayu...")
    await send_long(message, await ask_gigachat(load_prompt(), message.text))

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
