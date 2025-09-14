from utils.db import Log



def log_db(level: str = "INFO",
           message: str = "",
           reason: str = ""):

    """
        Пишет в log.db лог

        Args:
            level (str): Уровень логирования (INFO, WARN, ERROR)
            message (str): Сообщение
            reason (str): причина (если есть)

        Returns:
            1: Логирование прошло успешно
            0: Ошибка
    """

    log = Log()
    log.write(level=level, message=message, reason=reason)
