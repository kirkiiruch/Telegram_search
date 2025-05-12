// Пример данных, замените на реальные данные с вашего сервера или API
const products = [
    { "name": "Pomaranče voľné", "regular_price": "2,15 €/kg", "clubcard_price": "1.39 €", "expiration_date": "13.05.2025", "product_link": "https://potravinydomov.itesco.sk/groceries/sk-SK/products/2002006558552" }
    // Добавьте другие товары
];

// Настройка Fuse.js для поиска
const fuse = new Fuse(products, {
    keys: ['name'],
    threshold: 0.4, // Порог схожести
    ignoreLocation: true,
    includeScore: true
});

function searchProducts() {
    const query = document.getElementById("searchInput").value.toLowerCase();
    const resultsDiv = document.getElementById("results");

    if (!query) {
        resultsDiv.innerHTML = "<p>Введите запрос для поиска.</p>";
        return;
    }

    // Поиск с использованием Fuse.js
    const results = fuse.search(query);
    if (results.length === 0) {
        resultsDiv.innerHTML = "<p>Товары не найдены.</p>";
        return;
    }

    // Отображаем результаты
    resultsDiv.innerHTML = "";
    results.forEach((result, index) => {
        const product = result.item;
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
