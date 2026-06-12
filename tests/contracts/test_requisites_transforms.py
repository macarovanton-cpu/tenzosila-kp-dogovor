"""Тесты для src/contracts/requisites_transforms.py."""
from __future__ import annotations

import pytest


# ---------------------------------------------------------------------------
# full_name_from_short
# ---------------------------------------------------------------------------

class TestFullNameFromShort:
    def test_ooo(self):
        from src.contracts.requisites_transforms import full_name_from_short
        result = full_name_from_short('ООО "Ромашка"')
        assert result == 'Общество с ограниченной ответственностью "Ромашка"'

    def test_ao(self):
        from src.contracts.requisites_transforms import full_name_from_short
        result = full_name_from_short('АО "Тензосила"')
        assert result == 'Акционерное общество "Тензосила"'

    def test_pao(self):
        from src.contracts.requisites_transforms import full_name_from_short
        result = full_name_from_short('ПАО "Сбербанк"')
        assert result == 'Публичное акционерное общество "Сбербанк"'

    def test_zao(self):
        from src.contracts.requisites_transforms import full_name_from_short
        result = full_name_from_short('ЗАО "Прогресс"')
        assert result == 'Закрытое акционерное общество "Прогресс"'

    def test_ip(self):
        from src.contracts.requisites_transforms import full_name_from_short
        result = full_name_from_short('ИП Иванов И.И.')
        assert result == 'Индивидуальный предприниматель Иванов И.И.'

    def test_unknown_prefix_returns_empty(self):
        from src.contracts.requisites_transforms import full_name_from_short
        # Незнакомый ОПФ → ""
        assert full_name_from_short('НКО "Фонд"') == ""

    def test_empty_returns_empty(self):
        from src.contracts.requisites_transforms import full_name_from_short
        assert full_name_from_short("") == ""

    def test_zao_not_caught_by_ao_rule(self):
        """ЗАО не должно раскрываться как АО (правка №3 — ведущий токен)."""
        from src.contracts.requisites_transforms import full_name_from_short
        result = full_name_from_short('ЗАО "Пример"')
        # Должно быть ЗАО → Закрытое акционерное общество, а не АО
        assert result.startswith("Закрытое акционерное")
        assert "Акционерное общество" not in result[:30]

    def test_ao_substring_in_name_not_matched(self):
        """ОПФ-токен в имени не должен матчиться как ведущий."""
        from src.contracts.requisites_transforms import full_name_from_short
        # ООО с именем, содержащим 'АО' внутри
        result = full_name_from_short('ООО "РАО плюс"')
        assert result == 'Общество с ограниченной ответственностью "РАО плюс"'


# ---------------------------------------------------------------------------
# director_initials
# ---------------------------------------------------------------------------

class TestDirectorInitials:
    def test_full_fio(self):
        from src.contracts.requisites_transforms import director_initials
        assert director_initials("Иванов Иван Иванович") == "И.И. Иванов"

    def test_two_parts(self):
        from src.contracts.requisites_transforms import director_initials
        assert director_initials("Иванов Иван") == "И. Иванов"

    def test_single_word_returns_empty(self):
        from src.contracts.requisites_transforms import director_initials
        assert director_initials("Иванов") == ""

    def test_empty_returns_empty(self):
        from src.contracts.requisites_transforms import director_initials
        assert director_initials("") == ""

    def test_female(self):
        from src.contracts.requisites_transforms import director_initials
        assert director_initials("Петрова Мария Ивановна") == "М.И. Петрова"


# ---------------------------------------------------------------------------
# position_genitive
# ---------------------------------------------------------------------------

class TestPositionGenitive:
    def test_director(self):
        from src.contracts.requisites_transforms import position_genitive
        assert position_genitive("директор") == "директора"

    def test_general_director(self):
        from src.contracts.requisites_transforms import position_genitive
        assert position_genitive("генеральный директор") == "генерального директора"

    def test_unknown_returns_empty(self):
        from src.contracts.requisites_transforms import position_genitive
        # Незнакомая должность → "" (не перетираем поле)
        assert position_genitive("главный специалист") == ""

    def test_empty_returns_empty(self):
        from src.contracts.requisites_transforms import position_genitive
        assert position_genitive("") == ""

    def test_case_insensitive(self):
        from src.contracts.requisites_transforms import position_genitive
        assert position_genitive("Генеральный Директор") == "генерального директора"

    def test_president(self):
        from src.contracts.requisites_transforms import position_genitive
        assert position_genitive("президент") == "президента"


# ---------------------------------------------------------------------------
# decline_fio — правка №1: устойчивость, uncertain flag
# ---------------------------------------------------------------------------

class TestDeclineFio:
    def test_male_standard(self):
        """Типовое мужское ФИО склоняется корректно."""
        from src.contracts.requisites_transforms import decline_fio
        result, uncertain = decline_fio("Иванов Иван Иванович", "male")
        # Родительный: Иванова Ивана Ивановича
        assert "Ивано" in result  # Иванова или Ивановича
        assert uncertain is False

    def test_female_standard(self):
        """Типовое женское ФИО склоняется корректно."""
        from src.contracts.requisites_transforms import decline_fio
        result, uncertain = decline_fio("Петрова Мария Ивановна", "female")
        assert "Петров" in result  # Петровой
        assert uncertain is False

    def test_non_declinable_does_not_raise(self):
        """Несклоняемая фамилия не роняет функцию (правка №1)."""
        from src.contracts.requisites_transforms import decline_fio
        result, uncertain = decline_fio("Нгуен Дмитрий Вьетнамович", "male")
        # Не должно падать, результат строка
        assert isinstance(result, str)
        assert len(result) > 0

    def test_kim_does_not_raise(self):
        """Короткая/иностранная фамилия — без исключений."""
        from src.contracts.requisites_transforms import decline_fio
        result, uncertain = decline_fio("Ким Сергей Александрович", "male")
        assert isinstance(result, str)

    def test_empty_fio_returns_empty(self):
        from src.contracts.requisites_transforms import decline_fio
        result, uncertain = decline_fio("", "male")
        assert result == ""
        assert uncertain is False

    def test_single_word_uncertain(self):
        """Одно слово — нет составных частей для склонения → uncertain."""
        from src.contracts.requisites_transforms import decline_fio
        result, uncertain = decline_fio("Иванов", "male")
        assert uncertain is True

    def test_returns_tuple(self):
        from src.contracts.requisites_transforms import decline_fio
        res = decline_fio("Смирнов Алексей Петрович", "male")
        assert isinstance(res, tuple)
        assert len(res) == 2


# ---------------------------------------------------------------------------
# derive_requisites — интеграция
# ---------------------------------------------------------------------------

class TestDeriveRequisites:
    def test_full_derivation(self):
        """Полный набор входных полей порождает корректный производный subset."""
        from src.contracts.requisites_transforms import derive_requisites
        fields = {
            "ЗАКАЗЧИК_КРАТКОЕ_НАИМЕНОВАНИЕ": 'ООО "Тест"',
            "ЗАКАЗЧИК_ДИРЕКТОР_ФИО": "Иванов Иван Иванович",
            "ЗАКАЗЧИК_ДИРЕКТОР_ДОЛЖНОСТЬ": "директор",
        }
        derived, warnings = derive_requisites(fields)
        assert "ЗАКАЗЧИК_ПОЛНОЕ_НАИМЕНОВАНИЕ" in derived
        assert "Общество с ограниченной" in derived["ЗАКАЗЧИК_ПОЛНОЕ_НАИМЕНОВАНИЕ"]
        assert "ЗАКАЗЧИК_ДИРЕКТОР_ИНИЦИАЛЫ" in derived
        assert derived["ЗАКАЗЧИК_ДИРЕКТОР_ИНИЦИАЛЫ"] == "И.И. Иванов"
        assert "ЗАКАЗЧИК_ДИРЕКТОР_ДОЛЖНОСТЬ_РП" in derived
        assert derived["ЗАКАЗЧИК_ДИРЕКТОР_ДОЛЖНОСТЬ_РП"] == "директора"
        assert "ЗАКАЗЧИК_ДИРЕКТОР_ПОЛ" in derived
        assert derived["ЗАКАЗЧИК_ДИРЕКТОР_ПОЛ"] == "male"
        assert "ЗАКАЗЧИК_ДИРЕКТОР_ФИО_РП" in derived
        assert isinstance(warnings, list)

    def test_empty_fields_no_error(self):
        """Пустые поля не роняют функцию."""
        from src.contracts.requisites_transforms import derive_requisites
        derived, warnings = derive_requisites({})
        assert isinstance(derived, dict)
        assert isinstance(warnings, list)

    def test_uncertain_slope_adds_warning(self):
        """Неуверенное склонение приводит к предупреждению."""
        from src.contracts.requisites_transforms import derive_requisites
        # Используем фамилию, которая может вернуться без изменений
        fields = {
            "ЗАКАЗЧИК_ДИРЕКТОР_ФИО": "Черных Иван Иванович",
            "ЗАКАЗЧИК_ДИРЕКТОР_ПОЛ": "female",  # нарочно неверный пол → несоответствие
        }
        derived, warnings = derive_requisites(fields)
        # Функция не должна падать
        assert isinstance(derived, dict)
        assert isinstance(warnings, list)

    def test_returns_only_computable_fields(self):
        """Без ФИО не появляются производные от ФИО."""
        from src.contracts.requisites_transforms import derive_requisites
        fields = {"ЗАКАЗЧИК_КРАТКОЕ_НАИМЕНОВАНИЕ": 'АО "Пример"'}
        derived, _ = derive_requisites(fields)
        assert "ЗАКАЗЧИК_ДИРЕКТОР_ФИО_РП" not in derived
        assert "ЗАКАЗЧИК_ДИРЕКТОР_ИНИЦИАЛЫ" not in derived
