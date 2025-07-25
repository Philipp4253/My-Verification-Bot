"""FSM хендлеры верификации медицинских работников."""

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.fsm.context import FSMContext
from aiogram.filters import Command, CommandStart, CommandObject

from bot.database.manager import DatabaseManager
from bot.database.models.verification_log import VerificationMethod
from bot.services.verification_service import VerificationService
from bot.states.verification import VerificationStates
from bot.utils.validators import (
    validate_full_name,
    validate_workplace,
    validate_website_url,
    validate_file_size,
    validate_file_type
)
from config.settings import settings
from loguru import logger


router = Router(name='verification')


@router.message(CommandStart(deep_link=True))
async def start_verification_with_params(
    message: Message,
    command: CommandObject,
    db_manager: DatabaseManager
):
    """Команда /start с параметрами - автоматическое начало верификации для группы."""
    args = command.args

    if args and args.startswith("verify_"):
        group_id = int(args.replace("verify_", ""))

        # Проверяем, что пользователь есть в базе
        user = await db_manager.users.get_by_id(message.from_user.id)
        if not user:
            await message.answer(
                "❌ <b>Доступ ограничен</b>\n\n"
                "Этот бот работает только с участниками медицинской группы.\n"
                "Сначала вступите в группу, затем начните верификацию.",
                parse_mode="HTML"
            )
            return

        # Проверяем, что группа существует и активна
        group = await db_manager.groups.get_by_id(group_id)
        if not group or not group.is_active:
            await message.answer(
                "❌ <b>Группа не найдена</b>\n\n"
                "Указанная группа не существует или неактивна.",
                parse_mode="HTML"
            )
            return

        # Проверяем верификацию пользователя в этой группе
        verification = await db_manager.user_group_verifications.get_by_user_and_group(message.from_user.id, group_id)
        if not verification:
            await message.answer(
                "❌ <b>Нет доступа к верификации</b>\n\n"
                "Вы не являетесь участником указанной группы.",
                parse_mode="HTML"
            )
            return

        if verification.verified:
            await message.answer(
                f"✅ <b>Вы уже верифицированы</b>\n\n"
                f"Ваш статус в группе \"{group.group_name}\" подтвержден.",
                parse_mode="HTML"
            )
            return

        if verification.attempts_count >= settings.max_verification_attempts:
            await message.answer(
                f"❌ <b>Превышен лимит попыток</b>\n\n"
                f"Вы исчерпали все попытки верификации для группы \"{group.group_name}\".\n"
                "Обратитесь к администратору.",
                parse_mode="HTML"
            )
            return

        # Автоматически показываем кнопку начала верификации для этой группы
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🩺 Начать верификацию", callback_data=f"start_verification:{group_id}")]
        ])

        remaining_attempts = settings.max_verification_attempts - verification.attempts_count

        await message.answer(
            f"🏥 <b>Верификация для группы \"{group.group_name}\"</b>\n\n"
            "Для участия в группе необходимо подтвердить ваш статус медицинского работника.\n\n"
            "📋 <b>Процесс верификации:</b>\n"
            "1️⃣ Укажите ваше ФИО\n"
            "2️⃣ Укажите место работы\n"
            "3️⃣ Выберите способ подтверждения:\n"
            "   • 🌐 Через сайт организации\n"
            "   • 📄 Через документ (диплом/сертификат)\n"
            "4️⃣ Получите подтверждение верификации\n\n"
            f"⚠️ <b>Попыток осталось:</b> {remaining_attempts}\n"
            f"⏰ <b>Время на верификацию:</b> {settings.format_verification_complete_timeout()}\n\n"
            "Готовы начать?",
            reply_markup=keyboard,
            parse_mode="HTML"
        )
        return

    # Обработка других параметров или fallback
    if args and args.startswith("verify_"):
        target_user_id = int(args.replace("verify_", ""))

        if message.from_user.id != target_user_id:
            return

    if message.from_user.id in settings.admin_user_ids:
        await message.answer(
            "👑 <b>Вы являетесь администратором бота</b>\n\n"
            "Используйте команду /admin для доступа к административной панели.",
            parse_mode="HTML"
        )
        return

    user = await db_manager.users.get_by_id(message.from_user.id)
    if not user:
        await message.answer(
            "❌ <b>Доступ ограничен</b>\n\n"
            "Этот бот работает только с участниками медицинской группы.\n"
            "Сначала вступите в группу, затем начните верификацию.",
            parse_mode="HTML"
        )
        return
    user_verifications = await db_manager.user_group_verifications.get_user_verifications(message.from_user.id)

    unverified_groups = []
    for verification in user_verifications:
        if not verification.verified and verification.attempts_count < settings.max_verification_attempts:
            group = await db_manager.groups.get_by_id(verification.group_id)
            if group and group.is_active:
                unverified_groups.append((group, verification))

    if not unverified_groups:
        await message.answer(
            "ℹ️ <b>Нет групп для верификации</b>\n\n"
            "Вы либо уже верифицированы во всех группах, либо превысили лимит попыток.\n"
            "Обратитесь к администратору для получения помощи."
        )
        return

    if len(unverified_groups) == 1:
        group, verification = unverified_groups[0]
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🩺 Начать верификацию", callback_data=f"start_verification:{group.group_id}")]
        ])

        remaining_attempts = settings.max_verification_attempts - verification.attempts_count

        await message.answer(
            f"🏥 <b>Верификация для группы \"{group.group_name}\"</b>\n\n"
            "Для участия в группе необходимо подтвердить ваш статус медицинского работника.\n\n"
            "📋 <b>Процесс верификации:</b>\n"
            "1️⃣ Укажите ваше ФИО\n"
            "2️⃣ Укажите место работы\n"
            "3️⃣ Выберите способ подтверждения:\n"
            "   • 🌐 Через сайт организации\n"
            "   • 📄 Через документ (диплом/сертификат)\n"
            "4️⃣ Получите подтверждение верификации\n\n"
            f"⚠️ <b>Попыток осталось:</b> {remaining_attempts}\n"
            f"⏰ <b>Время на верификацию:</b> {settings.format_verification_complete_timeout()}\n\n"
            "Готовы начать?",
            reply_markup=keyboard
        )
    else:
        keyboard_buttons = []
        for group, verification in unverified_groups:
            remaining_attempts = settings.max_verification_attempts - verification.attempts_count
            button_text = f"🩺 {group.group_name} ({remaining_attempts} попыток)"
            keyboard_buttons.append([InlineKeyboardButton(
                text=button_text,
                callback_data=f"start_verification:{group.group_id}"
            )])

        keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)

        await message.answer(
            "🏥 <b>Выберите группу для верификации</b>\n\n"
            "У вас есть незавершенная верификация в следующих группах:\n\n"
            "Выберите группу, в которой хотите пройти верификацию:",
            reply_markup=keyboard
        )


@router.message(Command("start"))
async def start_verification_command(
    message: Message,
    db_manager: DatabaseManager
):
    """Команда /start без параметров."""
    if message.chat.type in ['group', 'supergroup']:
        if message.from_user.id in settings.admin_user_ids:
            return

        try:
            chat_member = await message.bot.get_chat_member(message.chat.id, message.from_user.id)
            if chat_member.status in ['administrator', 'creator']:
                return
        except Exception:
            pass

        return

    if message.from_user.id in settings.admin_user_ids:
        await message.answer(
            "👑 <b>Вы являетесь администратором бота</b>\n\n"
            "Используйте команду /admin для доступа к административной панели.",
            parse_mode="HTML"
        )
        return

    user = await db_manager.users.get_by_id(message.from_user.id)
    if not user:
        await message.answer(
            "❌ <b>Доступ ограничен</b>\n\n"
            "Этот бот работает только с участниками медицинской группы.\n"
            "Сначала вступите в группу, затем начните верификацию.",
            parse_mode="HTML"
        )
        return

    user_verifications = await db_manager.user_group_verifications.get_user_verifications(message.from_user.id)

    unverified_groups = []
    for verification in user_verifications:
        if not verification.verified and verification.attempts_count < settings.max_verification_attempts:
            group = await db_manager.groups.get_by_id(verification.group_id)
            if group and group.is_active:
                unverified_groups.append((group, verification))

    if not unverified_groups:
        await message.answer(
            "ℹ️ <b>Нет групп для верификации</b>\n\n"
            "Вы либо уже верифицированы во всех группах, либо превысили лимит попыток.\n"
            "Обратитесь к администратору для получения помощи."
        )
        return

    if len(unverified_groups) == 1:
        group, verification = unverified_groups[0]
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🩺 Начать верификацию", callback_data=f"start_verification:{group.group_id}")]
        ])

        remaining_attempts = settings.max_verification_attempts - verification.attempts_count

        await message.answer(
            f"🏥 <b>Верификация для группы \"{group.group_name}\"</b>\n\n"
            "Для участия в группе необходимо подтвердить ваш статус медицинского работника.\n\n"
            "📋 <b>Процесс верификации:</b>\n"
            "1️⃣ Укажите ваше ФИО\n"
            "2️⃣ Укажите место работы\n"
            "3️⃣ Выберите способ подтверждения:\n"
            "   • 🌐 Через сайт организации\n"
            "   • 📄 Через документ (диплом/сертификат)\n"
            "4️⃣ Получите подтверждение верификации\n\n"
            f"⚠️ <b>Попыток осталось:</b> {remaining_attempts}\n"
            f"⏰ <b>Время на верификацию:</b> {settings.format_verification_complete_timeout()}\n\n"
            "Готовы начать?",
            reply_markup=keyboard
        )
    else:
        keyboard_buttons = []
        for group, verification in unverified_groups:
            remaining_attempts = settings.max_verification_attempts - verification.attempts_count
            button_text = f"🩺 {group.group_name} ({remaining_attempts} попыток)"
            keyboard_buttons.append([InlineKeyboardButton(
                text=button_text,
                callback_data=f"start_verification:{group.group_id}"
            )])

        keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)

        await message.answer(
            "🏥 <b>Выберите группу для верификации</b>\n\n"
            "У вас есть незавершенная верификация в следующих группах:\n\n"
            "Выберите группу, в которой хотите пройти верификацию:",
            reply_markup=keyboard
        )


@router.callback_query(F.data.startswith("start_verification"))
async def start_verification_callback(
    callback: CallbackQuery,
    state: FSMContext,
    db_manager: DatabaseManager
):
    """Начало процесса верификации."""
    await callback.answer()

    callback_parts = callback.data.split(":")
    if len(callback_parts) == 2 and callback_parts[1]:
        group_id = int(callback_parts[1])
        await state.update_data(group_id=group_id)
        logger.info(f"Начата верификация пользователя {callback.from_user.id} для группы {group_id}")
    else:
        logger.warning(f"Неправильный формат callback_data: {callback.data}")
        await callback.message.edit_text("❌ Ошибка: не удалось определить группу для верификации.")
        return

    await db_manager.user_group_verifications.get_or_create(callback.from_user.id, group_id)
    await db_manager.user_group_verifications.increment_attempts(callback.from_user.id, group_id)
    await db_manager.user_group_verifications.update_state(
        callback.from_user.id, group_id, VerificationStates.entering_full_name.state
    )

    await callback.message.edit_text(
        "👤 <b>Шаг 1/4: Введите ваше ФИО</b>\n\n"
        "Укажите ваше полное ФИО (Фамилия Имя Отчество).\n"
        "Это должно точно соответствовать данным в ваших документах.\n\n"
        "📝 <b>Пример:</b> Иванов Иван Иванович"
    )

    await state.set_state(VerificationStates.entering_full_name)


@router.message(VerificationStates.entering_full_name)
async def process_full_name(message: Message, state: FSMContext, db_manager: DatabaseManager):
    """Обработка ввода ФИО."""

    # Проверяем тип чата - верификация должна происходить только в личных сообщениях
    if message.chat.type in ["group", "supergroup"]:
        try:
            # Удаляем сообщение из группы
            await message.delete()
            logger.info(f"Удалено сообщение пользователя {message.from_user.id} из группы во время верификации")

            # Отправляем напоминание в личку
            await message.bot.send_message(
                message.from_user.id,
                "⚠️ <b>Верификация происходит в личных сообщениях</b>\n\n"
                "Пожалуйста, введите ваше полное ФИО здесь, в личном чате с ботом."
            )
        except Exception as e:
            logger.error(f"Ошибка при обработке сообщения из группы во время верификации: {e}")
        return

    if not message.text:
        try:
            await message.bot.send_message(
                message.from_user.id,
                "❌ <b>Некорректное сообщение</b>\n\n"
                "Пожалуйста, введите ваше полное ФИО текстом:"
            )
        except Exception as e:
            logger.error(f"Не удалось отправить сообщение пользователю {message.from_user.id}: {e}")
            await state.clear()
        return

    full_name = message.text.strip()

    is_valid, error_message = await validate_full_name(full_name)
    if not is_valid:
        try:
            await message.bot.send_message(
                message.from_user.id,
                f"❌ <b>Ошибка валидации:</b> {error_message}\n\n"
                "Попробуйте еще раз. Введите ваше полное ФИО:"
            )
        except Exception as e:
            logger.error(f"Не удалось отправить сообщение пользователю {message.from_user.id}: {e}")
            await state.clear()
        return

    await state.update_data(full_name=full_name)
    await db_manager.users.update_step(message.from_user.id, VerificationStates.entering_workplace.state)

    try:
        await message.bot.send_message(
            message.from_user.id,
            "🏥 <b>Шаг 2/4: Укажите место работы</b>\n\n"
            "Введите полное название медицинской организации, где вы работаете.\n\n"
            "📝 <b>Примеры:</b>\n"
            "• ГБУЗ \"Городская больница №1\"\n"
            "• ООО \"Медицинский центр Здоровье\"\n"
            "• ФГБУ \"НИИ кардиологии\""
        )
    except Exception as e:
        logger.error(f"Не удалось отправить сообщение пользователю {message.from_user.id}: {e}")
        await state.clear()
        return

    await state.set_state(VerificationStates.entering_workplace)


@router.message(VerificationStates.entering_workplace)
async def process_workplace(message: Message, state: FSMContext, db_manager: DatabaseManager):
    """Обработка ввода места работы."""

    # Проверяем тип чата - верификация должна происходить только в личных сообщениях
    if message.chat.type in ["group", "supergroup"]:
        try:
            # Удаляем сообщение из группы
            await message.delete()
            logger.info(f"Удалено сообщение пользователя {message.from_user.id} из группы во время верификации")

            # Отправляем напоминание в личку
            await message.bot.send_message(
                message.from_user.id,
                "⚠️ <b>Верификация происходит в личных сообщениях</b>\n\n"
                "Пожалуйста, введите название медицинской организации здесь, в личном чате с ботом."
            )
        except Exception as e:
            logger.error(f"Ошибка при обработке сообщения из группы во время верификации: {e}")
        return

    if not message.text:
        try:
            await message.bot.send_message(
                message.from_user.id,
                "❌ <b>Некорректное сообщение</b>\n\n"
                "Пожалуйста, введите название медицинской организации текстом:"
            )
        except Exception as e:
            logger.error(f"Не удалось отправить сообщение пользователю {message.from_user.id}: {e}")
            await state.clear()
        return

    workplace = message.text.strip()

    is_valid, error_message = await validate_workplace(workplace)
    if not is_valid:
        try:
            await message.bot.send_message(
                message.from_user.id,
                f"❌ <b>Ошибка валидации:</b> {error_message}\n\n"
                "Попробуйте еще раз. Введите название медицинской организации:"
            )
        except Exception as e:
            logger.error(f"Не удалось отправить сообщение пользователю {message.from_user.id}: {e}")
            await state.clear()
        return

    await state.update_data(workplace=workplace)
    await db_manager.users.update_step(message.from_user.id, VerificationStates.choosing_verification_method.state)

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="🌐 Есть сайт организации",
            callback_data="method_website"
        )],
        [InlineKeyboardButton(
            text="📄 Нет сайта, загрузить документ",
            callback_data="method_document"
        )]
    ])

    try:
        await message.bot.send_message(
            message.from_user.id,
            "🔍 <b>Шаг 3/4: Выберите способ верификации</b>\n\n"
            "Выберите наиболее подходящий способ подтверждения вашего статуса врача:\n\n"
            "🌐 <b>Через сайт организации</b> (рекомендуется)\n"
            "• Быстрая проверка (1-2 минуты)\n"
            "• Высокая точность\n"
            "• Подходит если ваша организация имеет официальный сайт\n\n"
            "📄 <b>Через документ</b>\n"
            "• Загрузка диплома/сертификата\n"
            "• Анализ документа (2-3 минуты)\n"
            "• Подходит если у организации нет сайта",
            reply_markup=keyboard
        )
    except Exception as e:
        logger.error(f"Не удалось отправить сообщение пользователю {message.from_user.id}: {e}")
        await state.clear()
        return

    await state.set_state(VerificationStates.choosing_verification_method)


@router.callback_query(F.data == "method_website")
async def choose_website_method(callback: CallbackQuery, state: FSMContext, db_manager: DatabaseManager):
    """Выбор метода верификации через сайт."""
    await callback.answer()

    await state.update_data(method=VerificationMethod.WEBSITE)
    await db_manager.users.update_step(callback.from_user.id, VerificationStates.entering_website_url.state)

    await callback.message.edit_text(
        "🌐 <b>Шаг 4/4: Укажите сайт организации</b>\n\n"
        "Введите URL официального сайта вашей медицинской организации.\n\n"
        "📝 <b>Примеры:</b>\n"
        "• hospital1.ru\n"
        "• medcenter-health.com\n"
        "• https://cardio-institute.org\n\n"
        "💡 <b>Подсказка:</b> Можно вводить и с https://, и без протокола"
    )

    await state.set_state(VerificationStates.entering_website_url)


@router.callback_query(F.data == "method_document")
async def choose_document_method(callback: CallbackQuery, state: FSMContext, db_manager: DatabaseManager):
    """Выбор метода верификации через документ."""
    await callback.answer()

    await state.update_data(method=VerificationMethod.DOCUMENT)
    await db_manager.users.update_step(callback.from_user.id, VerificationStates.uploading_document.state)

    await callback.message.edit_text(
        "📄 <b>Шаг 4/4: Загрузите документ</b>\n\n"
        "Загрузите фотографию или скан одного из документов:\n\n"
        "✅ <b>Подходящие документы:</b>\n"
        "• Диплом о медицинском образовании\n"
        "• Сертификат специалиста\n"
        "• Справка с места работы\n"
        "• Удостоверение врача\n\n"
        "📋 <b>Требования:</b>\n"
        "• Формат: JPEG, PNG или PDF\n"
        "• Размер: до 20 МБ\n"
        "• Текст должен быть четко читаемым\n"
        "• Документ должен содержать ваше ФИО\n\n"
        "📤 Отправьте документ как фото или файл:"
    )

    await state.set_state(VerificationStates.uploading_document)


@router.message(VerificationStates.entering_website_url)
async def process_website_url(message: Message, state: FSMContext, db_manager: DatabaseManager):
    """Обработка ввода URL сайта."""

    # Проверяем тип чата - верификация должна происходить только в личных сообщениях
    if message.chat.type in ["group", "supergroup"]:
        try:
            # Удаляем сообщение из группы
            await message.delete()
            logger.info(f"Удалено сообщение пользователя {message.from_user.id} из группы во время верификации")

            # Отправляем напоминание в личку
            await message.bot.send_message(
                message.from_user.id,
                "⚠️ <b>Верификация происходит в личных сообщениях</b>\n\n"
                "Пожалуйста, введите URL сайта здесь, в личном чате с ботом."
            )
        except Exception as e:
            logger.error(f"Ошибка при обработке сообщения из группы во время верификации: {e}")
        return

    if not message.text:
        try:
            await message.bot.send_message(
                message.from_user.id,
                "❌ <b>Некорректное сообщение</b>\n\n"
                "Пожалуйста, введите URL сайта текстом:"
            )
        except Exception as e:
            logger.error(f"Не удалось отправить сообщение пользователю {message.from_user.id}: {e}")
            await state.clear()
        return

    url = message.text.strip()

    is_valid, validated_url_or_error = await validate_website_url(url)
    if not is_valid:
        try:
            await message.bot.send_message(
                message.from_user.id,
                f"❌ <b>Ошибка валидации URL:</b> {validated_url_or_error}\n\n"
                "Попробуйте еще раз. Введите корректный URL сайта:"
            )
        except Exception as e:
            logger.error(f"Не удалось отправить сообщение пользователю {message.from_user.id}: {e}")
            await state.clear()
        return

    await state.update_data(website_url=validated_url_or_error)
    await db_manager.users.update_step(message.from_user.id, VerificationStates.processing_verification.state)

    verification_service = VerificationService(db_manager)
    await verification_service.start_verification_process(message, state)


@router.message(VerificationStates.uploading_document, F.photo)
async def process_document_photo(message: Message, state: FSMContext, db_manager: DatabaseManager):
    """Обработка загруженной фотографии документа."""

    # Проверяем тип чата - верификация должна происходить только в личных сообщениях
    if message.chat.type in ["group", "supergroup"]:
        try:
            # Удаляем сообщение из группы
            await message.delete()
            logger.info(f"Удалено сообщение пользователя {message.from_user.id} из группы во время верификации")

            # Отправляем напоминание в личку
            await message.bot.send_message(
                message.from_user.id,
                "⚠️ <b>Верификация происходит в личных сообщениях</b>\n\n"
                "Пожалуйста, загрузите документ здесь, в личном чате с ботом."
            )
        except Exception as e:
            logger.error(f"Ошибка при обработке сообщения из группы во время верификации: {e}")
        return

    photo = message.photo[-1]

    is_valid, error_message = await validate_file_size(
        photo.file_size, settings.max_file_size_bytes, settings.max_file_size_mb
    )
    if not is_valid:
        try:
            await message.bot.send_message(
                message.from_user.id,
                f"❌ <b>{error_message}</b>"
            )
        except Exception as e:
            logger.error(f"Не удалось отправить сообщение пользователю {message.from_user.id}: {e}")
            await state.clear()
        return

    await state.update_data(
        document_file_id=photo.file_id,
        document_type="photo"
    )
    await db_manager.users.update_step(message.from_user.id, VerificationStates.processing_verification.state)

    verification_service = VerificationService(db_manager)
    await verification_service.start_verification_process(message, state)


@router.message(VerificationStates.uploading_document, F.document)
async def process_document_file(message: Message, state: FSMContext, db_manager: DatabaseManager):
    """Обработка загруженного файла документа."""

    # Проверяем тип чата - верификация должна происходить только в личных сообщениях
    if message.chat.type in ["group", "supergroup"]:
        try:
            # Удаляем сообщение из группы
            await message.delete()
            logger.info(f"Удалено сообщение пользователя {message.from_user.id} из группы во время верификации")

            # Отправляем напоминание в личку
            await message.bot.send_message(
                message.from_user.id,
                "⚠️ <b>Верификация происходит в личных сообщениях</b>\n\n"
                "Пожалуйста, загрузите документ здесь, в личном чате с ботом."
            )
        except Exception as e:
            logger.error(f"Ошибка при обработке сообщения из группы во время верификации: {e}")
        return

    document = message.document

    allowed_types = settings.allowed_file_types
    is_valid, error_message = await validate_file_type(document.mime_type, allowed_types)
    if not is_valid:
        try:
            await message.bot.send_message(
                message.from_user.id,
                f"❌ <b>{error_message}</b>"
            )
        except Exception as e:
            logger.error(f"Не удалось отправить сообщение пользователю {message.from_user.id}: {e}")
            await state.clear()
        return

    is_valid, error_message = await validate_file_size(
        document.file_size, settings.max_file_size_bytes, settings.max_file_size_mb
    )
    if not is_valid:
        try:
            await message.bot.send_message(
                message.from_user.id,
                f"❌ <b>{error_message}</b>"
            )
        except Exception as e:
            logger.error(f"Не удалось отправить сообщение пользователю {message.from_user.id}: {e}")
            await state.clear()
        return

    await state.update_data(
        document_file_id=document.file_id,
        document_type="document",
        document_mime_type=document.mime_type
    )
    await db_manager.users.update_step(message.from_user.id, VerificationStates.processing_verification.state)

    verification_service = VerificationService(db_manager)
    await verification_service.start_verification_process(message, state)


@router.message(VerificationStates.uploading_document)
async def process_invalid_document(message: Message):
    """Обработка некорректного типа сообщения при загрузке документа."""

    # Проверяем тип чата - верификация должна происходить только в личных сообщениях
    if message.chat.type in ["group", "supergroup"]:
        try:
            # Удаляем сообщение из группы
            await message.delete()
            logger.info(f"Удалено сообщение пользователя {message.from_user.id} из группы во время верификации")

            # Отправляем напоминание в личку
            await message.bot.send_message(
                message.from_user.id,
                "⚠️ <b>Верификация происходит в личных сообщениях</b>\n\n"
                "Пожалуйста, загрузите документ здесь, в личном чате с ботом."
            )
        except Exception as e:
            logger.error(f"Ошибка при обработке сообщения из группы во время верификации: {e}")
        return

    try:
        await message.bot.send_message(
            message.from_user.id,
            "❌ <b>Некорректный тип сообщения</b>\n\n"
            "Пожалуйста, отправьте документ как:\n"
            "• Фотографию (JPEG, PNG)\n"
            "• Файл (PDF)\n\n"
            "Текстовые сообщения не принимаются на этом этапе."
        )
    except Exception as e:
        logger.error(f"Не удалось отправить сообщение пользователю {message.from_user.id}: {e}")


@router.callback_query(F.data == "view_profile")
async def view_profile_callback(callback: CallbackQuery, db_manager: DatabaseManager):
    """Просмотр профиля пользователя."""
    await callback.answer()

    verification_service = VerificationService(db_manager)
    profile_text = await verification_service.get_user_profile_text(callback.from_user.id)

    await callback.message.edit_text(profile_text)


@router.message(F.chat.type == "private")
async def block_unknown_users(message: Message, db_manager: DatabaseManager):
    """Блокировка всех сообщений от пользователей после верификации."""
    user_id = message.from_user.id

    if user_id in settings.admin_user_ids:
        return

    user = await db_manager.users.get_by_id(user_id)
    if not user:
        return

    if user.verified:
        return

    if not user.state or user.state in ["left_group", "verification_timeout"]:
        return


verification_router = router
