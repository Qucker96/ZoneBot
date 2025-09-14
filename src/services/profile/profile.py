import interactions
from datetime import datetime, timedelta
import pytz
from typing import Optional, List, Dict, Any

from utils.db import Users
from utils.log import log_db
from config import admin


class ProfileService:
    """Core логика профилей, можно использовать повсюду"""

    def __init__(self) -> None:
        self.db = Users()
        self.cfg = admin
        self.MSK = pytz.timezone("Europe/Moscow")

    async def get_user_profile(self, user_id: int) -> Optional[Dict[str, Any]]:
        """
        Получает профиль пользователя

        Args:
            user_id (int): ID пользователя

        Returns:
            Optional[Dict[str, Any]]: Данные профиля или None
        """
        user_data = self.db.get_user(user_id)
        if not user_data:
            # Создаем пользователя если его нет
            self.db.add_user(user_id)
            user_data = self.db.get_user(user_id)
        
        return user_data

    async def set_birthday(self, user_id: int, birthday_str: str) -> int:
        """
        Устанавливает день рождения пользователя

        Args:
            user_id (int): ID пользователя
            birthday_str (str): Дата в формате DD.MM

        Returns:
            1: День рождения успешно установлен
            0: Неверный формат даты
            -1: Ошибка при сохранении
        """
        try:
            # Парсим дату в формате DD.MM
            day, month = birthday_str.split('.')
            day = int(day)
            month = int(month)
            
            # Проверяем корректность даты
            if not (1 <= day <= 31 and 1 <= month <= 12):
                return 0
            
            # Проверяем существование даты (например, 31.02 не существует)
            try:
                test_date = datetime(2024, month, day)
            except ValueError:
                return 0
            
            # Сохраняем в формате DD.MM используя метод из db.py
            success = self.db.update_birthday(user_id, birthday_str)
            if success:
                log_db("INFO", f"Пользователь {user_id} установил день рождения: {birthday_str}")
                return 1
            else:
                return -1
            
        except (ValueError, IndexError):
            return 0

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

    def format_profile_embed(self, user_data: Dict[str, Any], user: interactions.User) -> interactions.Embed:
        """Форматирует embed для профиля пользователя"""
        embed = interactions.Embed(
            title=f"👤 Профиль {user.display_name}",
            color=0x00FF00
        )
        
        embed.set_thumbnail(url=user.avatar.url if user.avatar else None)
        
        # Основная информация
        embed.add_field(
            name="📊 Статистика",
            value=f"Сообщений: {user_data['messages']}\n"
                  f"Предупреждений: {user_data['warns']}",
            inline=True
        )
        
        # День рождения
        birthday_text = user_data.get('birthday', 'Не установлен')
        if birthday_text == 'Не установлен':
            birthday_text = "❌ Не установлен"
        else:
            birthday_text = f"🎂 {birthday_text}"
            
        embed.add_field(
            name="🎂 День рождения",
            value=birthday_text,
            inline=True
        )
        
        embed.set_footer(text=f"ID: {user_data['user_id']}")
        
        return embed