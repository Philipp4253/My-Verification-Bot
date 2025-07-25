"""Валидаторы для данных верификации."""


async def validate_full_name(full_name: str) -> tuple[bool, str]:
    """Валидация ФИО пользователя."""
    if not full_name or len(full_name.strip()) < 3:
        return False, "ФИО должно содержать минимум 3 символа"

    if len(full_name) > 100:
        return False, "ФИО слишком длинное (максимум 100 символов)"

    words = full_name.strip().split()
    if len(words) < 2 or len(words) > 4:
        return False, "ФИО должно содержать 2-4 слова (Фамилия Имя Отчество)"

    for word in words:
        if not all(c.isalpha() or c == '-' for c in word):
            return False, "ФИО должно содержать только буквы и дефисы"

    return True, ""


async def validate_workplace(workplace: str) -> tuple[bool, str]:
    """Валидация места работы."""
    if not workplace or len(workplace.strip()) < 3:
        return False, "Место работы должно содержать минимум 3 символа"

    if len(workplace) > 200:
        return False, "Название места работы слишком длинное (максимум 200 символов)"

    return True, ""


async def validate_website_url(url: str) -> tuple[bool, str]:
    """Валидация URL сайта."""
    if not url or len(url.strip()) < 5:
        return False, "URL слишком короткий"

    url = url.strip().lower()

    if not url.startswith(('http://', 'https://')):
        url = 'https://' + url

    if not ('.' in url and len(url) > 10):
        return False, "Некорректный формат URL"

    return True, url


async def validate_file_size(file_size: int, max_size_bytes: int, max_size_mb: int) -> tuple[bool, str]:
    """Валидация размера файла."""
    if file_size > max_size_bytes:
        return False, (
            f"Файл слишком большой\n\n"
            f"Размер файла: {file_size / 1024 / 1024:.1f} МБ\n"
            f"Максимальный размер: {max_size_mb} МБ\n\n"
            "Попробуйте загрузить файл меньшего размера или сжать изображение."
        )
    return True, ""


async def validate_file_type(mime_type: str, allowed_types: list[str]) -> tuple[bool, str]:
    """Валидация типа файла."""
    if mime_type not in allowed_types:
        return False, (
            f"Неподдерживаемый тип файла\n\n"
            f"Тип файла: {mime_type}\n"
            f"Разрешенные типы: {', '.join(allowed_types)}\n\n"
            "Загрузите файл в формате JPEG, PNG или PDF."
        )
    return True, ""
