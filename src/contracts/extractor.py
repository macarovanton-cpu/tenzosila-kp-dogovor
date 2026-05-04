"""
extractor.py — извлечение текста из PDF/DOCX и данных через OpenRouter API
"""

import json
import re
from pathlib import Path

import pdfplumber
import streamlit as st
from docx import Document
from openai import OpenAI

PROMPT_PATH = Path(__file__).parent / "prompts" / "extract_contract_data.txt"


def extract_pdf_text(pdf_path: str, pages: list[int] = None) -> str:
    """
    Извлекает текст из PDF.
    pages — список номеров страниц (с 1). Если None — все страницы.
    """
    with pdfplumber.open(pdf_path) as pdf:
        total = len(pdf.pages)
        if pages is None:
            pages = list(range(1, total + 1))

        parts = []
        for page_num in pages:
            if 1 <= page_num <= total:
                text = pdf.pages[page_num - 1].extract_text()
                if text:
                    parts.append(f"=== СТРАНИЦА {page_num} ===\n{text}")

        return "\n\n".join(parts)


def extract_kp_text(pdf_path: str) -> str:
    """
    Извлекает нужные страницы из КП:
    - Страница 3: технические характеристики
    - Страница 4: спецификация и условия оплаты
    - Страница 5: (если есть ОРИОН — третья спецификация)
    Если страниц меньше — берёт что есть.
    """
    with pdfplumber.open(pdf_path) as pdf:
        total = len(pdf.pages)
        # Берём страницы 3–5, но не больше чем есть
        target_pages = [p for p in [3, 4, 5] if p <= total]

        parts = []
        for page_num in target_pages:
            text = pdf.pages[page_num - 1].extract_text()
            if text:
                parts.append(f"=== СТРАНИЦА {page_num} ===\n{text}")

        return "\n\n".join(parts)


def extract_docx_text(docx_path: str) -> str:
    """
    Извлекает текст из Word-документа (карточка контрагента).
    Обрабатывает таблицы и параграфы.
    """
    doc = Document(docx_path)
    parts = []

    # Таблицы (основная часть карточки)
    for table in doc.tables:
        for row in table.rows:
            cells = [c.text.strip() for c in row.cells]
            # Убираем дубли (merged cells) и пустые
            unique = []
            seen = set()
            for c in cells:
                if c and c not in seen:
                    unique.append(c)
                    seen.add(c)
            if unique:
                parts.append(" | ".join(unique))

    # Отдельные параграфы (если есть)
    for p in doc.paragraphs:
        t = p.text.strip()
        if t and t not in parts:
            parts.append(t)

    return "\n".join(parts)


def extract_data_via_ai(kp_text: str, card_text: str) -> dict:
    """
    Отправляет тексты в OpenRouter API, получает JSON с данными для договора.
    Возвращает dict с ключами 'requisites' и 'specification'.
    """
    with open(PROMPT_PATH, 'r', encoding='utf-8') as f:
        system_prompt = f.read()

    client = OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=st.secrets["OPENROUTER_API_KEY"],
    )

    user_message = (
        f"КОММЕРЧЕСКОЕ ПРЕДЛОЖЕНИЕ:\n{kp_text}"
        f"\n\n---\n\nКАРТОЧКА КОНТРАГЕНТА:\n{card_text}"
    )

    response = client.chat.completions.create(
        model="qwen/qwen3-235b-a22b:free",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ],
    )
    raw = response.choices[0].message.content.strip()

    # Убираем markdown-обёртку если есть
    raw = re.sub(r'^```json\s*', '', raw)
    raw = re.sub(r'\s*```$', '', raw)
    raw = raw.strip()

    return json.loads(raw)


def extract_from_files(kp_path: str, card_path: str) -> dict:
    """
    Главная функция: принимает пути к файлам, возвращает dict с данными.
    card_path может быть .docx или .pdf
    """
    # Извлекаем текст КП
    kp_text = extract_kp_text(kp_path)

    # Извлекаем текст карточки (поддерживаем оба формата)
    if card_path.lower().endswith('.pdf'):
        card_text = extract_pdf_text(card_path)
    else:
        card_text = extract_docx_text(card_path)

    # Получаем данные через AI
    data = extract_data_via_ai(kp_text, card_text)
    return data
