import interactions
from utils.db import Users
from utils.log import log_db

class WarnService:
    """Core логика для работы с предупреждениями"""

    def __init__(self) -> None:
        self.db = Users()



    async def add(self,
                  member: interactions.Member,
                  author: interactions.Member,
                  count: int = 1,
                  reason: str = "Не указана") -> tuple[int, int]:

        """
            Добавляет предупреждения пользователю

            Args:
                member (Member): Пользователь
                author (Member): Отправитель команды
                count (int): Количество предупреждений для добавления
                reason (str): Причина

            Returns:
                tuple: (status_code, new_warns_count)
                status_code:
                    1: Успешно
                    -1: Ошибка
        """

        try:
            new_count = self.db.add_warn(member.id, count)
            log_db("INFO",
                   f"Модератор {author} добавил {count} предупреждений пользователю {member}",
                   reason=reason)
            return (1, new_count)
        except Exception as e:
            log_db("ERROR", f"Ошибка при добавлении предупреждений: {str(e)}")
            return (-1, 0)



    async def remove(self,
                     member: interactions.Member,
                     author: interactions.Member,
                     count: int = 1,
                     reason: str = "Не указана") -> tuple[int, int]:

        """
            Убирает предупреждения у пользователя

            Args:
                member (Member): Пользователь
                author (Member): Отправитель команды
                count (int): Количество предупреждений для удаления
                reason (str): Причина

            Returns:
                tuple: (status_code, new_warns_count)
                status_code:
                    1: Успешно
                    -1: Ошибка
        """

        try:
            new_count = self.db.remove_warn(member.id, count)
            log_db("INFO",
                   f"Модератор {author} убрал {count} предупреждений у пользователя {member}",
                   reason=reason)
            return (1, new_count)
        except Exception as e:
            log_db("ERROR", f"Ошибка при удалении предупреждений: {str(e)}")
            return (-1, 0)



    async def clear(self,
                    member: interactions.Member,
                    author: interactions.Member,
                    reason: str = "Не указана") -> int:

        """
            Очищает все предупреждения пользователя

            Args:
                member (Member): Пользователь
                author (Member): Отправитель команды
                reason (str): Причина

            Returns:
                status_code:
                    1: Успешно
                    -1: Ошибка
        """

        try:
            self.db.clear_warns(member.id)
            log_db("INFO",
                   f"Модератор {author} очистил все предупреждения у пользователя {member}",
                   reason=reason)
            return 1
        except Exception as e:
            log_db("ERROR", f"Ошибка при очистке предупреждений: {str(e)}")
            return -1

    async def get_warns(self, member: interactions.Member) -> int:

        """
            Получает количество предупреждений пользователя

            Args:
                member (Member): Пользователь

            Returns:
                int: Количество предупреждений
        """

        user = self.db.get_user(member.id)
        return user['warns'] if user else 0