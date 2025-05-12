import asyncio
from playwright.async_api import async_playwright
import csv
import re
import math
from urllib.parse import urlencode


async def goto_with_retry(page, url, retries=3):
    for attempt in range(retries):
        try:
            await page.goto(url, timeout=60000)
            return True
        except Exception as e:
            print(f"Попытка {attempt + 1} не удалась для {url}: {e}")
            if attempt == retries - 1:
                raise
            await asyncio.sleep(2)
    return False


async def parse_page(page, page_number, total_pages):
    url = f"https://potravinydomov.itesco.sk/groceries/sk-SK/promotions/all?count=48&page={page_number}"
    print(f"Обработка страницы {page_number}/{total_pages}: {url}")

    try:
        await goto_with_retry(page, url)
        await page.wait_for_load_state("domcontentloaded", timeout=60000)
    except Exception as e:
        print(f"Ошибка загрузки страницы {page_number}: {e}")
        return [], page

    # Извлекаем данные о товарах
    products = []
    try:
        product_elements = await page.query_selector_all("div.product-details--wrapper")
        if not product_elements:
            print(f"Товары не найдены на странице {page_number}.")
            return products, page
    except Exception as e:
        print(f"Ошибка при поиске товаров на странице {page_number}: {e}")
        return products, page

    for i, product in enumerate(product_elements, 1):
        try:
            product_text = await product.inner_text()

            # Название товара
            name_elem = await product.query_selector("h3")
            name = await name_elem.inner_text() if name_elem else "N/A"

            # Обычная цена
            regular_price_elem = await product.query_selector("p.beans-price__subtext")
            regular_price = await regular_price_elem.inner_text() if regular_price_elem else "N/A"

            # Цена со скидкой (Clubcard)
            clubcard_price = "N/A"
            clubcard_match = re.search(r"S Clubcard (\d+[.,]\d+) €|predtým \d+[.,]\d+ €, teraz (\d+[.,]\d+) €", product_text)
            if clubcard_match:
                clubcard_price = clubcard_match.group(1) or clubcard_match.group(2)
                clubcard_price = clubcard_price + " €"

            # Дата окончания акции
            expiration_date = "N/A"
            expiration_match = re.search(r"Cena je platná do (\d{2}\.\d{2}\.\d{4})", product_text)
            if expiration_date:
                expiration_date = expiration_match.group(1)

            # Ссылка на товар
            link_elem = await product.query_selector("a")
            product_link = await link_elem.get_attribute("href") if link_elem else "N/A"
            if product_link and not product_link.startswith("http"):
                product_link = f"https://potravinydomov.itesco.sk{product_link}"

            # Форматированный вывод для товара
            print(f"\n{'-' * 60}")
            print(f"Страница {page_number}, Товар #{i}")
            print(f"  Название: {name}")
            print(f"  Обычная цена: {regular_price}")
            print(f"  Clubcard цена: {clubcard_price}")
            print(f"  Дата окончания акции: {expiration_date}")
            print(f"  Ссылка: {product_link}")
            print(f"{'-' * 60}")

            products.append({
                "name": name.strip(),
                "regular_price": regular_price,
                "clubcard_price": clubcard_price,
                "expiration_date": expiration_date,
                "product_link": product_link
            })

        except Exception as e:
            print(f"Ошибка при обработке товара #{i} на странице {page_number}: {e}")

    print(f"Страница {page_number}: собрано {len(products)} товаров.")
    return products, page


async def parse_tesco_promotions():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False, args=["--disable-blink-features=AutomationControlled"])
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36"
        )

        # Переходим на первую страницу, чтобы определить общее количество товаров
        base_url = "https://potravinydomov.itesco.sk/groceries/sk-SK/promotions/all?count=48&page=1"
        page = await context.new_page()
        await goto_with_retry(page, base_url)
        await page.wait_for_load_state("domcontentloaded", timeout=60000)

        # Извлекаем общее количество товаров
        try:
            await page.wait_for_selector("text=Zobrazených", timeout=60000)
            pagination_elem = await page.query_selector("xpath=//div[contains(text(), 'Zobrazených')]") or \
                              await page.query_selector("div.results-summary")
            pagination_text = await pagination_elem.inner_text() if pagination_elem else ""
            print(f"\nТекст пагинации: {pagination_text}")
        except Exception as e:
            print(f"Ошибка при поиске элемента с текстом 'Zobrazených': {e}")
            pagination_text = await page.evaluate("document.body.innerText")
            print(f"Текст всей страницы (через JS): {pagination_text[:500]}...")

        # Заменяем неразрывные пробелы на обычные
        pagination_text = pagination_text.replace("\xa0", " ")
        print(f"Текст пагинации после замены пробелов: {pagination_text}")

        total_items_match = re.search(r"Zobrazených\s*\d+\s*až\s*\d+\s*z\s*(\d+)\s*položiek", pagination_text)
        if total_items_match:
            total_items = int(total_items_match.group(1))
            print(f"Извлеченное количество товаров: {total_items}")
        else:
            total_items = 48
            print("Не удалось извлечь общее количество товаров, использовано значение по умолчанию: 48")

        items_per_page = 48
        total_pages = math.ceil(total_items / items_per_page)
        print(f"Всего товаров: {total_items}, страниц: {total_pages}\n")

        await page.close()

        # Ограничиваем количество одновременно обрабатываемых страниц
        max_concurrent_pages = 5
        all_products = []

        for page_start in range(1, total_pages + 1, max_concurrent_pages):
            page_end = min(page_start + max_concurrent_pages, total_pages + 1)
            tasks = []

            for page_number in range(page_start, page_end):
                new_page = await context.new_page()
                tasks.append(parse_page(new_page, page_number, total_pages))

            # Выполняем задачи параллельно
            page_results = await asyncio.gather(*tasks, return_exceptions=True)

            # Собираем результаты и закрываем страницы
            for result in page_results:
                if isinstance(result, tuple) and not isinstance(result, Exception):
                    products, page_to_close = result
                    all_products.extend(products)
                    await page_to_close.close()
                elif isinstance(result, Exception):
                    print(f"Ошибка на одной из страниц: {result}")

        # Выводим итоговую таблицу
        print("\n" + "=" * 100)
        print("Итоговые данные о товарах:")
        print("=" * 100)
        print(
            f"{'Название':<40} | {'Обычная цена':<15} | {'Clubcard цена':<15} | {'Дата окончания':<15} | {'Ссылка':<30}"
        )
        print("-" * 100)
        for product in all_products:
            print(
                f"{product['name'][:38]:<40} | "
                f"{product['regular_price']:<15} | "
                f"{product['clubcard_price']:<15} | "
                f"{product['expiration_date']:<15} | "
                f"{product['product_link'][:28]:<30}"
            )
        print("=" * 100)

        # Закрываем браузер
        await browser.close()

        # Сохраняем данные в CSV
        with open("tesco_promotions.csv", "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(
                f,
                fieldnames=["name", "regular_price", "clubcard_price", "expiration_date", "product_link"]
            )
            writer.writeheader()
            for product in all_products:
                writer.writerow(product)

        print(f"\nСобрано {len(all_products)} товаров. Данные сохранены в tesco_promotions.csv")


# Запускаем скрипт
if __name__ == "__main__":
    asyncio.run(parse_tesco_promotions())