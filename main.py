import sqlite3
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, MessageHandler, filters

TOKEN = "7995952833:AAEaLD669ZPZfYbthPpY6cOvTB4hdiWeDCg"  # O'z bot tokeningizni yozing
ADMIN_ID = 5387666015  # Adminning Telegram ID raqami

# Mahsulotlar ro‘yxati
products = {
    "30uc": 9000,
    "60uc": 12000,
    "325uc": 58000,
    "660uc": 115000,
    "1800uc": 290000,
    "3850uc": 570000,
    "8100uc": 1100000
}

# Ma'lumotlar bazasi yaratish yoki ulanish
def create_db():
    conn = sqlite3.connect("shop.db")
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS user_ids (
                      user_id INTEGER PRIMARY KEY, 
                      id_raqami TEXT)''')  # Foydalanuvchi ID raqamini saqlash
    cursor.execute('''CREATE TABLE IF NOT EXISTS orders (
                      id INTEGER PRIMARY KEY, 
                      user_id INTEGER, 
                      order_text TEXT, 
                      status TEXT)''')  # Buyurtmalarni saqlash
    cursor.execute('''CREATE TABLE IF NOT EXISTS user_status (
                      user_id INTEGER PRIMARY KEY, 
                      step INTEGER)''')  # Foydalanuvchi qaysi bosqichda ekanligini saqlash
    conn.commit()
    conn.close()


# Bot boshlang'ich xabari va tugma
async def start(update, context):
    user = update.message.from_user
    keyboard = [[InlineKeyboardButton("ID kiritish", callback_data="enter_id")]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        f"Assalomu alaykum, {user.first_name}!\n"
        "PUBG MOBILE ID raqamingizni kiritishingiz kerak. Quyidagi tugmani bosing:",
        reply_markup=reply_markup
    )


# ID kiritish tugmasi bosilganda
async def enter_id(update, context):
    query = update.callback_query
    await query.answer()  # Callbackni tasdiqlash
    await query.edit_message_text("Iltimos, PUBG MOBILE ID raqamingizni kiriting. Masalan: *1234567890*", parse_mode="Markdown")


# Foydalanuvchi ID raqamini kiritish va saqlash
async def id_raqamini_yozish(update, context):
    user = update.message.from_user
    id_raqami = update.message.text.strip()

    if not id_raqami.isdigit() or len(id_raqami) < 6:
        await update.message.reply_text("❌ Iltimos, PUBG MOBILE ID raqamingizni to‘g‘ri kiriting. Masalan: *1234567890*", parse_mode="Markdown")
        return

    conn = sqlite3.connect("shop.db")
    cursor = conn.cursor()
    cursor.execute("INSERT OR REPLACE INTO user_ids (user_id, id_raqami) VALUES (?, ?)", (user.id, id_raqami))
    conn.commit()

    # Set user step to 1 (ID is entered)
    cursor.execute("INSERT OR REPLACE INTO user_status (user_id, step) VALUES (?, ?)", (user.id, 1))
    conn.commit()
    conn.close()

    keyboard = [[InlineKeyboardButton("Buyurtma berish", callback_data="start_order")]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        f"Sizning ID raqamingiz: {id_raqami} muvaffaqiyatli saqlandi.\n"
        "Quyidagi tugma orqali buyurtma qilishingiz mumkin.",
        reply_markup=reply_markup
    )


# Buyurtma berish tugmasi bosilganda mahsulotlarni ko‘rsatish
async def start_order(update, context):
    query = update.callback_query
    await query.answer()

    # Mahsulotlar uchun tugmalar yaratish
    keyboard = [[InlineKeyboardButton(f"{nom} - {narx} so'm", callback_data=f"product_{nom}")]
                for nom, narx in products.items()]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(
        "Mahsulotlardan birini tanlang:",
        reply_markup=reply_markup
    )


# Mahsulot tanlangandan so‘ng to‘lov ma’lumotlarini yuborish
async def select_product(update, context):
    query = update.callback_query
    await query.answer()

    product_name = query.data.split("_")[1]
    total_price = products[product_name]
    order_details = f"Mahsulot: {product_name}\nJami: {total_price} so'm"
    user = query.from_user

    # Buyurtmani bazaga yozish
    conn = sqlite3.connect("shop.db")
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO orders (user_id, order_text, status) VALUES (?, ?, ?)",
        (user.id, order_details, "pending")
    )

    # Set user step to 2 (order selected)
    cursor.execute("INSERT OR REPLACE INTO user_status (user_id, step) VALUES (?, ?)", (user.id, 2))
    conn.commit()
    conn.close()

    payment_message = (
        f"✅ Siz {product_name} ni tanladingiz.\n"
        f"Umumiy narx: {total_price} so'm.\n\n"
        "To‘lovni amalga oshirish uchun quyidagi karta raqamiga to‘lov qiling va chekni yuboring:\n\n"
        "💳 Karta raqami: 9860600406437001\nKarta egasi: Karimov Murodjon"
    )
    keyboard = [[InlineKeyboardButton("Chekni yuborish", callback_data="submit_payment_receipt")]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(payment_message, reply_markup=reply_markup)


# Chekni yuborish tugmasi bosilganda
async def submit_payment_receipt(update, context):
    query = update.callback_query
    await query.answer()

    # Set user step to 3 (payment receipt submitted)
    conn = sqlite3.connect("shop.db")
    cursor = conn.cursor()
    cursor.execute("INSERT OR REPLACE INTO user_status (user_id, step) VALUES (?, ?)", (query.from_user.id, 3))
    conn.commit()
    conn.close()

    await query.edit_message_text("Iltimos, to‘lovni tasdiqlovchi rasmni yuboring.")


# Foydalanuvchidan to‘lov rasmini qabul qilish va tugma bilan yuborish
async def handle_payment_receipt(update, context):
    user = update.message.from_user

    # Check if user is allowed to submit a payment receipt (step 3)
    conn = sqlite3.connect("shop.db")
    cursor = conn.cursor()
    cursor.execute("SELECT step FROM user_status WHERE user_id=?", (user.id,))
    user_step = cursor.fetchone()
    conn.close()

    if user_step and user_step[0] == 3:  # Step 3 means they can submit the receipt
        if update.message.photo:
            photo = update.message.photo[-1].file_id
            caption = f"To'lov rasmi:\nMijoz: @{user.username if user.username else user.id}"

            # Tugma yaratish
            keyboard = [
                [InlineKeyboardButton("Tasdiqlash", callback_data=f"confirm_payment_{user.id}")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)

            # Adminga rasm va tugma yuborish
            await context.bot.send_photo(chat_id=ADMIN_ID, photo=photo, caption=caption, reply_markup=reply_markup)

            # Foydalanuvchiga tasdiqlash xabari
            await update.message.reply_text("✅ To‘lov tasdiqlandi va Adminga yuborildi. Buyurtmangiz ko'rib chiqilmoqda.")
        else:
            await update.message.reply_text("❌ Iltimos, to‘lovni tasdiqlovchi rasmni yuboring.")
    else:
        await update.message.reply_text("❌ Siz hozirda to'lovni yuborish bosqichida emassiz.")


# Admin tomonidan to‘lovni tasdiqlash
async def confirm_payment(update, context):
    query = update.callback_query
    admin_user = query.from_user

    # Tasdiqlangan foydalanuvchi ID sini olish
    target_user_id = int(query.data.split("_")[-1])

    # Admin uchun tasdiqlash xabarini yuborish
    await query.answer("To'lov tasdiqlandi!")
    await query.edit_message_caption("✅ To'lov tasdiqlandi!")

    # Foydalanuvchiga xabar yuborish
    await context.bot.send_message(
        chat_id=target_user_id,
        text="✅ Buyurtmangiz Bajarildi."
    )


def main():
    application = ApplicationBuilder().token(TOKEN).build()

    create_db()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(enter_id, pattern="^enter_id$"))
    application.add_handler(CallbackQueryHandler(start_order, pattern="^start_order$"))
    application.add_handler(CallbackQueryHandler(select_product, pattern="^product_"))
    application.add_handler(CallbackQueryHandler(submit_payment_receipt, pattern="^submit_payment_receipt$"))
    application.add_handler(CallbackQueryHandler(confirm_payment, pattern="^confirm_payment_"))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, id_raqamini_yozish))
    application.add_handler(MessageHandler(filters.PHOTO, handle_payment_receipt))

    application.run_polling()


if __name__ == "__main__":
    main()
