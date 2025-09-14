import interactions
from datetime import datetime, timedelta
import pytz
from typing import List, Optional

from utils.db import MoviePolls
from utils.log import log_db
from interactions import Task, IntervalTrigger
from config import admin

class MovieService:
    """Ядро логики голосований за фильм: создание, добавление вариантов, голосование, закрытие"""

    def __init__(self) -> None:
        self.db = MoviePolls()

        self.cfg = admin
        self.MSK = pytz.timezone("Europe/Moscow")


    def _format_until(self, end_iso: str) -> str:
        dt = datetime.fromisoformat(end_iso)
        # Приводим к МСК и выводим явное время в МСК + относительное время
        if dt.tzinfo is None:
            dt = self.MSK.localize(dt)
        msk_dt = dt.astimezone(self.MSK)
        human_msk = msk_dt.strftime("%d.%m.%Y %H:%M")
        return f"{human_msk} (МСК)"


    def _build_poll_embed(self, message_id: int) -> interactions.Embed:
        poll = self.db.get_poll(message_id)
        if not poll:
            return interactions.Embed(title="Опрос не найден", color=0xED4245)

        title = poll["title"]
        description = poll.get("description") or ""
        status = str(poll.get("status", "open"))
        ts_end = poll["ts_end"]

        counts = self.db.count_votes_by_option(message_id)
        options = self.db.list_options(message_id)

        embed = interactions.Embed(
            title=f"🎬 {title}",
            description=description,
            color=0x5865F2
        )
        embed.add_field(name="Начало", value=self._format_until(ts_end), inline=True)
        embed.add_field(name="Статус", value="Открыт" if status == "open" else "Завершён", inline=True)

        if options:
            lines: List[str] = []
            for opt in options:
                v = counts.get(int(opt["id"]), 0)
                line = f"• {opt['title']} — {v}"
                if opt.get("link"):
                    line += f"\n{opt['link']}"
                lines.append(line)
            embed.add_field(name="Варианты", value="\n".join(lines)[:1000] or "—", inline=False)
        else:
            embed.add_field(name="Варианты", value="Пока нет. Нажмите 'Предложить фильм'", inline=False)

        embed.set_footer(text="Выберите вариант в меню или предложите свой")
        return embed


    def _build_vote_components(self, message_id: int) -> List[interactions.ActionRow]:
        options = self.db.list_options(message_id)
        has_options = len(options) > 0

        # Кнопка добавления фильма
        row_buttons = interactions.ActionRow(
            interactions.Button(style=interactions.ButtonStyle.PRIMARY,
                                 label="Предложить фильм",
                                 custom_id="movie_add"),
        )

        # Меню выбора варианта (если есть варианты)
        select_options: List[interactions.StringSelectOption] = []
        for opt in options:
            select_options.append(
                interactions.StringSelectOption(
                    label=(opt["title"][:100] if len(opt["title"]) > 100 else opt["title"]),
                    value=str(opt["id"])
                )
            )

        opts = select_options or [interactions.StringSelectOption(label="Нет вариантов", value="0")]
        select_menu = interactions.StringSelectMenu(
            *opts,
            custom_id="movie_vote",
            placeholder="Выберите фильм",
            min_values=1,
            max_values=1,
            disabled=not has_options,
        )

        row_select = interactions.ActionRow(select_menu)
        return [row_buttons, row_select]


    async def create_poll(self,
                          ctx: interactions.SlashContext,
                          title: str,
                          end_str: str,
                          description: str = "") -> int:
        """Создаёт сообщение-опрос в канале и записывает poll в БД"""
        channel_id = int(self.cfg.get("channels.movie_polls"))
        channel = await ctx.client.fetch_channel(channel_id)

        # Ожидаем формат "DD.MM.YY HH:MM" в MSK
        end_naive = datetime.strptime(end_str, "%d.%m.%y %H:%M")
        end_dt = self.MSK.localize(end_naive)

        embed = self._build_poll_embed_placeholder(title=title, description=description, ts_end=end_dt.isoformat())
        components = self._build_vote_components(message_id=0)  # заглушка, затем перерисуем

        msg = await channel.send(embed=embed, components=components)

        self.db.add_poll(
            message_id=int(msg.id),
            title=title,
            description=description or "",
            ts_end=end_dt.isoformat(),
            status="open",
        )

        # Перестроим embed/компоненты уже с реальным message_id
        await msg.edit(embed=self._build_poll_embed(int(msg.id)), components=self._build_vote_components(int(msg.id)))

        log_db("INFO", f"Создан опрос фильмов '{title}' ({msg.id})")
        return int(msg.id)


    def _build_poll_embed_placeholder(self, title: str, description: str, ts_end: str) -> interactions.Embed:
        embed = interactions.Embed(title=f"🎬 {title}", description=description or "", color=0x5865F2)
        embed.add_field(name="Начало", value=self._format_until(ts_end), inline=True)
        embed.add_field(name="Статус", value="Открыт", inline=True)
        embed.add_field(name="Варианты", value="Пока нет. Нажмите 'Предложить фильм'", inline=False)
        embed.set_footer(text="Выберите вариант в меню или предложите свой")
        return embed


    async def add_option(self, message_id: int, title: str, link: Optional[str], author_id: Optional[int]) -> bool:
        """Добавляет вариант. Возвращает False, если дубликат по названию."""
        poll = self.db.get_poll(message_id)
        if not poll or str(poll.get("status")) != "open":
            return False
        existing = self.db.list_options(message_id)
        title_norm = title.strip().casefold()
        for opt in existing:
            if opt["title"].strip().casefold() == title_norm:
                return False
        self.db.add_option(message_id, title.strip(), (link or "").strip() or None, author_id)
        return True


    async def cast_vote(self, message_id: int, user_id: int, option_id: int) -> bool:
        poll = self.db.get_poll(message_id)
        if not poll or str(poll.get("status")) != "open":
            return False
        # Проверим, что опция принадлежит этому опросу
        options = self.db.list_options(message_id)
        valid_ids = {int(o["id"]) for o in options}
        if option_id not in valid_ids:
            return False
        self.db.upsert_vote(message_id, user_id, option_id)
        return True


    async def close_due_polls(self, client: interactions.Client) -> List[int]:
        """Закрывает опросы, у которых подошло время окончания. Возвращает список message_id закрытых опросов."""
        now = datetime.now(self.MSK)
        to_iso = now.isoformat()
        polls = self.db.list_polls_overdue(to_iso)

        closed: List[int] = []
        if not polls:
            return closed

        channel_id = int(self.cfg.get("channels.movie_polls"))
        channel = await client.fetch_channel(channel_id)

        for p in polls:
            mid = int(p["message_id"])
            try:
                # Проверка на ничью среди лидеров (>=2 вариантов имеют максимум голосов)
                tied = self.db.top_tied_options(mid)
                if tied:
                    # Запускаем доголосование: оставляем только финалистов, чистим голоса, ставим +10 минут
                    option_ids = [int(o["id"]) for o in tied]
                    self.db.keep_only_options(mid, option_ids)
                    self.db.reset_votes(mid)
                    new_end = (now + timedelta(minutes=10)).isoformat()
                    self.db.set_poll_end(mid, new_end)

                    # Обновляем сообщение с пометкой доголосования
                    msg = await channel.fetch_message(mid)
                    embed = self._build_poll_embed(mid)
                    embed.add_field(name="Статус", value="Доголосование (10 минут)", inline=False)
                    await msg.edit(embed=embed, components=self._build_vote_components(mid))

                    role_id = self.cfg.get("roles.movie")
                    mention = f"<@&{int(role_id)}> " if role_id else ""
                    names = ", ".join(o['title'] for o in tied)
                    await channel.send(f"{mention}Ничья! Доголосование между: {names} (10 минут)")
                else:
                    winner = self.db.pick_winner(mid)
                    self.db.set_poll_status(mid, "closed")

                    msg = await channel.fetch_message(mid)
                    embed = self._build_poll_embed(mid)
                    if winner:
                        embed.add_field(name="Победитель",
                                        value=f"{winner['title']} ({self.db.count_votes_by_option(mid).get(int(winner['id']), 0)} голосов)",
                                        inline=False)
                    await msg.edit(embed=embed, components=[])

                    if winner:
                        role_id = self.cfg.get("roles.movie")
                        mention = f"<@&{int(role_id)}> " if role_id else ""
                        announce = f"{mention}🎉 Голосование завершено! Сегодня смотрим: {winner['title']}"
                        if winner.get("link"):
                            announce += f"\n{winner['link']}"
                        await channel.send(announce)
                    else:
                        await channel.send("Голосование завершено, победитель не определён (нет вариантов)")

                    closed.append(mid)
            except Exception as e:
                log_db("ERROR", f"movie.close_due_polls failed for {mid}", str(e))

        return closed


    async def refresh_poll_embeds(self, client: interactions.Client) -> None:
        """Обновляет эмбед опросов (для актуализации голосов/вариантов)"""
        poll = self.db.get_latest_open_poll()
        if not poll:
            return
        channel_id = int(self.cfg.get("channels.movie_polls"))
        channel = await client.fetch_channel(channel_id)
        try:
            msg = await channel.fetch_message(int(poll["message_id"]))
            await msg.edit(embed=self._build_poll_embed(int(poll["message_id"])),
                           components=self._build_vote_components(int(poll["message_id"])) )
        except Exception:
            pass


_TASK_STARTED = False


def setup_tasks(bot: interactions.Client, service: MovieService) -> None:
    """Запускает периодическую проверку каждые 1 минуту (одиночный старт)"""
    global _TASK_STARTED
    if _TASK_STARTED:
        return

    @Task.create(IntervalTrigger(minutes=1))
    async def _movie_loop():
        try:
            await service.close_due_polls(bot)
            await service.refresh_poll_embeds(bot)
        except Exception:
            pass

    _movie_loop.start()
    _TASK_STARTED = True


