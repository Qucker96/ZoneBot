import os
import sqlite3
import pytz
from datetime import datetime
from typing import Optional, List, Dict, Any


class DB:
    """Универсальный класс для работы с SQLite"""

    def __init__(self, db_path: str) -> None:
        os.makedirs(os.path.dirname(db_path), exist_ok=True)

        self.path = db_path
        self.conn = sqlite3.connect(self.path)

        self.conn.row_factory = sqlite3.Row

        self.cursor = self.conn.cursor()

        self.MSK = pytz.timezone("Europe/Moscow")

        self._init_tables()

    def _init_tables(self) -> None:
        """Переопределяем в наследниках"""
        pass

    def commit(self) -> None:
        self.conn.commit()

    def close(self) -> None:
        self.conn.close()



class Log(DB):
    """Работа с таблицей logs"""

    def __init__(self) -> None:
        super().__init__(os.path.abspath("src/data/db/log.db"))



    def _init_tables(self) -> None:
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                level TEXT NOT NULL,
                message TEXT NOT NULL,
                reason TEXT,
                ts TEXT NOT NULL
            );
        """)
        self.commit()



    def write(self, level: str, message: str, reason: Optional[str] = None) -> None:
        ts = datetime.now(self.MSK).isoformat()
        self.cursor.execute(
            "INSERT INTO logs(level, message, reason, ts) VALUES (?, ?, ?, ?)",
                     (level.upper(), message, reason, ts)
        )
        self.commit()


    
    def get(self, limit: int = 10) -> List[Dict[str, Any]]:
        self.cursor.execute(
            "SELECT id, level, message, reason, ts "
            "FROM logs ORDER BY id DESC LIMIT ?",
            (limit,)
        )
        return [dict(row) for row in self.cursor.fetchall()]



class Users(DB):
    """Работа с таблицей users (статистика и предупреждения)"""

    def __init__(self) -> None:
        super().__init__(os.path.abspath("src/data/db/users.db"))

    def _init_tables(self) -> None:
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                birthday TEXT,
                messages INTEGER DEFAULT 0,
                warns INTEGER DEFAULT 0
            );
        """)
        self.commit()



    def add_user(self, user_id: int) -> None:
        """Добавляет нового пользователя, если его еще нет"""
        self.cursor.execute(
            "INSERT OR IGNORE INTO users (user_id, messages, warns) VALUES (?, 0, 0)",
            (user_id,)
        )
        self.commit()



    def get_user(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Получает информацию о пользователе"""
        self.cursor.execute(
            "SELECT user_id, birthday, messages, warns FROM users WHERE user_id = ?",
            (user_id,)
        )
        row = self.cursor.fetchone()
        return dict(row) if row else None



    def increment_messages(self, user_id: int) -> None:
        """Увеличивает счетчик сообщений пользователя"""
        self.add_user(user_id)
        self.cursor.execute(
            "UPDATE users SET messages = messages + 1 WHERE user_id = ?",
            (user_id,)
        )
        self.commit()



    def add_warn(self, user_id: int, count: int = 1) -> int:
        """Добавляет предупреждения пользователю"""
        self.add_user(user_id)
        self.cursor.execute(
            "UPDATE users SET warns = warns + ? WHERE user_id = ?",
            (count, user_id)
        )
        self.commit()
        
        user = self.get_user(user_id)
        return user['warns'] if user else 0



    def remove_warn(self, user_id: int, count: int = 1) -> int:
        """Убирает предупреждения у пользователя"""
        self.add_user(user_id)
        self.cursor.execute(
            "UPDATE users SET warns = MAX(0, warns - ?) WHERE user_id = ?",
            (count, user_id)
        )
        self.commit()
        
        user = self.get_user(user_id)
        return user['warns'] if user else 0



    def clear_warns(self, user_id: int) -> None:
        """Очищает все предупреждения пользователя"""
        self.add_user(user_id)
        self.cursor.execute(
            "UPDATE users SET warns = 0 WHERE user_id = ?",
            (user_id,)
        )
        self.commit()



    def get_leaderboard(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Получает топ пользователей по сообщениям"""
        self.cursor.execute(
            "SELECT user_id, messages, warns FROM users ORDER BY messages DESC LIMIT ?",
            (limit,)
        )
        return [dict(row) for row in self.cursor.fetchall()]



    def get_birthday_users_by_date(self, date_str: str) -> List[Dict[str, Any]]:
        """Получает список пользователей с днем рождения в указанную дату (формат DD.MM)"""
        self.cursor.execute(
            "SELECT user_id, birthday, messages, warns FROM users WHERE birthday = ?",
            (date_str,)
        )
        return [dict(row) for row in self.cursor.fetchall()]

    def get_all_users_with_birthday(self) -> List[Dict[str, Any]]:
        """Получает всех пользователей, у которых установлен день рождения"""
        self.cursor.execute(
            "SELECT user_id, birthday, messages, warns FROM users WHERE birthday IS NOT NULL AND birthday != ''"
        )
        return [dict(row) for row in self.cursor.fetchall()]

    def update_birthday(self, user_id: int, birthday: str) -> bool:
        """Обновляет день рождения пользователя. Возвращает True если успешно"""
        try:
            self.add_user(user_id)  # Создаем пользователя если его нет
            self.cursor.execute(
                "UPDATE users SET birthday = ? WHERE user_id = ?",
                (birthday, user_id)
            )
            self.commit()
            return True
        except Exception:
            return False

    def remove_birthday(self, user_id: int) -> None:
        """Удаляет день рождения у пользователя"""
        self.add_user(user_id)
        self.cursor.execute(
            "UPDATE users SET birthday = NULL WHERE user_id = ?",
            (user_id,)
        )
        self.commit()



class Events(DB):
    """Работа с таблицей events (Ивенты)"""

    def __init__(self) -> None:
        super().__init__(os.path.abspath("src/data/db/events.db"))



    def _init_tables(self) -> None:
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS events (
                message_id BIGINT PRIMARY KEY,
                title TEXT NOT NULL,
                description TEXT,
                participants TEXT DEFAULT '',
                max_participants INTEGER NOT NULL,
                status TEXT NOT NULL,
                ts TEXT NOT NULL
            );
        """)
        self.commit()



    def add_event(self, message_id: int, 
                  title: str, 
                  description: str, 
                  participants: str, 
                  max_participants: int, 
                  status: str,
                  ts: str) -> None:
        """Добавляет ивент"""
        self.cursor.execute(
            "INSERT INTO events (message_id, title, description, participants, max_participants, status, ts) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (message_id, title, description, participants, max_participants, status, ts)
        )
        self.commit()



    def get_event(self, message_id: int) -> Optional[Dict[str, Any]]:
        """Получает ивент по message_id"""
        self.cursor.execute(
            "SELECT message_id, title, description, participants, max_participants, status, ts FROM events WHERE message_id = ?",
            (message_id,)
        )
        row = self.cursor.fetchone()
        return dict(row) if row else None



    def update_event(self, message_id: int, title: str, description: str, participants: str, max_participants: int, status: str, ts: str) -> None:
        """Полное обновление ивента"""
        self.cursor.execute(
            "UPDATE events SET title = ?, description = ?, participants = ?, max_participants = ?, status = ?, ts = ? WHERE message_id = ?",
            (title, description, participants, max_participants, status, ts, message_id)
        )
        self.commit()



    def list_events(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Возвращает список ивентов (по времени начала)"""
        self.cursor.execute(
            "SELECT message_id, title, description, participants, max_participants, status, ts FROM events ORDER BY ts ASC LIMIT ?",
            (limit,)
        )
        return [dict(r) for r in self.cursor.fetchall()]



    def set_status(self, message_id: int, status: str) -> None:
        """Обновляет статус ивента"""
        self.cursor.execute(
            "UPDATE events SET status = ? WHERE message_id = ?",
            (status, message_id)
        )
        self.commit()



    def _get_participants_list(self, participants: str) -> List[int]:
        if not participants:
            return []
        return [int(p) for p in participants.split(",") if p]



    def add_participant(self, message_id: int, user_id: int) -> tuple[bool, int, int]:
        """Добавляет участника. Возвращает (успех, текущее_кол-во, максимум)"""
        event = self.get_event(message_id)
        if not event:
            return (False, 0, 0)

        participants_list = self._get_participants_list(event["participants"])
        if user_id in participants_list:
            return (True, len(participants_list), int(event["max_participants"]))

        if len(participants_list) >= int(event["max_participants"]):
            return (False, len(participants_list), int(event["max_participants"]))

        participants_list.append(user_id)
        new_value = ",".join(str(p) for p in participants_list)
        self.cursor.execute(
            "UPDATE events SET participants = ? WHERE message_id = ?",
            (new_value, message_id)
        )
        self.commit()
        return (True, len(participants_list), int(event["max_participants"]))



    def remove_participant(self, message_id: int, user_id: int) -> tuple[bool, int, int]:
        """Удаляет участника. Возвращает (успех, текущее_кол-во, максимум)"""
        event = self.get_event(message_id)
        if not event:
            return (False, 0, 0)

        participants_list = self._get_participants_list(event["participants"])
        if user_id not in participants_list:
            return (True, len(participants_list), int(event["max_participants"]))

        participants_list = [p for p in participants_list if p != user_id]
        new_value = ",".join(str(p) for p in participants_list)
        self.cursor.execute(
            "UPDATE events SET participants = ? WHERE message_id = ?",
            (new_value, message_id)
        )
        self.commit()
        return (True, len(participants_list), int(event["max_participants"]))



    def list_need_notification(self, from_iso: str, to_iso: str) -> List[Dict[str, Any]]:
        """Ивенты со статусом 'planned', начинающиеся в интервале [from_iso, to_iso]"""
        self.cursor.execute(
            "SELECT message_id, title, description, participants, max_participants, status, ts FROM events "
            "WHERE status = 'planned' AND ts >= ? AND ts <= ?",
            (from_iso, to_iso)
        )
        return [dict(r) for r in self.cursor.fetchall()]



class MoviePolls(DB):
    """Работа с таблицами голосований за фильм"""

    def __init__(self) -> None:
        super().__init__(os.path.abspath("src/data/db/events.db"))


    def _init_tables(self) -> None:
        # Таблица опросов по фильмам
        self.cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS movie_polls (
                message_id BIGINT PRIMARY KEY,
                title TEXT NOT NULL,
                description TEXT,
                status TEXT NOT NULL,
                ts_end TEXT NOT NULL,
                created_ts TEXT NOT NULL
            );
            """
        )
        # Варианты фильмов
        self.cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS movie_options (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                poll_message_id BIGINT NOT NULL,
                title TEXT NOT NULL,
                link TEXT,
                author_id BIGINT,
                FOREIGN KEY (poll_message_id) REFERENCES movie_polls(message_id)
            );
            """
        )
        # Голоса пользователей (по одному на опрос)
        self.cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS movie_votes (
                poll_message_id BIGINT NOT NULL,
                user_id BIGINT NOT NULL,
                option_id INTEGER NOT NULL,
                UNIQUE(poll_message_id, user_id),
                FOREIGN KEY (poll_message_id) REFERENCES movie_polls(message_id),
                FOREIGN KEY (option_id) REFERENCES movie_options(id)
            );
            """
        )
        self.commit()


    # --- Polls ---
    def add_poll(self,
                 message_id: int,
                 title: str,
                 description: str,
                 ts_end: str,
                 status: str = "open") -> None:
        created_ts = datetime.now(self.MSK).isoformat()
        self.cursor.execute(
            "INSERT INTO movie_polls(message_id, title, description, status, ts_end, created_ts) VALUES (?, ?, ?, ?, ?, ?)",
            (message_id, title, description, status, ts_end, created_ts)
        )
        self.commit()

    def get_poll(self, message_id: int) -> Optional[Dict[str, Any]]:
        self.cursor.execute(
            "SELECT message_id, title, description, status, ts_end, created_ts FROM movie_polls WHERE message_id = ?",
            (message_id,)
        )
        row = self.cursor.fetchone()
        return dict(row) if row else None

    def set_poll_status(self, message_id: int, status: str) -> None:
        self.cursor.execute(
            "UPDATE movie_polls SET status = ? WHERE message_id = ?",
            (status, message_id)
        )
        self.commit()

    def get_latest_open_poll(self) -> Optional[Dict[str, Any]]:
        self.cursor.execute(
            "SELECT message_id, title, description, status, ts_end, created_ts FROM movie_polls WHERE status = 'open' ORDER BY created_ts DESC LIMIT 1"
        )
        row = self.cursor.fetchone()
        return dict(row) if row else None

    def list_polls_to_close(self, from_iso: str, to_iso: str) -> List[Dict[str, Any]]:
        self.cursor.execute(
            "SELECT message_id, title, description, status, ts_end, created_ts FROM movie_polls WHERE status = 'open' AND ts_end >= ? AND ts_end <= ?",
            (from_iso, to_iso)
        )
        return [dict(r) for r in self.cursor.fetchall()]

    def list_polls_overdue(self, to_iso: str) -> List[Dict[str, Any]]:
        """Открытые опросы, у которых срок окончания уже наступил (ts_end <= to_iso)."""
        self.cursor.execute(
            "SELECT message_id, title, description, status, ts_end, created_ts FROM movie_polls WHERE status = 'open' AND ts_end <= ?",
            (to_iso,)
        )
        return [dict(r) for r in self.cursor.fetchall()]


    # --- Options ---
    def add_option(self, poll_message_id: int, title: str, link: Optional[str], author_id: Optional[int]) -> int:
        self.cursor.execute(
            "INSERT INTO movie_options(poll_message_id, title, link, author_id) VALUES (?, ?, ?, ?)",
            (poll_message_id, title, link, author_id)
        )
        self.commit()
        self.cursor.execute("SELECT last_insert_rowid() AS id")
        row = self.cursor.fetchone()
        return int(row["id"]) if row else 0

    def list_options(self, poll_message_id: int) -> List[Dict[str, Any]]:
        self.cursor.execute(
            "SELECT id, poll_message_id, title, link, author_id FROM movie_options WHERE poll_message_id = ? ORDER BY id ASC",
            (poll_message_id,)
        )
        return [dict(r) for r in self.cursor.fetchall()]


    # --- Votes ---
    def upsert_vote(self, poll_message_id: int, user_id: int, option_id: int) -> None:
        self.cursor.execute(
            """
            INSERT INTO movie_votes(poll_message_id, user_id, option_id)
            VALUES (?, ?, ?)
            ON CONFLICT(poll_message_id, user_id)
            DO UPDATE SET option_id = excluded.option_id
            """,
            (poll_message_id, user_id, option_id)
        )
        self.commit()

    def get_user_vote(self, poll_message_id: int, user_id: int) -> Optional[int]:
        self.cursor.execute(
            "SELECT option_id FROM movie_votes WHERE poll_message_id = ? AND user_id = ?",
            (poll_message_id, user_id)
        )
        row = self.cursor.fetchone()
        return int(row["option_id"]) if row else None

    def count_votes_by_option(self, poll_message_id: int) -> Dict[int, int]:
        self.cursor.execute(
            "SELECT option_id, COUNT(*) AS c FROM movie_votes WHERE poll_message_id = ? GROUP BY option_id",
            (poll_message_id,)
        )
        rows = self.cursor.fetchall()
        return {int(r["option_id"]): int(r["c"]) for r in rows}

    def pick_winner(self, poll_message_id: int) -> Optional[Dict[str, Any]]:
        """Возвращает вариант-победитель (dict movie_options.*)"""
        counts = self.count_votes_by_option(poll_message_id)
        options = self.list_options(poll_message_id)
        if not options:
            return None
        # Присвоим 0 голосов отсутствующим в counts
        for opt in options:
            opt_id = int(opt["id"])
            opt["_votes"] = counts.get(opt_id, 0)
        # Победитель: макс по голосам, при равенстве - с меньшим id (раньше добавлен)
        winner = sorted(options, key=lambda o: (-int(o["_votes"]), int(o["id"])))[0]
        return winner

    # --- Runoff helpers ---
    def top_tied_options(self, poll_message_id: int) -> Optional[List[Dict[str, Any]]]:
        """Возвращает все варианты, которые разделяют максимум голосов (>=2 варианта и >0 голосов)."""
        counts = self.count_votes_by_option(poll_message_id)
        options = self.list_options(poll_message_id)
        if len(options) < 2:
            return None
        # Сформировать словарь голосов с 0 по умолчанию
        id_to_votes = {int(o["id"]): counts.get(int(o["id"]), 0) for o in options}
        if not id_to_votes:
            return None
        max_votes = max(id_to_votes.values())
        if max_votes <= 0:
            return None
        tied_ids = [oid for oid, v in id_to_votes.items() if v == max_votes]
        if len(tied_ids) < 2:
            return None
        id_to_opt = {int(o["id"]): o for o in options}
        # Отсортируем по id для стабильности отображения
        return [id_to_opt[oid] for oid in sorted(tied_ids)]

    def reset_votes(self, poll_message_id: int) -> None:
        self.cursor.execute(
            "DELETE FROM movie_votes WHERE poll_message_id = ?",
            (poll_message_id,)
        )
        self.commit()

    def keep_only_options(self, poll_message_id: int, option_ids: list[int]) -> None:
        placeholders = ",".join(["?"] * len(option_ids))
        self.cursor.execute(
            f"DELETE FROM movie_options WHERE poll_message_id = ? AND id NOT IN ({placeholders})",
            (poll_message_id, *option_ids)
        )
        self.commit()

    def set_poll_end(self, poll_message_id: int, new_end_iso: str) -> None:
        self.cursor.execute(
            "UPDATE movie_polls SET ts_end = ?, status = 'open' WHERE message_id = ?",
            (new_end_iso, poll_message_id)
        )
        self.commit()