import csv
import json


def csv_to_json(csv_file="tesco_promotions.csv", json_file="products.json"):
    products = []
    with open(csv_file, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            products.append(row)

    with open(json_file, "w", encoding="utf-8") as f:
        json.dump(products, f, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    csv_to_json()