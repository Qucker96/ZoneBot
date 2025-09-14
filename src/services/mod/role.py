import interactions
from typing import List, Tuple
from utils.log import log_db

class RoleService:
    """ Core логика, можно использовать повсюду """

    async def add(self,
                  member: interactions.Member,
                  author: interactions.Member | None,
                  role: interactions.Role,
                  reason: str = "Не указана") -> int:

        """
            Добавляет роль пользователю

            Args:
                member (Member): Пользователь
                role (Role): Роль, присваемая пользователю
                reason (str): Причина выдачи роли (по умолчанию "Не указана")

            Returns:
                1: Команда успешно выполнена
                2: У пользователя уже есть эта роль
                -1: У бота нет прав для этого действия
                0: Произошла ошибка
        """

        try:
            if role in member.roles:
                return 2

            await member.add_role(role=role, reason=reason)
            if author is not None:
                log_db(level="INFO",
                       message=f"Модератор {author} добавил роль {role.name} пользователю {member}",
                       reason=reason)

            return 1

        except interactions.errors.Forbidden:
            return -1
        except:
            return 0



    async def adds(self,
                   members: List[interactions.Member],
                   role: interactions.Role,
                   reason: str = "Не указана") -> List[Tuple[interactions.Member, int]]:

        """
            Добавляет роль нескольким пользователям

            Args:
                members (Member): Пользователи
                role (Role): Роль, присваемая пользователям
                reason (str): Причина выдачи роли (по умолчанию "Не указана")

            Returns:
                Возвращает список [member, код]
        """

        results: List[Tuple[interactions.Member, int]] = []
        for m in members:
            res = await self.add(member=m,
                                 author=None,
                                 role=role,
                                 reason=reason)
            results.append((m, res))
        return results

    async def add_many(self,
                       guild: interactions.Guild,
                       members: List[interactions.Member],
                       role: interactions.Role,
                       reason: str = "Не указана") -> List[Tuple[interactions.Member, int]]:
        return await self.adds(members=members, role=role, reason=reason)



    async def remove(self,
                     member: interactions.Member,
                     author: interactions.Member | None,
                     role: interactions.Role,
                     reason: str = "Не указана") -> int:

        """
            Убирает роль у пользователя

            Args:
                member (Member): Пользователь
                role (Role): Роль, убираемая у пользователя
                reason (str): Причина убирания роли (по умолчанию "Не указана")

            Returns:
                1: Команда успешно выполнена
                2: У пользователя нет этой роли
                -1: У бота нет прав для этого действия
                0: Произошла ошибка
        """

        try:
            if role not in member.roles:
                return 2
            
            await member.remove_role(role=role, reason=reason)
            if author is not None:
                log_db(level="INFO",
                       message=f"Модератор {author} убрал роль {role.name} у пользователя {member}",
                       reason=reason)

            return 1

        except interactions.errors.Forbidden:
            return -1
        except:
            return 0



    async def removes(self,
                      members: List[interactions.Member],
                      role: interactions.Role,
                      reason: str = "Не указана") -> List[Tuple[interactions.Member, int]]:

        """
            Убирает роль у нескольких пользователей

            Args:
                members (Member): Пользователи
                role (Role): Роль, убираемая у пользователей
                reason (str): Причина убирания роли (по умолчанию "Не указана")

            Returns:
                Возвращает список [member, код]
        """

        results: List[Tuple[interactions.Member, int]] = []
        for m in members:
            res = await self.remove(member=m,
                                    author=None,
                                    role=role,
                                    reason=reason)
            results.append((m, res))
        return results

    async def remove_many(self,
                          guild: interactions.Guild,
                          members: List[interactions.Member],
                          role: interactions.Role,
                          reason: str = "Не указана") -> List[Tuple[interactions.Member, int]]:
        return await self.removes(members=members, role=role, reason=reason)



    async def list_members(self,
                           guild: interactions.Guild,
                           role: interactions.Role) -> List[interactions.Member]:

        """
            Выводит список участников, у которых есть данная роль

            Args:
                guild (Guild): Сервер, на котором выполняется команда
                role (Role): Роль

            Returns:
                Возвращает список пользователей
        """

        await guild.chunk()
        return [m for m in guild.members if role in m.roles]

            
