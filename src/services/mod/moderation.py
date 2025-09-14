import interactions
import os

from services.mod.role import RoleService
from utils.log import log_db
from config import admin

class ModerationService:
    """ Core логика, можно использовать повсюду """

    def __init__(self) -> None:
        self.mute_role = int(admin.get("roles.mute"))

        self.role = RoleService()


    async def kick(self,
                   member: interactions.Member,
                   author: interactions.Member,
                   reason: str = "Не указана") -> int:
        """
            Кикает пользователя

            Args:
                member (Member): Пользователь
                author (Member): Отправитель команды (ЛОГИ)
                reason (str): Причина кика (по умолчанию "Не указана")

            Returns:
                1: Команда успешно выполнена
                -1: У бота нет прав на выполнение этого действия
                0: Произошла ошибка
        """

        try:
            await member.kick(reason=reason)
            log_db("INFO", 
                    f"Модератор {author} кикнул пользователя {member}",
                    reason=reason)

            return 1

        except interactions.errors.Forbidden:
            return -1
        except:
            return 0



    async def ban(self,
                  member:  interactions.Member,
                  author: interactions.Member,
                  reason: str = "Не указана",
                  delete_messages: int = 0) -> int:
        """
            Банит пользователя

            Args:
                member (Member): Пользователь
                author (Member): Отправитель команды (ЛОГИ)
                reason (str): Причина бана (по умолчанию "Не указана")
                delete_messages (int): Удалять ли сообщения пользователя (в днях)

            Returns:
                1: Команда успешно выполнена
                -1: У бота нет прав на выполнение этого действия
                0: Произошла ошибка
        """

        try:
            await member.ban(reason=reason,
                             delete_message_seconds=(delete_messages*86_400))
            log_db("INFO", 
                    f"Модератор {author} забанил пользователя {member}",
                    reason=reason)

            return 1

        except interactions.errors.Forbidden:
            return -1
        except:
            return 0



    async def unban(self,
                guild: interactions.Guild,
                author: interactions.Member,
                user: int,
                reason: str = "Не указана") -> int:
        """
            Разбанивает пользователя по ID.

            Args:
                guild (Guild): сервер
                author (Member): Отправитель команды (ЛОГИ)
                user (int): Discord-ID пользователя
                reason (str): причина (по умолчанию "Не указана")

            Returns:
                1: успешно
                -1: нет прав
                0: ошибка
        """
        try:
            await guild.unban(user=user, reason=reason)
            user_id = guild.get_member(user)
            log_db("INFO", 
                    f"Модератор {author} разбанил пользователя {user_id}",
                    reason=reason)

            return 1
        except interactions.errors.Forbidden:
            return -1
        except:
            return 0



    async def mute(self,
                   guild: interactions.Guild,
                   member: interactions.Member,
                   author: interactions.Member,
                   reason: str = "Не указана") -> int:

        """
            Мьютит пользователя

            Args:
                guild (Guild): Сервер
                member (Member): Пользователь
                author (Member): Отправитель команды (ЛОГИ)
                reason (str): Причина мута (по умолчанию "Не указана")

            Returns:
                1: Команда успешно выполнена
                -1: У бота нет прав на выполнение этого действия
                0: Произошла ошибка
        """

        role = guild.get_role(self.mute_role)
        res = await self.role.add(member=member,
                                  author=author,
                                  role=role,
                                  reason=reason)

        return res



    async def unmute(self,
                     guild: interactions.Guild,
                     member: interactions.Member,
                     author: interactions.Member,
                     reason: str = "Не указана"):
        """
            Размьючивает пользователя

            Args:
                guild (Guild): Сервер
                member (Member): Пользователь
                reason (str): Причина размьюта (по умолчанию "Не указана")

            Returns:
                1: Команда успешно выполнена
                -1: У бота нет прав на выполнение этого действия
                0: Произошла ошибка
        """

        role = guild.get_role(self.mute_role)
        res = await self.role.remove(member=member,
                                     author=author,
                                     role=role,
                                     reason=reason)

        return res
