import os, random, string, asyncio
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

BOT_TOKEN   = os.getenv("BOT_TOKEN", "YOUR_BOT_TOKEN")
CHANNEL_ID  = os.getenv("CHANNEL_ID", "@darsyor_uz")
WEBAPP_URL  = os.getenv("WEBAPP_URL", "https://your-site.com")

codes: dict[str, str] = {}
verified: dict[str, str] = {}

bot = Bot(token=BOT_TOKEN)
dp  = Dispatcher(storage=MemoryStorage())

class Form(StatesGroup):
    waiting_phone = State()

def gen_code() -> str:
    return "".join(random.choices(string.digits, k=6))

@dp.message(CommandStart())
async def cmd_start(msg: Message, state: FSMContext):
    kb = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="📱 Telefon raqamni yuborish", request_contact=True)]],
        resize_keyboard=True, one_time_keyboard=True
    )
    await msg.answer(
        "👋 DarsYor'ga xush kelibsiz!\n\nRo'yxatdan o'tish uchun telefon raqamingizni yuboring 👇",
        reply_markup=kb
    )
    await state.set_state(Form.waiting_phone)

@dp.message(Form.waiting_phone, F.contact)
async def got_phone(msg: Message, state: FSMContext):
    phone = msg.contact.phone_number
    user_id = msg.from_user.id
    try:
        member = await bot.get_chat_member(CHANNEL_ID, user_id)
        is_member = member.status in ("member", "administrator", "creator")
    except Exception:
        is_member = False
    if not is_member:
        await msg.answer(
            f"⚠️ Avval kanalimizga a'zo bo'ling:\n👉 t.me/darsyor_uz\n\nA'zo bo'lgach /start ni bosing.",
            reply_markup=ReplyKeyboardRemove()
        )
        await state.clear()
        return
    code = gen_code()
    codes[phone] = code
    verified[code] = phone
    await msg.answer(
        f"✅ A'zolik tasdiqlandi!\n\n🔑 Sizning kodingiz:\n\n<b>{code}</b>\n\nBu kodni saytga kiriting:\n{WEBAPP_URL}",
        parse_mode="HTML",
        reply_markup=ReplyKeyboardRemove()
    )
    await state.clear()

@dp.message(Form.waiting_phone)
async def wrong_input(msg: Message):
    await msg.answer("Iltimos, tugma orqali telefon raqamingizni yuboring 👇")

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/verify/{code}")
async def verify_code(code: str):
    phone = verified.get(code)
    if not phone:
        raise HTTPException(status_code=400, detail="Kod noto'g'ri yoki muddati o'tgan")
    del verified[code]
    del codes[phone]
    return {"ok": True, "phone": phone}

@app.get("/health")
async def health():
    return {"status": "ok"}

async def main():
    server = uvicorn.Server(uvicorn.Config(app, host="0.0.0.0", port=int(os.getenv("PORT", 8000))))
    await asyncio.gather(
        dp.start_polling(bot, skip_updates=True),
        server.serve()
    )

if __name__ == "__main__":
    asyncio.run(main())
