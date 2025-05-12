import asyncio
import csv
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
    ContextTypes,
)
from thefuzz import fuzz
from thefuzz import process
from unidecode import unidecode

# Настройка логирования
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# Глобальный флаг для остановки вывода товаров
stop_output = False

# Функция для загрузки данных из CSV
def load_products_from_csv(file_path="tesco_promotions.csv"):
    products = []
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                products.append(row)
        logger.info(f"Загружено {len(products)} товаров из {file_path}")
        return products
    except FileNotFoundError:
        logger.error(f"Файл {file_path} не найден")
        return []
    except Exception as e:
        logger.error(f"Ошибка при чтении CSV: {e}")
        return []

# Функция для поиска точных и похожих товаров
def search_products(keyword, products, threshold=85):
    keyword = unidecode(keyword.lower().strip())
    exact_matches = [
        product for product in products
        if keyword in unidecode(product.get("name", "").lower())
    ]

    # Если точных совпадений нет, ищем похожие товары
    if not exact_matches:
        all_names = [product.get("name", "") for product in products if product.get("name", "")]
        all_names_normalized = [unidecode(name.lower()) for name in all_names]
        # Фильтрация по длине слов
        keyword_len = len(keyword)
        filtered_names = [
            name for name in all_names_normalized
            if keyword_len * 0.5 <= len(name) <= keyword_len * 2
        ]
        if not filtered_names:
            return []

        # Используем token_sort_ratio для поиска с опечатками
        closest_matches = process.extract(keyword, filtered_names, limit=3, scorer=fuzz.token_sort_ratio)
        logger.info(f"Похожие товары для '{keyword}': {closest_matches}")
        similar_products = []
        for match, score in closest_matches:
            if score >= threshold:  # Порог схожести
                for product in products:
                    if unidecode(product.get("name", "").lower()) == match:
                        similar_products.append(product)
                        break
        return similar_products
    return exact_matches

# Обработчик команды /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Привет! Я бот для поиска акционных товаров Tesco. "
        "Отправь мне название товара (например, 'Lyofilizované'), и я найду все подходящие предложения!"
    )

# Обработчик текстовых сообщений
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global stop_output
    stop_output = False  # Сбрасываем флаг перед новым поиском

    keyword = update.message.text
    logger.info(f"Получен запрос: {keyword}")

    # Загружаем данные из CSV
    products = load_products_from_csv()
    if not products:
        await update.message.reply_text(
            "Не удалось загрузить данные о товарах. Убедитесь, что файл tesco_promotions.csv существует."
        )
        return

    # Ищем товары (точные или похожие)
    matching_products = search_products(keyword, products)
    if not matching_products:
        # Предлагаем похожие названия
        all_names = [product.get("name", "") for product in products if product.get("name", "")]
        all_names_normalized = [unidecode(name.lower()) for name in all_names]
        closest_matches = process.extract(unidecode(keyword.lower()), all_names_normalized, limit=3, scorer=fuzz.token_sort_ratio)
        suggestions = [all_names[all_names_normalized.index(match[0])] for match in closest_matches if match[1] >= 70]
        if suggestions:
            await update.message.reply_text(
                f"Товары по запросу '{keyword}' не найдены. Возможно, вы имели в виду:\n"
                + "\n".join([f"- {s}" for s in suggestions]) + "\nПопробуйте уточнить запрос."
            )
        else:
            await update.message.reply_text(
                f"Товары по запросу '{keyword}' не найдены. Попробуйте уточнить запрос."
            )
        return

    # Создаём кнопку "Стоп"
    keyboard = [[InlineKeyboardButton("Стоп", callback_data="stop_output")]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    # Отправляем общее количество найденных товаров с кнопкой "Стоп"
    await update.message.reply_text(
        f"Найдено {len(matching_products)} товаров по запросу '{keyword}':",
        reply_markup=reply_markup
    )

    # Отправляем каждый товар отдельным сообщением
    for i, product in enumerate(matching_products, 1):
        if stop_output:  # Проверяем, не нажата ли кнопка "Стоп"
            await update.message.reply_text("Вывод товаров остановлен.")
            break

        response = (
            f"**Товар #{i}**\n"
            f"Название: {product.get('name', 'N/A')}\n"
            f"Обычная цена: {product.get('regular_price', 'N/A')}\n"
            f"Clubcard цена: {product.get('clubcard_price', 'N/A')}\n"
            f"Дата окончания акции: {product.get('expiration_date', 'N/A')}\n"
            f"Ссылка: {product.get('product_link', 'N/A')}\n"
        )
        await update.message.reply_text(response, parse_mode="Markdown")
        # Небольшая задержка между сообщениями
        await asyncio.sleep(0.5)

# Обработчик нажатия на кнопку "Стоп"
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global stop_output
    query = update.callback_query
    await query.answer()

    if query.data == "stop_output":
        stop_output = True
        # Удаляем кнопку "Стоп" из сообщения
        await query.edit_message_reply_markup(reply_markup=None)

# Обработчик ошибок
async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.error(f"Ошибка: {context.error}")
    if update and update.message:
        await update.message.reply_text(
            "Произошла ошибка. Попробуйте снова позже."
        )

# Основная функция для запуска бота
async def main():
    # Замените 'YOUR_BOT_TOKEN' на токен вашего бота
    BOT_TOKEN = "7414902681:AAEuSnNg5TkTiSPoln1nl2_5T1JuYEXLKJo"

    # Создаём приложение
    application = Application.builder().token(BOT_TOKEN).build()

    # Добавляем обработчики
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.add_handler(CallbackQueryHandler(button_handler))
    application.add_error_handler(error_handler)

    # Запускаем бота
    logger.info("Бот запущен")
    await application.initialize()
    await application.start()
    await application.updater.start_polling(allowed_updates=Update.ALL_TYPES)

    # Держим бота активным
    try:
        await asyncio.Event().wait()
    finally:
        await application.updater.stop()
        await application.stop()
        await application.shutdown()

if __name__ == "__main__":
    # Создаём новый цикл событий
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(main())
    except Exception as e:
        logger.error(f"Ошибка запуска: {e}")
    finally:
        loop.close()