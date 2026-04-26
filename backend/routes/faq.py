from fastapi import APIRouter
from pydantic import BaseModel

from database import db

router = APIRouter()


class FAQItem(BaseModel):
    question: str
    answer: str
    category: str
    sort_order: int = 0


@router.get("/faq")
async def get_faq():
    faqs = await db.faqs.find({}, {"_id": 0}).sort("sort_order", 1).to_list(100)
    if not faqs:
        default_faqs = [
            FAQItem(question="Как добавить новую позицию в меню?", answer="Перейдите в раздел 'Меню', выберите категорию и нажмите кнопку 'Добавить позицию'.", category="Меню", sort_order=1),
            FAQItem(question="Как настроить QR-код для стола?", answer="В разделе 'Настройки' → 'Столы' вы можете создать стол и получить уникальный код.", category="Столы", sort_order=2),
            FAQItem(question="Как настроить типы вызовов?", answer="В разделе 'Настройки' → 'Типы вызовов' можно создать и редактировать типы вызовов.", category="Настройки", sort_order=3),
            FAQItem(question="Как подключить Telegram-бота?", answer="В разделе 'Telegram-бот' введите токен вашего бота и ID чата.", category="Интеграции", sort_order=4),
            FAQItem(question="Как импортировать меню из файла?", answer="В разделе 'Меню' нажмите 'Импорт меню' и выберите .json или .data файл.", category="Меню", sort_order=5),
            FAQItem(question="Как создать резервную копию?", answer="Раздел 'Резервные копии' (только для суперадмина): кнопки 'Скачать бэкап БД' и 'Скачать бэкап файлов'.", category="Настройки", sort_order=6),
        ]
        for faq in default_faqs:
            await db.faqs.insert_one(faq.model_dump())
        faqs = [f.model_dump() for f in default_faqs]
    return faqs
