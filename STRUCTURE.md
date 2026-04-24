# Структура проекта Tenzosila_KP_Dogovor

```
Tenzosila_KP_Dogovor/
├── README.md                          # Описание проекта и запуск
├── STRUCTURE.md                       # Карта структуры (этот файл)
├── .gitignore                         # Исключения git
├── requirements.txt                   # Зависимости Python
├── .env.example                       # Переменные окружения
├── 01_concept/
│   └── concept.md                     # Концепция проекта
├── 02_plan/
│   └── roadmap.md                     # Дорожная карта
├── 03_knowledge_base/                 # База знаний
│   ├── opisanie_tipa_VESTA.md         # Описание типа СИ
│   ├── spravochnik_vesta.md           # Внутренний справочник
│   └── sample_kps/                    # Примеры реальных КП
│       ├── Gipsobeton_VESTA-S-80-18.pdf
│       └── Kirova_VESTA-FL-80-18.pdf
├── data/                              # Справочники и данные
│   ├── build_models.py                # Скрипт сборки справочника
│   ├── models.json                    # Готовый справочник моделей
│   └── .gitkeep
├── templates/                         # Шаблоны документов
│   ├── contract_templates/            # Шаблоны договоров
│   └── .gitkeep
├── src/                               # Исходный код
│   ├── __init__.py
│   ├── models/                        # Pydantic-модели
│   │   └── __init__.py
│   ├── data_loaders/                  # Загрузка JSON
│   │   └── __init__.py
│   ├── ui/                            # Интерфейс Streamlit
│   │   └── __init__.py
│   ├── generators/                    # Генерация DOCX
│   │   └── __init__.py
│   └── utils/                         # Утилиты
│       └── __init__.py
├── tests/                             # Тестирование
│   └── __init__.py
├── output/                            # Результаты генерации
│   └── .gitkeep
└── docs/                              # Документация разработки
    ├── decisions.md                   # Журнал решений
    ├── backlog.md                     # Бэклог идей
    └── QUESTIONS_TO_PRODUCTION.md     # Вопросы к производству
```
