CATEGORY_KEYWORDS = {
    'Одежда': {
        'keywords': ['свитшот', 'худи', 'футболка', 'брюки', 'джинсы', 'рубашка', 'кофта', 'пальто', 'куртка', 'платье', 'юбка', 'шорты'],
        'gender_keywords': ['мужское', 'женское', 'детское', 'унисекс']
    },
    'Обувь': {
        'keywords': ['кроссовки', 'ботинки', 'туфли', 'сандалии', 'кеды', 'мокасины', 'сапоги', 'балетки'],
        'gender_keywords': ['мужское', 'женское', 'детское', 'унисекс']
    },
    'Аксессуары': {
        'keywords': ['сумка', 'рюкзак', 'кошелек', 'ремень', 'шарф', 'перчатки', 'шапка', 'очки'],
        'gender_keywords': ['мужское', 'женское', 'детское', 'унисекс']
    },
    'Спортивные товары': {
        'keywords': ['спорт', 'фитнес', 'тренировка', 'бег', 'йога'],
        'gender_keywords': ['мужское', 'женское', 'детское', 'унисекс']
    }
}

DEFAULT_CATEGORY = 'Разное'
DEFAULT_MAX_WORDS = 1

CURRENCY_MAP = {
    "руб": "RUB",
    "р": "RUB", 
    "₽": "RUB",
    "usd": "USD",
    "$": "USD",
    "eur": "EUR",
    "€": "EUR",
    "uah": "UAH",
    "₴": "UAH",
    "byn": "BYN",
    "br": "BYR",
}

SIZE_KEYWORDS = ["s", "m", "l", "xl", "xxl", "xs"]
SIZE_MAPPING = {
    "S": "S",
    "SMALL": "S",
    "M": "M", 
    "MEDIUM": "M",
    "L": "L",
    "LARGE": "L",
    "XL": "XL",
    "XXL": "XXL",
    "2XL": "XXL",
    "XXXL": "XXXL",
    "3XL": "XXXL",
    "XS": "XS",
    "XSMALL": "XS",
}

IMAGE_SEPARATORS = [" ", ",", ";"]

TRUE_AVAILABILITY_VALUES = ("1", "true", "yes", "y", "available", "in stock", "есть", "в наличии")
