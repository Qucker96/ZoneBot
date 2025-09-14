import re
from interactions import (
    SlashCommand, slash_option,
    Extension, Permissions,
    OptionType, SlashContext,
    Embed, ActionRow, StringSelectMenu, StringSelectOption,
    component_callback, ComponentContext, listen, Button, ButtonStyle, Modal, ShortText,
    modal_callback, ModalContext
)
from services.events.movie import MovieService, setup_tasks
from utils.tomlIO import TomlIO
from typing import Dict


from config import admin
_movie_perms = Permissions(int(admin.get("permissions.movie")))


class MovieCog(Extension):
    """Опросы фильмов: создание, добавление вариантов, голосование, завершение"""

    def __init__(self, bot) -> None:
        self.bot = bot
        self.svc = MovieService()
        # Запоминаем для какого пользователя какой опрос ожидать при сабмите модалки
        self._pending_add: Dict[int, int] = {}


    @listen()
    async def on_startup(self):
        setup_tasks(self.bot, self.svc)


    movie = SlashCommand(
        name="movie",
        description="Голосование за фильм",
        default_member_permissions=_movie_perms
    )


    @movie.subcommand(sub_cmd_name="create", sub_cmd_description="Создать голосование")
    @slash_option(name="title",
                  description="Название опроса",
                  opt_type=OptionType.STRING,
                  required=True)
    @slash_option(name="when",
                  description="Окончание в формате DD.MM.YY HH:MM (MSK)",
                  opt_type=OptionType.STRING,
                  required=True)
    @slash_option(name="description",
                  description="Описание",
                  opt_type=OptionType.STRING,
                  required=False)
    async def cmd_create(self,
                         ctx: SlashContext,
                         title: str,
                         when: str,
                         description: str = ""):
        try:
            mid = await self.svc.create_poll(ctx, title, when, description)
            await ctx.send(f"✅ Создан опрос. message_id: {mid}", ephemeral=True)
        except Exception as e:
            await ctx.send(f"❗ Ошибка создания: {e}", ephemeral=True)


    @movie.subcommand(sub_cmd_name="stop", sub_cmd_description="Завершить голосование (по message_id)")
    @slash_option(name="message_id",
                  description="ID сообщения опроса",
                  opt_type=OptionType.STRING,
                  required=True)
    async def cmd_stop(self,
                       ctx: SlashContext,
                       message_id: str):
        try:
            mid = int(message_id)
            poll = self.svc.db.get_poll(mid)
            if not poll:
                return await ctx.send("Опрос не найден", ephemeral=True)

            self.svc.db.set_poll_status(mid, "closed")

            channel_id = int(self.svc.cfg.get("channels.movie_polls"))
            channel = await ctx.client.fetch_channel(channel_id)
            msg = await channel.fetch_message(mid)

            embed = self.svc._build_poll_embed(mid)
            winner = self.svc.db.pick_winner(mid)
            if winner:
                embed.add_field(name="Победитель",
                                value=f"{winner['title']} ({self.svc.db.count_votes_by_option(mid).get(int(winner['id']), 0)} голосов)",
                                inline=False)
            await msg.edit(embed=embed, components=[])

            # Объявление победителя с пингом роли movie (если есть)
            winner = self.svc.db.pick_winner(mid)
            if winner:
                role_id = self.svc.cfg.get("roles.movie")
                mention = f"<@&{int(role_id)}> " if role_id else ""
                announce = f"{mention}🎉 Голосование завершено! Сегодня смотрим: {winner['title']}"
                if winner.get("link"):
                    announce += f"\n{winner['link']}"
                await channel.send(announce)

            await ctx.send("✅ Опрос завершён", ephemeral=True)
        except Exception as e:
            await ctx.send(f"❗ Ошибка завершения: {e}", ephemeral=True)


    # Кнопка "Предложить фильм" → модалка
    @component_callback("movie_add")
    async def on_add_button(self, ctx: ComponentContext):
        try:
            poll_message_id = int(ctx.message.id)
            # Привяжем пользователя к конкретному опросу
            self._pending_add[int(ctx.author.id)] = poll_message_id
            modal = Modal(
                ShortText(label="Название фильма", custom_id="movie_add_title", required=True, max_length=200),
                title="Предложить фильм",
                custom_id="movie_add"
            )
            await ctx.send_modal(modal)
        except Exception as e:
            await ctx.send(f"❗ Ошибка: {e}", ephemeral=True)


    # Обработка модалки добавления
    @modal_callback("movie_add")
    async def on_add_modal(self, ctx: ModalContext, movie_add_title: str):
        try:
            user_id = int(ctx.author.id)
            poll_message_id = self._pending_add.get(user_id)
            if not poll_message_id:
                # Фоллбэк: возьмём последний открытый опрос
                latest = self.svc.db.get_latest_open_poll()
                if not latest:
                    return await ctx.send("❗ Не найден активный опрос", ephemeral=True)
                poll_message_id = int(latest["message_id"])
            # Очистим привязку, чтобы не залипала
            self._pending_add.pop(user_id, None)
            title_val = movie_add_title or ""

            ok = await self.svc.add_option(poll_message_id, title_val, None, int(ctx.author.id))
            if not ok:
                return await ctx.send("❗ Не удалось добавить (возможно, дубликат или опрос закрыт)", ephemeral=True)

            # Обновляем сообщение
            channel_id = int(self.svc.cfg.get("channels.movie_polls"))
            channel = await self.bot.fetch_channel(channel_id)
            try:
                msg = await channel.fetch_message(poll_message_id)
                await msg.edit(embed=self.svc._build_poll_embed(poll_message_id),
                               components=self.svc._build_vote_components(poll_message_id))
            except Exception:
                pass

            await ctx.send("✅ Вариант добавлен", ephemeral=True)
        except Exception as e:
            try:
                await ctx.send(f"❗ Ошибка: {e}", ephemeral=True)
            except Exception:
                # Если не удалось ответить (например, уже ответили), просто игнорируем
                pass


    # Выбор фильма из селекта → голос
    @component_callback("movie_vote")
    async def on_vote_select(self, ctx: ComponentContext):
        try:
            poll_message_id = int(ctx.message.id)
            if not ctx.values:
                return await ctx.send("❗ Ничего не выбрано", ephemeral=True)
            option_id = int(ctx.values[0])
            ok = await self.svc.cast_vote(poll_message_id, int(ctx.author.id), option_id)
            if not ok:
                return await ctx.send("❗ Не удалось проголосовать (возможно, опрос закрыт)", ephemeral=True)

            await ctx.edit_origin(embed=self.svc._build_poll_embed(poll_message_id),
                                  components=self.svc._build_vote_components(poll_message_id))
        except Exception as e:
            await ctx.send(f"❗ Ошибка: {e}", ephemeral=True)


