import os
from interactions import (
    SlashCommand, slash_option,
    Extension, Permissions,
    OptionType, SlashContext,
    Embed, Button, ButtonStyle,
    ActionRow, ComponentContext, component_callback, listen
)
from services.events.events import EventsService, setup_tasks
from utils.tomlIO import TomlIO



from config import admin
_events_perms = Permissions(int(admin.get("permissions.events")))



class EventsCog(Extension):
    """ Ивенты: создание, участие, выход и просмотр участников """

    def __init__(self, bot) -> None:
        self.bot = bot
        self.svc = EventsService()



    @listen()
    async def on_startup(self):
        """ Запускает фоновую задачу после старта бота """
        setup_tasks(self.bot, self.svc)



    events = SlashCommand(
        name="event",
        description="Система ивентов",
        default_member_permissions=_events_perms
    )



    @events.subcommand(sub_cmd_name="create", sub_cmd_description="Создать ивент")
    @slash_option(name="title",
                  description="Название",
                  opt_type=OptionType.STRING,
                  required=True)
    @slash_option(name="when",
                  description="Время старта в формате DD.MM.YY HH:MM (MSK)",
                  opt_type=OptionType.STRING,
                  required=True)
    @slash_option(name="description",
                  description="Описание",
                  opt_type=OptionType.STRING,
                  required=False)
    @slash_option(name="max",
                  description="Лимит участников",
                  opt_type=OptionType.INTEGER,
                  required=False)
    async def cmd_create(self,
                         ctx: SlashContext,
                         title: str,
                         description: str = "",
                         when: str = "",
                         max: int = 100):
        """
            Создаёт ивент и публикует embed в канале событий

            Args:
                ctx (SlashContext): контекст команды
                title (str): название ивента
                description (str): описание
                when (str): время в формате DD.MM.YY HH:MM (MSK)
                max (int): лимит участников
        """

        try:
            msg_id = await self.svc.create(ctx, title, description, when, max or 100)
            await ctx.send(f"✅ Ивент создан. message_id: {msg_id}", ephemeral=True)
        except Exception as e:
            await ctx.send(f"❗ Ошибка создания: {e}", ephemeral=True)


    @events.subcommand(sub_cmd_name="stop", sub_cmd_description="Завершить ивент (по message_id)")
    @slash_option(name="message_id",
                  description="ID сообщения ивента",
                  opt_type=OptionType.STRING,
                  required=True)
    async def cmd_stop(self,
                       ctx: SlashContext,
                       message_id: str):
        """ Убирает кнопки, меняет статус и добавляет список участников в embed """

        try:
            mid = int(message_id)
            event = self.svc.db.get_event(mid)
            if not event:
                return await ctx.send("Ивент не найден", ephemeral=True)


            self.svc.db.set_status(mid, "finished")


            embed = self.svc.build_event_embed(mid)
            ids = [int(p) for p in (event["participants"].split(",") if event["participants"] else []) if p]
            if ids:
                mentions = "\n".join(f"<@{pid}>" for pid in ids)
                embed.add_field(name="Участники", value=mentions, inline=False)

            channel_id = int(self.svc.cfg.get("channels.events"))
            channel = await ctx.client.fetch_channel(channel_id)
            msg = await channel.fetch_message(mid)
            await msg.edit(embed=embed, components=[])

            await ctx.send("✅ Ивент завершён", ephemeral=True)
        except Exception as e:
            await ctx.send(f"❗ Ошибка завершения: {e}", ephemeral=True)


    @component_callback("event_toggle")
    async def on_toggle(self, ctx: ComponentContext):
        """ Переключает участие пользователя и обновляет сообщение и кнопки """
        try:
            message_id = int(ctx.message.id)
            # Проверим текущее состояние и переключим
            event = self.svc.db.get_event(message_id)
            user_id = int(ctx.author.id)
            participants = [int(p) for p in (event["participants"].split(",") if event and event["participants"] else []) if p]

            did_join = False
            if user_id in participants:
                ok, cur, mx = await self.svc.leave(message_id, user_id)
                text = "✅ Вы вышли из ивента" if ok else "❗ Ошибка выхода"
            else:
                ok, cur, mx = await self.svc.join(message_id, user_id)
                if not ok:
                    return await ctx.send("❗ Не удалось присоединиться (возможно, лимит)", ephemeral=True)
                text = f"✅ Вы в списке участников ({cur}/{mx})"
                did_join = True

            # Обновим embed (счётчики/статус) в основном сообщении
            updated_embed = self.svc.build_event_embed(message_id)
            await ctx.message.edit(embed=updated_embed)

            # Эпhemeral кнопки с персональной надписью "Выйти"/"Присоединиться"
            in_event = user_id in ([int(p) for p in (self.svc.db.get_event(message_id)["participants"].split(",") 
                       if self.svc.db.get_event(message_id)["participants"] else []) if p])
            personal_row = ActionRow(
                Button(style=ButtonStyle.DANGER if in_event else ButtonStyle.SUCCESS,
                       label="Выйти" if in_event else "Присоединиться",
                       custom_id="event_toggle"),
                Button(style=ButtonStyle.SECONDARY, label="Игроки", custom_id="event_list"),
            )
            if did_join:
                await ctx.send(text, ephemeral=True)
            else:
                await ctx.send(text, components=personal_row, ephemeral=True)
        except Exception as e:
            await ctx.send(f"❗ Ошибка: {e}", ephemeral=True)



    @component_callback("event_list")
    async def on_list(self, ctx: ComponentContext):
        """ Показывает список участников текущего ивента (ephemeral) """
        try:
            message_id = int(ctx.message.id)
            event = self.svc.db.get_event(message_id)
            ids = [int(p) for p in (event["participants"].split(",") if event and event["participants"] else []) if p]
            if not ids:
                return await ctx.send("Пока никто не присоединился", ephemeral=True)
            # Формируем список упоминаний
            mentions = "\n".join(f"<@{pid}>" for pid in ids)
            await ctx.send(f"Участники ({len(ids)}):\n{mentions}", ephemeral=True)
        except Exception as e:
            await ctx.send(f"❗ Ошибка: {e}", ephemeral=True)


