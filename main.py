# File: main.py — основной бот ароматизаторов (логика Telegram-бота)

import os
import re
import csv
import logging
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ConversationHandler,
    ContextTypes,
    filters,
)

# ─────────────────────────────────────────────────────────
# ЗАГРУЗКА КОНФИГУРАЦИИ
# ─────────────────────────────────────────────────────────

load_dotenv()
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
ADMIN_CHAT_ID = os.getenv("ADMIN_CHAT_ID")

if not TELEGRAM_TOKEN or not ADMIN_CHAT_ID:
    missing = [name for name, val in [("TELEGRAM_TOKEN", TELEGRAM_TOKEN), ("ADMIN_CHAT_ID", ADMIN_CHAT_ID)] if not val]
    print("❌ Ошибка: не найдены обязательные переменные в файле .env:")
    for m in missing:
        print(f"   {m}")
    print("\nСоздайте файл .env рядом с main.py и добавьте нужные строки:")
    print("   TELEGRAM_TOKEN=ваш_токен_от_BotFather")
    print("   ADMIN_CHAT_ID=ваш_chat_id")
    exit(1)

ADMIN_CHAT_ID = int(ADMIN_CHAT_ID)

# ─────────────────────────────────────────────────────────
# НАСТРОЙКА ЛОГИРОВАНИЯ
# ─────────────────────────────────────────────────────────

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────
# ПУТИ К ФАЙЛАМ
# ─────────────────────────────────────────────────────────

BASE_DIR = Path(__file__).parent
PDF_PATH = BASE_DIR / "commercial_offer.pdf"
ORDERS_CSV = BASE_DIR / "orders.csv"

# ─────────────────────────────────────────────────────────
# КОНТЕНТ: 16 ГРУПП АРОМАТИЗАТОРОВ
# ─────────────────────────────────────────────────────────

AROMA_GROUPS = [
    {
        "id": "citrus",
        "name": "🍋 Цитрусовые",
        "count": 24,
        "popular": ["Лимон", "Апельсин", "Грейпфрут", "Лайм", "Мандарин"],
    },
    {
        "id": "berry",
        "name": "🍓 Ягодные",
        "count": 31,
        "popular": ["Клубника", "Малина", "Черника", "Вишня", "Смородина"],
    },
    {
        "id": "tropical",
        "name": "🍍 Тропические",
        "count": 19,
        "popular": ["Манго", "Ананас", "Маракуйя", "Кокос", "Папайя"],
    },
    {
        "id": "stone",
        "name": "🍑 Косточковые",
        "count": 17,
        "popular": ["Персик", "Абрикос", "Слива", "Черешня", "Нектарин"],
    },
    {
        "id": "apple_pear",
        "name": "🍏 Яблочно-грушевые",
        "count": 14,
        "popular": ["Яблоко", "Груша", "Айва", "Яблоко-корица", "Зелёное яблоко"],
    },
    {
        "id": "dairy",
        "name": "🥛 Молочные",
        "count": 22,
        "popular": ["Сливки", "Сгущёнка", "Йогурт", "Кефир", "Творог"],
    },
    {
        "id": "vanilla",
        "name": "🌿 Ванильные",
        "count": 11,
        "popular": ["Ваниль классическая", "Ваниль бурбон", "Ваниль Madagascar", "Ванильный крем", "Тонка"],
    },
    {
        "id": "confectionery",
        "name": "🍰 Кондитерские",
        "count": 28,
        "popular": ["Карамель", "Шоколад", "Тирамису", "Чизкейк", "Вафля"],
    },
    {
        "id": "nut",
        "name": "🥜 Ореховые",
        "count": 16,
        "popular": ["Фундук", "Миндаль", "Арахис", "Грецкий орех", "Фисташка"],
    },
    {
        "id": "mint",
        "name": "🌱 Мятные и ментоловые",
        "count": 13,
        "popular": ["Мята перечная", "Мята садовая", "Ментол", "Мята-лимон", "Холодящая мята"],
    },
    {
        "id": "coffee_tea",
        "name": "☕ Кофейные и чайные",
        "count": 18,
        "popular": ["Эспрессо", "Капучино", "Зелёный чай", "Чай с бергамотом", "Матча"],
    },
    {
        "id": "alcohol",
        "name": "🥃 Алкогольные",
        "count": 20,
        "popular": ["Ром", "Коньяк", "Виски", "Амаретто", "Ирландский крем"],
    },
    {
        "id": "spice",
        "name": "🌶 Пряные и специи",
        "count": 25,
        "popular": ["Корица", "Имбирь", "Кардамон", "Анис", "Гвоздика"],
    },
    {
        "id": "floral",
        "name": "🌸 Цветочные",
        "count": 12,
        "popular": ["Роза", "Лаванда", "Жасмин", "Фиалка", "Бузина"],
    },
    {
        "id": "smoke",
        "name": "🔥 Дымные и копчёные",
        "count": 9,
        "popular": ["Дым барбекю", "Копчёная древесина", "Торф", "Жжёная карамель", "Дым бочки"],
    },
    {
        "id": "vegetable",
        "name": "🥬 Овощные и зелёные",
        "count": 15,
        "popular": ["Огурец", "Базилик", "Сельдерей", "Зелёный перец", "Шпинат"],
    },
]

# ─────────────────────────────────────────────────────────
# КОНТЕНТ: FAQ — 6 ТЕМ
# ─────────────────────────────────────────────────────────

FAQ_ITEMS = [
    {
        "id": "origin",
        "question": "🌍 Где производятся ароматизаторы?",
        "answer": (
            "Мы сотрудничаем с крупными европейскими заводами, например в Германии и Франции. "
            "А также являемся партнёрами производителей в Японии."
        ),
    },
    {
        "id": "delivery",
        "question": "🚚 Как быстро доставят заказ?",
        "answer": (
            "Мы являемся сертифицированными поставщиками импортного сырья, доставляем ароматизаторы собственным транспортом. "
            "После заказа и оплаты назовём примерный срок и привезём сырьё вовремя. "
            "Срок зависит от размера партии и от того, насколько редкий вкус ароматизатора вам нужен."
        ),
    },
    {
        "id": "volume",
        "question": "📦 Минимальный размер партии?",
        "answer": (
            "Минимальный размер — 25 кг, максимальной границы нет."
        ),
    },
    {
        "id": "payment",
        "question": "💳 Как проходит оплата?",
        "answer": (
            "Мы выставляем счёт в рублях, вы оплачиваете его в стандартном порядке."
        ),
    },
    {
        "id": "custom",
        "question": "🎨 В каталоге нет вкуса, что делать?",
        "answer": (
            "Вы можете оставить заявку, наш консультант свяжется с вами и уточнит детали. "
            "Потом мы передадим ваш запрос на завод, который производит пищевые ароматизаторы. "
            "Производитель может пойти навстречу и кастомизировать вкус под ваш запрос."
        ),
    },
]

# ─────────────────────────────────────────────────────────
# СОСТОЯНИЯ ДИАЛОГА ЗАЯВКИ
# ─────────────────────────────────────────────────────────

ORDER_GROUP, ORDER_FLAVOR, ORDER_VOLUME, ORDER_CONTACT = range(4)

# ─────────────────────────────────────────────────────────
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ─────────────────────────────────────────────────────────

def validate_contact(text: str) -> bool:
    """Проверяет, является ли строка телефоном или email."""
    phone_pattern = re.compile(r"^[\+\d][\d\s\-\(\)]{6,20}$")
    email_pattern = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
    cleaned = text.strip()
    return bool(phone_pattern.match(cleaned) or email_pattern.match(cleaned))


def save_order(order: dict):
    """Сохраняет заявку в CSV-файл."""
    fieldnames = ["datetime", "user_id", "username", "group", "flavor", "volume", "contact"]
    file_exists = ORDERS_CSV.exists()
    with open(ORDERS_CSV, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        if not file_exists:
            writer.writeheader()
        writer.writerow(order)


def main_menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📦 Ассортимент", callback_data="menu_assortment")],
        [InlineKeyboardButton("❓ FAQ", callback_data="menu_faq")],
        [InlineKeyboardButton("📄 Коммерческое предложение", callback_data="menu_cp")],
        [InlineKeyboardButton("✍️ Оставить заявку", callback_data="menu_order")],
        [InlineKeyboardButton("🙋 Позвать консультанта", callback_data="menu_consultant")],
    ])


def back_to_main_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🏠 Главное меню", callback_data="menu_main")],
    ])


# ─────────────────────────────────────────────────────────
# ГЛАВНОЕ МЕНЮ
# ─────────────────────────────────────────────────────────

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "👋 Добро пожаловать!\n\n"
        "Мы предлагаем широкий ассортимент пищевых ароматизаторов "
        "для производств любого масштаба.\n\n"
        "Выберите нужный раздел:"
    )
    await update.message.reply_text(text, reply_markup=main_menu_keyboard())


async def show_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("Выберите нужный раздел:", reply_markup=main_menu_keyboard())


# ─────────────────────────────────────────────────────────
# АССОРТИМЕНТ
# ─────────────────────────────────────────────────────────

async def show_assortment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    keyboard = []
    for group in AROMA_GROUPS:
        keyboard.append([InlineKeyboardButton(group["name"], callback_data=f"group_{group['id']}")])
    keyboard.append([InlineKeyboardButton("🏠 Главное меню", callback_data="menu_main")])
    await query.edit_message_text(
        "📦 Наш ассортимент — 16 групп ароматизаторов:\n\nВыберите группу:",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


async def show_group(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    group_id = query.data.replace("group_", "")
    group = next((g for g in AROMA_GROUPS if g["id"] == group_id), None)
    if not group:
        await query.edit_message_text("Группа не найдена.", reply_markup=back_to_main_keyboard())
        return
    popular_list = "\n".join(f"  • {p}" for p in group["popular"])
    text = (
        f"{group['name']}\n\n"
        f"Количество вкусов: {group['count']}\n\n"
        f"Популярные позиции:\n{popular_list}"
    )
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("✍️ Оставить заявку", callback_data="menu_order")],
        [InlineKeyboardButton("🙋 Позвать консультанта", callback_data="menu_consultant")],
        [InlineKeyboardButton("◀️ Назад к группам", callback_data="menu_assortment")],
        [InlineKeyboardButton("🏠 Главное меню", callback_data="menu_main")],
    ])
    await query.edit_message_text(text, reply_markup=keyboard)


# ─────────────────────────────────────────────────────────
# FAQ
# ─────────────────────────────────────────────────────────

async def show_faq(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    keyboard = []
    for item in FAQ_ITEMS:
        keyboard.append([InlineKeyboardButton(item["question"], callback_data=f"faq_{item['id']}")])
    keyboard.append([InlineKeyboardButton("🏠 Главное меню", callback_data="menu_main")])
    await query.edit_message_text(
        "❓ Часто задаваемые вопросы:\n\nВыберите тему:",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


async def show_faq_item(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    faq_id = query.data.replace("faq_", "")
    item = next((f for f in FAQ_ITEMS if f["id"] == faq_id), None)
    if not item:
        await query.edit_message_text("Вопрос не найден.", reply_markup=back_to_main_keyboard())
        return
    text = f"{item['question']}\n\n{item['answer']}"
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("◀️ Назад к вопросам", callback_data="menu_faq")],
        [InlineKeyboardButton("✍️ Оставить заявку", callback_data="menu_order")],
        [InlineKeyboardButton("🙋 Позвать консультанта", callback_data="menu_consultant")],
        [InlineKeyboardButton("🏠 Главное меню", callback_data="menu_main")],
    ])
    await query.edit_message_text(text, reply_markup=keyboard)


# ─────────────────────────────────────────────────────────
# КОММЕРЧЕСКОЕ ПРЕДЛОЖЕНИЕ
# ─────────────────────────────────────────────────────────

async def send_commercial_offer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not PDF_PATH.exists():
        await query.edit_message_text(
            "⚠️ Файл коммерческого предложения пока не загружен.\n"
            "Пожалуйста, свяжитесь с нами через кнопку «Позвать консультанта».",
            reply_markup=back_to_main_keyboard(),
        )
        return
    with open(PDF_PATH, "rb") as pdf_file:
        await context.bot.send_document(
            chat_id=query.message.chat_id,
            document=pdf_file,
            filename="Коммерческое_предложение.pdf",
            caption="📄 Наше коммерческое предложение. Для вопросов — нажмите «Позвать консультанта».",
        )
    await query.edit_message_text("✅ Файл отправлен выше ⬆️", reply_markup=main_menu_keyboard())


# ─────────────────────────────────────────────────────────
# КОНСУЛЬТАНТ
# ─────────────────────────────────────────────────────────

async def call_consultant(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user = query.from_user
    username = f"@{user.username}" if user.username else f"ID: {user.id}"
    notify_text = (
        f"🙋 Запрос на консультацию\n\n"
        f"Пользователь: {user.full_name} ({username})\n"
        f"Chat ID: {user.id}\n"
        f"Время: {datetime.now().strftime('%d.%m.%Y %H:%M')}"
    )
    await context.bot.send_message(chat_id=ADMIN_CHAT_ID, text=notify_text)
    await query.edit_message_text(
        "✅ Консультант уведомлён и скоро свяжется с вами.\n\n"
        "Пока можете ознакомиться с нашим ассортиментом или оформить заявку.",
        reply_markup=main_menu_keyboard(),
    )


# ─────────────────────────────────────────────────────────
# НАПОМИНАНИЯ О НЕЗАВЕРШЁННЫХ ЗАЯВКАХ
# ─────────────────────────────────────────────────────────

REMINDER_DELAY_SECONDS = 30 * 60  # 30 минут


def _schedule_reminder(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Планирует напоминание пользователю через 30 минут."""
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    job = context.application.job_queue.run_once(
        _send_reminder,
        when=REMINDER_DELAY_SECONDS,
        data={"chat_id": chat_id},
        name=f"reminder_{user_id}",
    )
    context.user_data["reminder_job"] = job


def _cancel_reminder(context: ContextTypes.DEFAULT_TYPE):
    """Отменяет запланированное напоминание, если оно есть."""
    job = context.user_data.get("reminder_job")
    if job:
        job.schedule_removal()
        context.user_data.pop("reminder_job", None)


async def _send_reminder(context: ContextTypes.DEFAULT_TYPE):
    """Отправляет напоминание пользователю о незавершённой заявке."""
    data = context.job.data
    await context.bot.send_message(
        chat_id=data["chat_id"],
        text=(
            "👋 Напоминаем, что вы начали оформление заявки, но не завершили её.\n\n"
            "Нажмите «Оставить заявку», чтобы продолжить."
        ),
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("✍️ Оставить заявку", callback_data="menu_order")],
            [InlineKeyboardButton("🏠 Главное меню", callback_data="menu_main")],
        ]),
    )


# ─────────────────────────────────────────────────────────
# ОФОРМЛЕНИЕ ЗАЯВКИ — ConversationHandler
# ─────────────────────────────────────────────────────────

async def start_order(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Запуск оформления заявки."""
    query = update.callback_query
    await query.answer()
    context.user_data["order"] = {}
    _cancel_reminder(context)
    _schedule_reminder(update, context)
    keyboard = []
    for group in AROMA_GROUPS:
        keyboard.append([InlineKeyboardButton(group["name"], callback_data=f"order_group_{group['id']}")])
    keyboard.append([InlineKeyboardButton("❌ Отмена", callback_data="order_cancel")])
    await query.edit_message_text(
        "✍️ Оформление заявки\n\nШаг 1 из 4. Выберите группу ароматизаторов:",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )
    return ORDER_GROUP


async def order_group_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    group_id = query.data.replace("order_group_", "")
    group = next((g for g in AROMA_GROUPS if g["id"] == group_id), None)
    if not group:
        await query.edit_message_text("Ошибка выбора. Попробуйте ещё раз.", reply_markup=back_to_main_keyboard())
        return ConversationHandler.END
    context.user_data["order"]["group"] = group["name"]
    await query.edit_message_text(
        f"✅ Группа: {group['name']}\n\n"
        "Шаг 2 из 4. Введите вкусовой профиль\n"
        "(например: «Клубника с мятой» или «Карамельный эспрессо»):"
    )
    return ORDER_FLAVOR


async def order_flavor_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    flavor = update.message.text.strip()
    if not flavor:
        await update.message.reply_text(
            "⚠️ Это поле обязательно. Пожалуйста, введите вкусовой профиль."
        )
        return ORDER_FLAVOR
    context.user_data["order"]["flavor"] = flavor
    await update.message.reply_text(
        f"✅ Вкусовой профиль: {flavor}\n\n"
        "Шаг 3 из 4. Введите объём заказа\n"
        "(например: «50 кг» или «500 литров»):"
    )
    return ORDER_VOLUME


async def order_volume_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    volume = update.message.text.strip()
    if not volume:
        await update.message.reply_text(
            "⚠️ Это поле обязательно. Пожалуйста, введите объём заказа."
        )
        return ORDER_VOLUME
    context.user_data["order"]["volume"] = volume
    await update.message.reply_text(
        f"✅ Объём: {volume}\n\n"
        "Шаг 4 из 4. Введите ваши контактные данные\n"
        "(номер телефона или email):"
    )
    return ORDER_CONTACT


async def order_contact_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    contact = update.message.text.strip()
    if not validate_contact(contact):
        await update.message.reply_text(
            "⚠️ Не удалось распознать формат. "
            "Введите номер телефона или адрес электронной почты.\n"
            "Пример: +79001234567 или mail@example.com"
        )
        return ORDER_CONTACT
    context.user_data["order"]["contact"] = contact
    order = context.user_data["order"]
    _cancel_reminder(context)
    # Сохраняем заявку в CSV
    user = update.effective_user
    order_record = {
        "datetime": datetime.now().strftime("%d.%m.%Y %H:%M"),
        "user_id": user.id,
        "username": user.username or "",
        "group": order["group"],
        "flavor": order["flavor"],
        "volume": order["volume"],
        "contact": order["contact"],
    }
    save_order(order_record)
    # Уведомляем администратора
    username = f"@{user.username}" if user.username else f"ID: {user.id}"
    admin_text = (
        f"📬 Новая заявка!\n\n"
        f"Пользователь: {user.full_name} ({username})\n"
        f"Время: {order_record['datetime']}\n\n"
        f"Группа: {order['group']}\n"
        f"Вкусовой профиль: {order['flavor']}\n"
        f"Объём: {order['volume']}\n"
        f"Контакт: {order['contact']}"
    )
    await context.bot.send_message(chat_id=ADMIN_CHAT_ID, text=admin_text)
    # Подтверждение пользователю
    await update.message.reply_text(
        "✅ Заявка принята! Менеджер свяжется с вами в ближайшее время.\n\n"
        "Спасибо за интерес к нашей продукции!",
        reply_markup=main_menu_keyboard(),
    )
    context.user_data.pop("order", None)
    return ConversationHandler.END


async def order_cancel_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отмена заявки через кнопку."""
    query = update.callback_query
    await query.answer()
    _cancel_reminder(context)
    context.user_data.pop("order", None)
    await query.edit_message_text("❌ Оформление заявки отменено.", reply_markup=main_menu_keyboard())
    return ConversationHandler.END


async def order_cancel_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отмена заявки через команду /cancel."""
    _cancel_reminder(context)
    context.user_data.pop("order", None)
    await update.message.reply_text("❌ Оформление заявки отменено.", reply_markup=main_menu_keyboard())
    return ConversationHandler.END


# ─────────────────────────────────────────────────────────
# ТОЧКА ВХОДА
# ─────────────────────────────────────────────────────────

def main():
    app = Application.builder().token(TELEGRAM_TOKEN).build()

    # ConversationHandler для пошагового оформления заявки
    order_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(start_order, pattern="^menu_order$")],
        states={
            ORDER_GROUP: [
                CallbackQueryHandler(order_group_selected, pattern="^order_group_"),
                CallbackQueryHandler(order_cancel_callback, pattern="^order_cancel$"),
            ],
            ORDER_FLAVOR: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, order_flavor_received),
            ],
            ORDER_VOLUME: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, order_volume_received),
            ],
            ORDER_CONTACT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, order_contact_received),
            ],
        },
        fallbacks=[
            CallbackQueryHandler(order_cancel_callback, pattern="^order_cancel$"),
            CommandHandler("cancel", order_cancel_command),
        ],
        allow_reentry=True,
    )

    # Регистрируем обработчики
    app.add_handler(CommandHandler("start", start))
    app.add_handler(order_conv)
    app.add_handler(CallbackQueryHandler(show_main_menu, pattern="^menu_main$"))
    app.add_handler(CallbackQueryHandler(show_assortment, pattern="^menu_assortment$"))
    app.add_handler(CallbackQueryHandler(show_group, pattern="^group_"))
    app.add_handler(CallbackQueryHandler(show_faq, pattern="^menu_faq$"))
    app.add_handler(CallbackQueryHandler(show_faq_item, pattern="^faq_"))
    app.add_handler(CallbackQueryHandler(send_commercial_offer, pattern="^menu_cp$"))
    app.add_handler(CallbackQueryHandler(call_consultant, pattern="^menu_consultant$"))

    logger.info("Бот запущен.")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()