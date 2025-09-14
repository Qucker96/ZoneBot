import interactions
from datetime import datetime, timedelta
import pytz
from typing import List, Dict, Any

from utils.db import Users
from utils.log import log_db
from interactions import Task, CronTrigger
from config import admin


class BirthdayService:
    """Сервис для работы с днями рождения"""

    def __init__(self) -> None:
        self.db = Users()
        self.cfg = admin
        self.MSK = pytz.timezone("Europe/Moscow")

    async def get_birthday_users_today(self) -> List[Dict[str, Any]]:
        """Получает список пользователей, у которых сегодня день рождения"""
        today = datetime.now(self.MSK)
        today_str = f"{today.day:02d}.{today.month:02d}"
        
        # Используем метод из db.py
        return self.db.get_birthday_users_by_date(today_str)

    async def get_birthday_users_tomorrow(self) -> List[Dict[str, Any]]:
        """Получает список пользователей, у которых завтра день рождения"""
        tomorrow = datetime.now(self.MSK) + timedelta(days=1)
        tomorrow_str = f"{tomorrow.day:02d}.{tomorrow.month:02d}"
        
        # Используем метод из db.py
        return self.db.get_birthday_users_by_date(tomorrow_str)

    async def send_birthday_congratulations(self, bot: interactions.Client) -> None:
        """Отправляет поздравления с днем рождения в специальный канал"""
        try:
            birthday_users = await self.get_birthday_users_today()
            
            if not birthday_users:
                return
            
            # Получаем канал для поздравлений
            channel_id = int(self.cfg.get("channels.birthday", self.cfg.get("channels.events")))
            channel = await bot.fetch_channel(channel_id)
            
            for user_data in birthday_users:
                user_id = user_data['user_id']
                try:
                    user = await bot.fetch_user(user_id)
                    if user:
                        embed = interactions.Embed(
                            title="🎉 С Днем Рождения! 🎉",
                            description=f"Поздравляем {user.mention} с днем рождения! 🎂\n\n"
                                       f"Желаем счастья, здоровья и исполнения всех желаний! ✨",
                            color=0xFFD700
                        )
                        embed.add_field(
                            name="📊 Статистика",
                            value=f"Сообщений: {user_data['messages']}\n"
                                  f"Предупреждений: {user_data['warns']}",
                            inline=True
                        )
                        embed.set_thumbnail(url=user.avatar.url if user.avatar else None)
                        embed.set_footer(text=f"День рождения: {user_data['birthday']}")
                        
                        await channel.send(embed=embed)
                        
                except Exception as e:
                    log_db("ERROR", f"Не удалось отправить поздравление пользователю {user_id}: {str(e)}")
                    
        except Exception as e:
            log_db("ERROR", f"Ошибка при отправке поздравлений: {str(e)}")

    async def check_and_send_birthdays(self, bot: interactions.Client) -> None:
        """Проверяет дни рождения и отправляет поздравления"""
        try:
            await self.send_birthday_congratulations(bot)
        except Exception as e:
            log_db("ERROR", f"Ошибка при проверке дней рождения: {str(e)}")


def setup_birthday_tasks(bot: interactions.Client, birthday_service: BirthdayService) -> None:
    """Настраивает фоновые задачи для проверки дней рождения"""
    
    @Task.create(CronTrigger("0 10 * * *", tz="Europe/Moscow"))
    async def birthday_check_task():
        """Задача для проверки дней рождения в 10:00 по МСК"""
        await birthday_service.check_and_send_birthdays(bot)
    
    # Запускаем задачу
    birthday_check_task.start()
    
    log_db("INFO", "Задача проверки дней рождения запущена (каждый день в 10:00 МСК)")