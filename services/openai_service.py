"""Сервис интеграции с OpenAI для верификации врачей."""
import base64
import json
from typing import Optional, Tuple, Dict, Any
from openai import AsyncOpenAI
from loguru import logger

from config.settings import settings


class OpenAIService:
    """Сервис для взаимодействия с OpenAI API."""

    def __init__(self):
        self.client = AsyncOpenAI(api_key=settings.openai_api_key)
        self.model = settings.openai_model

    async def verify_website(self, full_name: str, workplace: str, website_url: str) -> Dict[str, Any]:
        """
        Проверка врача на сайте с использованием веб-поиска.

        Args:
            full_name: Полное имя врача
            workplace: Место работы врача
            website_url: URL сайта медицинской организации

        Returns:
            Словарь с результатами верификации
        """
        try:
            prompt = (
                f"Проверь, работает ли врач {full_name} в медицинской организации {workplace}. "
                f"Найди информацию на сайте {website_url} или других официальных источниках. "
                f"Верни результат в JSON формате."
            )

            logger.info(f"Проверка через web search: {full_name} в {workplace} на {website_url}")

            response = await self.client.responses.create(
                model=self.model,
                tools=[{"type": "web_search_preview"}],
                text={
                    "format": {
                        "type": "json_schema",
                        "name": "verification_result",
                        "schema": {
                            "type": "object",
                            "properties": {
                                "found": {
                                    "type": "boolean",
                                    "description": "Найден ли врач в указанном месте работы"
                                },
                                "confidence": {
                                    "type": "string",
                                    "enum": ["high", "medium", "low"],
                                    "description": "Уровень уверенности в результате"
                                },
                                "explanation": {
                                    "type": "string",
                                    "description": "Краткое объяснение результата поиска"
                                },
                                "sources": {
                                    "type": "array",
                                    "items": {"type": "string"},
                                    "description": "Найденные источники информации"
                                },
                                "found_name": {
                                    "type": "string",
                                    "description": "Точное ФИО найденное на сайте (если найдено)"
                                }
                            },
                            "required": ["found", "confidence", "explanation", "sources", "found_name"],
                            "additionalProperties": False
                        },
                        "strict": True
                    }
                },
                input=[
                    {
                        "role": "system",
                        "content": (
                            "Ты помощник для проверки медицинских работников. "
                            "Используй web search для поиска информации о враче на официальных сайтах. "
                            "КРИТИЧЕСКИ ВАЖНО: ФИО должно совпадать ТОЧНО - фамилия, имя И отчество! "
                            "Любое различие в любой части ФИО = НЕ совпадение. "
                            "Примеры НЕ совпадений: "
                            "'Иванов Иван Петрович' ≠ 'Иванов Иван Сергеевич' (разные отчества) "
                            "'Иванов Иван Петрович' ≠ 'Петров Иван Петрович' (разные фамилии) "
                            "'Иванов Иван Петрович' ≠ 'Иванов Петр Петрович' (разные имена) "
                            "Возвращай found: true только при АБСОЛЮТНО ТОЧНОМ совпадении всех трех частей. "
                            "В поле found_name указывай точное ФИО, найденное на сайте. "
                            "Будь честным в оценке уверенности результата."
                        )
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            )

            result = json.loads(response.output_text)

            logger.info("=" * 60)
            logger.info("🔍 OPENAI WEB SEARCH VERIFICATION RESPONSE")
            logger.info("=" * 60)
            logger.info(f"👤 User: {full_name}")
            logger.info(f"🏥 Workplace: {workplace}")
            logger.info(f"🌐 Website: {website_url}")
            logger.info("-" * 60)
            logger.info("📄 JSON Response:")
            logger.info(json.dumps(result, ensure_ascii=False, indent=2))
            logger.info("=" * 60)

            return result

        except Exception as e:
            logger.error(f"Ошибка при web search верификации: {e}")
            return {
                "found": False,
                "confidence": "low",
                "explanation": f"Ошибка при проверке: {str(e)}",
                "sources": [],
                "found_name": ""
            }

    async def verify_document(self, full_name: str, workplace: str, file_id: str) -> Dict[str, Any]:
        """
        Проверка документа врача.

        Args:
            full_name: Полное имя врача
            workplace: Место работы врача
            file_id: ID файла документа

        Returns:
            Словарь с результатами верификации
        """
        try:
            from aiogram import Bot
            from config.settings import settings

            bot = Bot(token=settings.get_telegram_bot_token())
            file = await bot.get_file(file_id)
            file_data = await bot.download_file(file.file_path)

            await bot.session.close()

            return await self.verify_diploma_document(full_name, file_data.read(), "image/jpeg", workplace)

        except Exception as e:
            logger.error(f"Ошибка при получении файла {file_id}: {e}")
            return {
                "found": False,
                "confidence": "low",
                "explanation": f"Ошибка при анализе документа: {str(e)}",
                "document_type": "unknown",
                "found_name": "",
                "is_medical_document": False,
                "medical_indicators": [],
                "issuing_organization": ""
            }

    async def verify_diploma_document(self, full_name: str, image_data: bytes, file_type: str, workplace: str = "") -> Dict[str, Any]:
        """
        Проверить, содержит ли документ диплома указанное имя врача.

        Args:
            full_name: Полное имя врача для проверки
            image_data: Данные файла изображения
            file_type: MIME тип файла
            workplace: Место работы врача (необязательно)

        Returns:
            Словарь с результатами анализа документа
        """
        try:
            base64_image = base64.b64encode(image_data).decode('utf-8')

            logger.info(f"Анализ документа для врача {full_name}")

            response = await self.client.responses.create(
                model=self.model,
                text={
                    "format": {
                        "type": "json_schema",
                        "name": "document_verification",
                        "schema": {
                            "type": "object",
                            "properties": {
                                "found": {
                                    "type": "boolean",
                                    "description": "Найдено ли указанное ФИО в документе"
                                },
                                "confidence": {
                                    "type": "string",
                                    "enum": ["high", "medium", "low"],
                                    "description": "Уровень уверенности в результате"
                                },
                                "explanation": {
                                    "type": "string",
                                    "description": "Объяснение результата анализа"
                                },
                                "document_type": {
                                    "type": "string",
                                    "description": "Тип обнаруженного документа"
                                },
                                "found_name": {
                                    "type": "string",
                                    "description": "Найденное в документе ФИО (если есть)"
                                },
                                "is_medical_document": {
                                    "type": "boolean",
                                    "description": "Является ли документ медицинским (диплом, сертификат, удостоверение врача)"
                                },
                                "medical_indicators": {
                                    "type": "array",
                                    "items": {"type": "string"},
                                    "description": "Найденные медицинские признаки в документе"
                                },
                                "issuing_organization": {
                                    "type": "string",
                                    "description": "Организация, выдавшая документ (если указана)"
                                }
                            },
                            "required": ["found", "confidence", "explanation", "document_type", "found_name", "is_medical_document", "medical_indicators", "issuing_organization"],
                            "additionalProperties": False
                        },
                        "strict": True
                    }
                },
                input=[
                    {
                        "role": "system",
                        "content": (
                            "Ты помощник для анализа медицинских документов. "
                            "КРИТИЧЕСКИ ВАЖНО: ФИО должно совпадать ТОЧНО - фамилия, имя И отчество! "
                            "Любое различие в любой части ФИО = НЕ совпадение. "
                            "Примеры НЕ совпадений: "
                            "'Иванов Иван Петрович' ≠ 'Иванов Иван Сергеевич' (разные отчества) "
                            "'Иванов Иван Петрович' ≠ 'Петров Иван Петрович' (разные фамилии) "
                            "'Иванов Иван Петрович' ≠ 'Иванов Петр Петрович' (разные имена) "
                            "Возвращай found: true только при АБСОЛЮТНО ТОЧНОМ совпадении всех трех частей. "
                            "В поле found_name указывай точное ФИО, найденное в документе. "
                            "ВАЖНО: Проверяй, что документ действительно медицинский! "
                            "Медицинские документы должны содержать: "
                            "- Название медицинского учебного заведения или медицинской организации "
                            "- Медицинские термины (медицина, врач, лечебное дело, педиатрия, хирургия и т.д.) "
                            "- Официальные печати медицинских учреждений "
                            "- Номера лицензий или регистрационные номера "
                            "- Подписи уполномоченных лиц медицинских организаций "
                            "НЕ принимай: водительские удостоверения, паспорта, справки с работы, "
                            "самодельные документы, документы без медицинских признаков. "
                            "Возвращай структурированный результат в JSON формате."
                        )
                    },
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "input_text",
                                "text": f"Проанализируй этот документ на предмет медицинского образования/квалификации. "
                                        f"Ищи ФИО: {full_name}. "
                                        f"ОБЯЗАТЕЛЬНО проверь медицинские признаки документа: "
                                        f"медицинские термины, названия мед. учреждений, печати, подписи. "
                                        f"Верни подробный результат в JSON."
                            },
                            {
                                "type": "input_image",
                                "image_url": f"data:{file_type};base64,{base64_image}"
                            }
                        ]
                    }
                ]
            )

            result = json.loads(response.output_text)

            logger.info("=" * 60)
            logger.info("📄 OPENAI DOCUMENT VERIFICATION RESPONSE")
            logger.info("=" * 60)
            logger.info(f"👤 User: {full_name}")
            logger.info(f"🏥 Workplace: {workplace}")
            logger.info(f"📋 File Type: {file_type}")
            logger.info(f"📏 Image Size: {len(image_data)} bytes")
            logger.info("-" * 60)
            logger.info("📄 JSON Response:")
            logger.info(json.dumps(result, ensure_ascii=False, indent=2))
            logger.info("=" * 60)

            return result

        except Exception as e:
            logger.error(f"Ошибка при анализе документа: {e}")
            return {
                "found": False,
                "confidence": "low",
                "explanation": f"Ошибка при анализе документа: {str(e)}",
                "document_type": "unknown"
            }
