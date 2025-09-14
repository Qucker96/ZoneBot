import interactions
import os

from datetime import datetime, timedelta
import pytz
from typing import List

from utils.db import Events
from utils.log import log_db
from interactions import Task, IntervalTrigger
from config import admin


class EventsService:
    """ Core-логика ивентов: создание, участие, выход, уведомления """



    def __init__(self) -> None:
        self.db = Events()
        self.cfg = admin
        self.MSK = pytz.timezone("Europe/Moscow")



    async def create(self,
                     ctx: interactions.SlashContext,
                     title: str,
                     description: str,
                     when_str: str,
                     max_participants: int = 100) -> int:

        """
            Создаёт embed-пост в канале и записывает ивент в БД
            
            Args:
                ctx: SlashContext
                title: str
                description: str
                when_str: str
                max_participants: int = 100

            Returns:
                int: message_id
        """

        channel_id = int(self.cfg.get("channels.events"))
        channel = await ctx.client.fetch_channel(channel_id)

        # Ожидаем формат "DD.MM.YY HH:MM" в MSK
        when_naive = datetime.strptime(when_str, "%d.%m.%y %H:%M")
        when_dt = self.MSK.localize(when_naive)

        embed = interactions.Embed(
            title=f"🎯 {title}",
            description=description or "",
            color=0x5865F2
        )
        embed.add_field(name="Начало", value=f"<t:{int(when_dt.timestamp())}:F>", inline=False)
        embed.add_field(name="Лимит", value=str(max_participants), inline=True)
        embed.add_field(name="Участники", value=f"0/{max_participants}", inline=True)
        embed.add_field(name="Статус", value=self._compute_status(when_dt.isoformat(), db_status="planned"), inline=True)
        embed.set_footer(text="Нажмите кнопки ниже, чтобы присоединиться или выйти")

        components = interactions.ActionRow(
            interactions.Button(style=interactions.ButtonStyle.SUCCESS, label="Присоединиться", custom_id="event_toggle"),
            interactions.Button(style=interactions.ButtonStyle.SECONDARY, label="Игроки", custom_id="event_list")
        )

        msg = await channel.send(embed=embed, components=components)

        self.db.add_event(
            message_id=int(msg.id),
            title=title,
            description=description or "",
            participants="",
            max_participants=max_participants,
            status="planned",
            ts=when_dt.isoformat()
        )

        log_db("INFO", f"Создан ивент '{title}' ({msg.id})")
        return int(msg.id)


    def build_event_embed(self, message_id: int) -> interactions.Embed:
        """ Строит актуальный embed по данным из БД """
        e = self.db.get_event(message_id)
        if not e:
            return interactions.Embed(title="Ивент не найден", color=0xED4245)

        title: str = e["title"]
        description: str = e.get("description") or ""
        max_participants: int = int(e["max_participants"])
        ts = e["ts"]
        when_dt = datetime.fromisoformat(ts)

        participants_list = [int(p) for p in (e["participants"].split(",") if e["participants"] else []) if p]
        cur = len(participants_list)

        embed = interactions.Embed(
            title=f"🎯 {title}",
            description=description,
            color=0x5865F2
        )
        embed.add_field(name="Начало", value=f"<t:{int(when_dt.timestamp())}:F>", inline=False)
        embed.add_field(name="Лимит", value=str(max_participants), inline=True)
        embed.add_field(name="Участники", value=f"{cur}/{max_participants}", inline=True)
        embed.add_field(name="Статус", value=self._compute_status(when_dt.isoformat(), db_status=str(e.get("status", "planned"))), inline=True)
        embed.set_footer(text="Нажмите кнопки ниже, чтобы присоединиться или выйти")
        return embed


    def _compute_status(self, when_iso: str, db_status: str) -> str:
        """Возвращает статус ивента.
        Правила:
          - Если db_status == 'finished' → "Закончился".
          - Иначе по времени:
              now < start-5m → "Скоро"
              start-5m <= now < start → "Начинается"
              now >= start → "Идёт"
        """
        now = datetime.now(self.MSK)
        start = datetime.fromisoformat(when_iso)
        # Перевести в MSK, если вдруг без TZ
        if start.tzinfo is None:
            start = self.MSK.localize(start)
        if str(db_status).lower() == "finished":
            return "Закончился"
        start_minus_5 = start - timedelta(minutes=5)
        if now < start_minus_5:
            return "Скоро"
        if start_minus_5 <= now < start:
            return "Начинается"
        return "Идёт"



    async def join(self, message_id: int, user_id: int) -> tuple[bool, int, int]:
        """Присоединение пользователя к ивенту"""
        ok, cur, mx = self.db.add_participant(message_id, user_id)
        return (ok, cur, mx)



    async def leave(self, message_id: int, user_id: int) -> tuple[bool, int, int]:
        """Выход пользователя из ивента"""
        ok, cur, mx = self.db.remove_participant(message_id, user_id)
        return (ok, cur, mx)



    async def notify_upcoming(self, client: interactions.Client) -> List[int]:
        """Отправляет напоминания за ~5 минут. Возвращает список message_id, по которым было уведомление"""
        now = datetime.now(self.MSK)
        start = (now + timedelta(minutes=4)).isoformat()
        end = (now + timedelta(minutes=6)).isoformat()
        events = self.db.list_need_notification(start, end)

        notified: List[int] = []
        if not events:
            return notified

        notif_channel_id = int(self.cfg.get("channels.event_notifications"))
        notif_channel = await client.fetch_channel(notif_channel_id)

        for e in events:
            participants = [int(p) for p in (e["participants"].split(",") if e["participants"] else []) if p]
            if not participants:
                continue

            mentions = " ".join(f"<@{pid}>" for pid in participants)
            await notif_channel.send(f"⏰ Через 5 минут начнётся ивент '{e['title']}' {mentions}")
            # Помечаем как уведомлённый, чтобы не слать повторно в следующей минуте
            try:
                self.db.set_status(int(e["message_id"]), "notified")
            except Exception:
                pass
            notified.append(int(e["message_id"]))
        return notified


    async def refresh_status_embeds(self, client: interactions.Client) -> None:
        """Периодически обновляет статус в embed для актуальных ивентов"""
        now = datetime.now(self.MSK)
        # Берём события, которые начнутся в течение 12 часов или начались не позже 3 часов назад
        relevant: list[dict] = self.db.list_events(limit=200)
        channel_id = int(self.cfg.get("channels.events"))
        channel = await client.fetch_channel(channel_id)

        for e in relevant:
            start = datetime.fromisoformat(e["ts"]).astimezone(self.MSK)
            if (now - timedelta(hours=3)) <= start <= (now + timedelta(hours=12)):
                try:
                    msg = await channel.fetch_message(int(e["message_id"]))
                    embed = self.build_event_embed(int(e["message_id"]))
                    await msg.edit(embed=embed)
                except Exception:
                    pass


_TASK_STARTED = False


def setup_tasks(bot: interactions.Client, service: EventsService) -> None:
    """Запускает периодическую проверку каждые 1 минуту (одиночный старт)"""
    global _TASK_STARTED
    if _TASK_STARTED:
        return

    @Task.create(IntervalTrigger(minutes=1))
    async def _notify_loop():
        try:
            await service.notify_upcoming(bot)
            await service.refresh_status_embeds(bot)
        except Exception:
            pass

    _notify_loop.start()
    _TASK_STARTED = True


