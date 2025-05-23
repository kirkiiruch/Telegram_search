// Пример данных, замените на реальные данные с вашего сервера или API
let fuse;

// Функция для нормализации текста (удаляет спецсимволы и приводит символы с акцентами к базовым)
function normalizeText(text) {
    // Приводим к нижнему регистру и удаляем спецсимволы
    text = text.toLowerCase().normalize("NFD").replace(/[\u0300-\u036f]/g, "");
    // Удаляем все символы, кроме букв и цифр
    return text.replace(/[^a-z0-9]/g, "");
}

fetch('products.json')
    .then(response => response.json())
    .then(data => {
        // Нормализуем данные перед созданием поискового индекса
        data.forEach(product => {
            console.log("Нормализованное имя продукта:", normalizeText(product.name));
        });

        fuse = new Fuse(data, {
            keys: ['name'],
            threshold: 0.3, // Порог совпадений
            ignoreLocation: true,
            includeScore: true,
            shouldSort: true,
            getFn: (obj, path) => normalizeText(obj[path]), // Нормализуем текст перед поиском
        });

        console.log("Данные загружены:", data);
    })
    .catch(error => {
        console.error("Ошибка загрузки products.json:", error);
    });

function searchProducts() {
    const query = document.getElementById("searchInput").value;
    const resultsDiv = document.getElementById("results");

    if (!fuse) {
        resultsDiv.innerHTML = "<p>Данные ещё не загружены. Подождите.</p>";
        return;
    }

    if (!query) {
        resultsDiv.innerHTML = "<p>Введите запрос для поиска.</p>";
        return;
    }

    // Нормализуем запрос перед поиском
    const normalizedQuery = normalizeText(query);
    console.log("Нормализованный запрос:", normalizedQuery);  // Печатаем нормализованный запрос

    const results = fuse.search(normalizedQuery);
    console.log("Результаты поиска:", results);  // Печатаем все результаты с точкой совпадения

    if (results.length === 0) {
        resultsDiv.innerHTML = "<p>Товары не найдены.</p>";
        return;
    }

    resultsDiv.innerHTML = "";
    results.forEach((result, index) => {
        const product = result.item;
        console.log(`Результат ${index + 1}:`, result.score); // Выводим точность совпадения для каждого товара
        const productDiv = document.createElement("div");
        productDiv.className = "product";
        productDiv.innerHTML = `
            <strong>Товар #${index + 1}</strong><br>
            Название: ${product.name || 'N/A'}<br>
            Обычная цена: ${product.regular_price || 'N/A'}<br>
            Clubcard цена: ${product.clubcard_price || 'N/A'}<br>
            Дата окончания акции: ${product.expiration_date || 'N/A'}<br>
            Ссылка: <a href="${product.product_link || '#'}" target="_blank">${product.product_link || 'N/A'}</a>
        `;
        resultsDiv.appendChild(productDiv);
    });
}
