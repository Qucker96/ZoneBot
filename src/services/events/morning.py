import interactions
import pytz
import random
import os
from datetime import datetime
from interactions import Task, CronTrigger
from config import admin
from utils.log import log_db


class MorningService:
    """Сервис для ежедневных уведомлений 'доброе утро' в 8:00 МСК"""

    def __init__(self) -> None:
        self.cfg = admin
        self.MSK = pytz.timezone("Europe/Moscow")
        self._task_started = False
        self.messages_file = os.path.join(os.path.dirname(__file__), "..", "..", "data", "morning.txt")
        self.gifs_file = os.path.join(os.path.dirname(__file__), "..", "..", "data", "morning_gif.txt")

    def _get_random_message(self) -> str:
        """Читает файл с сообщениями и возвращает случайное"""
        try:
            if not os.path.exists(self.messages_file):
                log_db("WARNING", f"Файл {self.messages_file} не найден, используется стандартное сообщение")
                return "Доброе утро! Надеюсь, у вас будет отличный день! ☀️"
            
            with open(self.messages_file, 'r', encoding='utf-8') as f:
                messages = [line.strip() for line in f.readlines() if line.strip()]
            
            if not messages:
                log_db("WARNING", f"Файл {self.messages_file} пуст, используется стандартное сообщение")
                return "Доброе утро! Надеюсь, у вас будет отличный день! ☀️"
            
            return random.choice(messages)
            
        except Exception as e:
            log_db("ERROR", f"Ошибка при чтении файла сообщений: {str(e)}")
            return "Доброе утро! Надеюсь, у вас будет отличный день! ☀️"

    def _get_random_gif(self) -> str:
        """Читает файл с гифками и возвращает случайную ссылку"""
        try:
            if not os.path.exists(self.gifs_file):
                log_db("WARNING", f"Файл {self.gifs_file} не найден, гифка не будет добавлена")
                return None
            
            with open(self.gifs_file, 'r', encoding='utf-8') as f:
                gifs = [line.strip() for line in f.readlines() if line.strip()]
            
            if not gifs:
                log_db("WARNING", f"Файл {self.gifs_file} пуст, гифка не будет добавлена")
                return None
            
            return random.choice(gifs)
            
        except Exception as e:
            log_db("ERROR", f"Ошибка при чтении файла гифок: {str(e)}")
            return None

    async def send_morning_notification(self, client: interactions.Client) -> None:
        """Отправляет уведомление 'доброе утро' в настроенный канал"""
        try:
            # Получаем ID канала из конфига
            channel_id = self.cfg.get("channels.events")
            if not channel_id:
                log_db("ERROR", "Не настроен канал для уведомлений в admin.toml")
                return

            channel = await client.fetch_channel(int(channel_id))
            if not channel:
                log_db("ERROR", f"Не удалось найти канал {channel_id}")
                return

            # Получаем случайное сообщение и гифку
            message_text = self._get_random_message()
            gif_url = self._get_random_gif()

            # Создаем embed с сообщением и гифкой
            embed = interactions.Embed(
                description=message_text,
                color=0xFFD700  # Золотой цвет
            )
            
            # Добавляем гифку, если она есть
            if gif_url:
                embed.set_image(url=gif_url)

            await channel.send(embed=embed)
            log_db("INFO", f"Отправлено уведомление 'доброе утро': {message_text[:50]}...")

        except Exception as e:
            log_db("ERROR", f"Ошибка при отправке уведомления: {str(e)}")

    def setup_morning_task(self, bot: interactions.Client) -> None:
        """Настраивает задачу для ежедневной отправки уведомлений в 8:00 МСК"""
        if self._task_started:
            return

        @Task.create(CronTrigger(hour=8, minute=0, timezone="Europe/Moscow"))
        async def morning_task():
            await self.send_morning_notification(bot)

        morning_task.start()
        self._task_started = True
        log_db("INFO", "Настроена задача ежедневных уведомлений в 8:00 МСК")
