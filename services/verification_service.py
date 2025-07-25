"""Сервис верификации медицинских работников."""

from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from loguru import logger
from typing import Dict, Any

from bot.database.manager import DatabaseManager
from bot.services.openai_service import OpenAIService
from bot.states.verification import VerificationStates
from config.settings import settings
import re
from bot.database.models.verification_log import VerificationMethod, VerificationLog


class VerificationService:
    """Сервис для обработки верификации пользователей."""

    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager
        self.openai_service = OpenAIService()

    def _normalize_name(self, name: str) -> str:
        """Нормализация ФИО для сравнения."""
        if not name:
            return ""
        normalized = re.sub(r'\s+', ' ', name.strip().lower())
        normalized = normalized.replace('.', '')
        return normalized

    def _compare_full_names(self, input_name: str, found_name: str) -> bool:
        """Строгое сравнение ФИО."""
        if not input_name or not found_name:
            return False

        input_normalized = self._normalize_name(input_name)
        found_normalized = self._normalize_name(found_name)

        logger.info("🔍 Сравнение ФИО:")
        logger.info(f"   Введено: '{input_name}' → '{input_normalized}'")
        logger.info(f"   Найдено: '{found_name}' → '{found_normalized}'")

        exact_match = input_normalized == found_normalized

        if exact_match:
            logger.info("✅ ФИО совпадают точно")
            return True
        else:
            logger.warning("❌ ФИО НЕ совпадают")
            return False

    async def start_verification_process(self, message: Message, state: FSMContext):
        """Запуск процесса верификации через OpenAI."""
        await message.answer(
            "⏳ <b>Обработка верификации...</b>\n\n"
            "Пожалуйста, подождите. Это может занять 1-3 минуты."
        )

        await state.set_state(VerificationStates.processing_verification)

        data = await state.get_data()
        user_id = message.from_user.id

        try:
            if data["method"] == VerificationMethod.WEBSITE:
                result = await self.openai_service.verify_website(
                    full_name=data["full_name"],
                    workplace=data["workplace"],
                    website_url=data["website_url"]
                )
            else:
                result = await self.openai_service.verify_document(
                    full_name=data["full_name"],
                    workplace=data["workplace"],
                    file_id=data["document_file_id"]
                )

            log = VerificationLog(
                user_id=user_id,
                method=data["method"],
                full_name=data["full_name"],
                workplace=data["workplace"],
                website_url=data.get("website_url"),
                details=f"{data['full_name']} - {data['workplace']}",
                openai_response=str(result),
                result="processing"
            )
            await self.db_manager.logs.add(log)

            is_verified = self._analyze_openai_json_response(result, data["full_name"])

            if is_verified:
                await self._handle_successful_verification(message, state, data)
            else:
                await self._handle_failed_verification(message, state)

        except Exception as e:
            logger.error(f"Ошибка при верификации пользователя {user_id}: {e}")

            log = VerificationLog(
                user_id=user_id,
                method=data.get("method"),
                full_name=data.get("full_name"),
                workplace=data.get("workplace"),
                website_url=data.get("website_url"),
                details=f"{data.get('full_name', 'N/A')} - {data.get('workplace', 'N/A')}",
                result="error",
                openai_response=f"Ошибка: {str(e)}"
            )
            await self.db_manager.logs.add(log)

            try:
                await message.bot.send_message(
                    message.from_user.id,
                    "❌ <b>Ошибка при обработке верификации</b>\n\n"
                    "Произошла техническая ошибка. Попробуйте еще раз позже или обратитесь к администратору."
                )
            except Exception as send_error:
                logger.error(f"Не удалось отправить сообщение об ошибке пользователю {user_id}: {send_error}")
            await state.clear()

    def _analyze_openai_json_response(self, result: Dict[str, Any], input_full_name: str) -> bool:
        """Анализ JSON ответа OpenAI для определения результата верификации."""
        if not result or not isinstance(result, dict):
            logger.error("❌ Некорректный JSON ответ от OpenAI")
            return False

        found = result.get("found", False)
        confidence = result.get("confidence", "low")
        explanation = result.get("explanation", "Нет объяснения")
        is_medical_document = result.get("is_medical_document", False)
        medical_indicators = result.get("medical_indicators", [])
        issuing_organization = result.get("issuing_organization", "Не указана")
        document_type = result.get("document_type", "")
        found_name = result.get("found_name", "")

        logger.info("=" * 60)
        logger.info("🎯 АНАЛИЗ РЕШЕНИЯ О ВЕРИФИКАЦИИ")
        logger.info("=" * 60)
        logger.info(f"✅ Найдено: {found}")
        logger.info(f"🎚️ Уверенность: {confidence}")
        logger.info(f"📄 Тип документа: {document_type}")
        logger.info(f"👤 Найденное ФИО: {found_name}")
        logger.info(f"🏥 Является медицинским документом: {is_medical_document}")
        logger.info(f"🔬 Медицинские признаки: {medical_indicators}")
        logger.info(f"🏢 Выдавшая организация: {issuing_organization}")
        logger.info(f"💬 Пояснение: {explanation}")
        logger.info("-" * 60)

        is_website_verification = "sources" in result or not document_type
        is_document_verification = document_type and "sources" not in result

        logger.info(f"🔍 Тип проверки: {'Веб-сайт' if is_website_verification else 'Документ'}")

        if is_document_verification:
            if not is_medical_document:
                logger.info("❌ РЕШЕНИЕ: ОТКЛОНЕНО")
                logger.info("Причина: документ не является медицинским")
                logger.info("=" * 60)
                return False

            if not medical_indicators or len(medical_indicators) == 0:
                logger.info("❌ РЕШЕНИЕ: ОТКЛОНЕНО")
                logger.info("Причина: отсутствуют медицинские признаки в документе")
                logger.info("=" * 60)
                return False

        if found and found_name:
            names_match = self._compare_full_names(input_full_name, found_name)
            if not names_match:
                logger.info("❌ РЕШЕНИЕ: ОТКЛОНЕНО")
                logger.info("Причина: ФИО не совпадают точно")
                logger.info("=" * 60)
                return False

        if found and confidence in ["high", "medium"]:
            logger.info("✅ РЕШЕНИЕ: ОДОБРЕНО")
            logger.info("=" * 60)
            return True
        else:
            logger.info("❌ РЕШЕНИЕ: ОТКЛОНЕНО")
            if found and confidence == "low":
                logger.warning("Причина: низкая уверенность")
            elif not found:
                logger.info("Причина: ФИО не найдено")
            logger.info("=" * 60)
            return False

    async def _handle_successful_verification(
        self,
        message: Message,
        state: FSMContext,
        data: dict
    ):
        """Обработка успешной верификации."""
        user_id = message.from_user.id

        state_data = await state.get_data()
        group_id = state_data.get('group_id')

        if not group_id:
            logger.error(f"Не найден group_id в FSM state для пользователя {user_id}")
            try:
                await message.bot.send_message(
                    message.from_user.id,
                    "❌ Ошибка: не удалось определить группу для верификации."
                )
            except Exception as e:
                logger.error(f"Не удалось отправить сообщение пользователю {user_id}: {e}")
            return

        await self.db_manager.user_group_verifications.update_verified_status(user_id, group_id, True, "manual")

        # Сбрасываем флаг requires_verification после успешной верификации
        await self.db_manager.user_group_verifications.update_requires_verification(user_id, group_id, False)
        
        # Сбрасываем счетчик сообщений после успешной верификации
        await self.db_manager.message_counts.reset_count(user_id, group_id)

        await self.db_manager.logs.update_verification_result(user_id, "success")
        await self.db_manager.user_group_verifications.update_state(user_id, group_id, None)

        logger.debug(f"✅ Пользователь {user_id} верифицирован в группе {group_id}, кэш обновится автоматически")

        success_message = "🎉 <b>Верификация успешно завершена!</b>"

        try:
            await message.bot.send_message(message.from_user.id, success_message)
        except Exception as e:
            logger.error(f"Не удалось отправить сообщение о успешной верификации пользователю {user_id}: {e}")

        try:
            from bot.handlers.group_events import delete_verification_notice
            await delete_verification_notice(user_id)
        except Exception as e:
            logger.debug(f"Не удалось удалить сообщение с предупреждением для {user_id}: {e}")

        await state.clear()
        logger.info(
            f"Пользователь {user_id} успешно верифицирован в группе {group_id}: {data['full_name']} - {data['workplace']}")

    async def _handle_failed_verification(
        self,
        message: Message,
        state: FSMContext
    ):
        """Обработка неудачной верификации."""
        user_id = message.from_user.id

        state_data = await state.get_data()
        group_id = state_data.get('group_id')

        await self.db_manager.logs.update_verification_result(user_id, "failed")

        if group_id:
            await self.db_manager.user_group_verifications.update_state(user_id, group_id, None)
            verification = await self.db_manager.user_group_verifications.get_by_user_and_group(user_id, group_id)
            remaining_attempts = settings.max_verification_attempts - verification.attempts_count if verification else 0
        else:
            await self.db_manager.users.update_step(user_id, None)
            user = await self.db_manager.users.get_by_id(user_id)
            remaining_attempts = settings.max_verification_attempts - user.attempts_count if user else 0

        failure_message = "❌ <b>Верификация не пройдена</b>"

        if remaining_attempts > 0:
            failure_message += "\n\n🔄 Используйте команду /start для новой попытки"

        try:
            await message.bot.send_message(message.from_user.id, failure_message)
        except Exception as e:
            logger.error(f"Не удалось отправить сообщение о неудачной верификации пользователю {user_id}: {e}")

        await state.clear()

        group_info = f" в группе {group_id}" if group_id else ""
        logger.info(
            f"Верификация пользователя {user_id}{group_info} не пройдена. Попыток осталось: {remaining_attempts}")

    async def get_user_profile_text(self, user_id: int) -> str:
        """Получение текста профиля пользователя (только статус верификации)."""
        user = await self.db_manager.users.get_by_id(user_id)
        if not user:
            return "❌ Пользователь не найден"

        status_emoji = "✅" if user.verified else "❌"
        status_text = "Верифицирован" if user.verified else "Не верифицирован"

        profile_text = (
            f"👤 <b>Ваш профиль</b>\n\n"
            f"🆔 <b>ID:</b> {user.user_id}\n"
            f"{status_emoji} <b>Статус:</b> {status_text}\n"
        )

        if user.verified and user.verified_at:
            profile_text += f"📅 <b>Дата верификации:</b> {user.verified_at.strftime('%d.%m.%Y %H:%M')}\n"

        if user.created_at:
            profile_text += f"📅 <b>Регистрация:</b> {user.created_at.strftime('%d.%m.%Y %H:%M')}\n"

        profile_text += f"🔢 <b>Попыток верификации:</b> {user.attempts_count}\n"

        profile_text += (
            "\n<i>ℹ️ Согласно политике конфиденциальности, "
            "персональные данные не сохраняются в профиле.</i>"
        )

        return profile_text
