from interactions import (
    SlashCommand, slash_option,
    Extension,
    OptionType, SlashContext,
    Button, ButtonStyle,
    ActionRow, ComponentContext, component_callback,
    Modal, ShortText, listen, modal_callback, ModalContext
)
from services.profile.profile import ProfileService
from services.profile.birthday import BirthdayService, setup_birthday_tasks


class ProfileCog(Extension):
    """Профили пользователей: просмотр и настройка
    
    Commands:
        /profile show [user]: показать профиль (свой или указанного пользователя)
        /profile edit: редактировать свой профиль
    """

    def __init__(self, bot) -> None:
        self.bot = bot
        self.svc = ProfileService()
        self.birthday_svc = BirthdayService()
        # Храним информацию о том, для какого пользователя показывается профиль
        self._profile_users = {}
        # Храним информацию о том, какой пользователь открыл модальное окно
        self._modal_users = {}

        self.answers = {
            1:  ("✅", "День рождения успешно установлен: {date}", 0x57F287),
            0:  ("❌", "Неверный формат даты. Используйте формат DD.MM", 0xED4245),
            -1: ("❗", "Ошибка при сохранении дня рождения", 0xFAA81A),
        }

    def _build_answer(self, code: int, date: str = "") -> str:
        emoji, template, _ = self.answers[code]
        return f"{emoji} {template.format(date=date)}"

    @listen()
    async def on_startup(self):
        """Запускает фоновую задачу после старта бота"""
        setup_birthday_tasks(self.bot, self.birthday_svc)

    @listen()
    async def on_message_create(self, event):
        """Отслеживает сообщения пользователей и увеличивает счетчик"""
        try:
            # Игнорируем сообщения ботов
            if event.message.author.bot:
                return
            
            # Игнорируем системные сообщения
            if event.message.type != 0:  # 0 = DEFAULT (обычное сообщение)
                return
            
            # Увеличиваем счетчик сообщений
            self.svc.db.increment_messages(event.message.author.id)
            
        except Exception as e:
            # Логируем ошибку, но не прерываем работу бота
            print(f"Ошибка при подсчете сообщений: {e}")

    profile = SlashCommand(
        name="profile",
        description="Показать профиль пользователя"
    )

    @profile.subcommand(sub_cmd_name="show", sub_cmd_description="Показать профиль")
    @slash_option(
        name="user",
        description="Пользователь (если не указан, показывается ваш профиль)",
        opt_type=OptionType.USER,
        required=False
    )
    async def show_profile(self, ctx: SlashContext, user=None):
        """Показывает профиль пользователя"""
        try:
            # Если пользователь не указан, показываем профиль автора команды
            target_user = user if user else ctx.author
            target_user_id = target_user.id
            
            user_data = await self.svc.get_user_profile(target_user_id)
            
            if not user_data:
                await ctx.send("❌ Ошибка при получении данных профиля", ephemeral=True)
                return
            
            embed = self.svc.format_profile_embed(user_data, target_user)
            
            # Добавляем кнопку обновления для всех профилей
            buttons = [
                Button(
                    style=ButtonStyle.SECONDARY,
                    label="🔄 Обновить",
                    custom_id="profile_refresh"
                )
            ]
            action_row = ActionRow(*buttons)
            
            msg = await ctx.send(embed=embed, components=[action_row])
            self._profile_users[msg.id] = target_user_id
            
        except Exception as e:
            await ctx.send(f"❌ Ошибка: {str(e)}", ephemeral=True)

    @profile.subcommand(sub_cmd_name="edit", sub_cmd_description="Редактировать свой профиль")
    async def edit_profile(self, ctx: SlashContext):
        """Показывает интерфейс для редактирования профиля"""
        try:
            # Получаем данные профиля
            user_data = await self.svc.get_user_profile(ctx.author.id)
            
            if not user_data:
                await ctx.send("❌ Ошибка при получении данных профиля", ephemeral=True)
                return
            
            embed = self.svc.format_profile_embed(user_data, ctx.author)
            
            # Создаем кнопки для редактирования
            buttons = [
                Button(
                    style=ButtonStyle.PRIMARY,
                    label="🎂 Установить день рождения",
                    custom_id="profile_set_birthday"
                ),
                Button(
                    style=ButtonStyle.SECONDARY,
                    label="🔄 Обновить",
                    custom_id="profile_refresh"
                )
            ]
            
            action_row = ActionRow(*buttons)
            

            msg = await ctx.send(embed=embed, components=[action_row], ephemeral=True)
            self._profile_users[msg.id] = ctx.author.id
            
        except Exception as e:
            await ctx.send(f"❌ Ошибка: {str(e)}", ephemeral=True)

    @component_callback("profile_set_birthday")
    async def set_birthday_callback(self, ctx: ComponentContext):
        """Обработчик кнопки установки дня рождения"""
        try:
            # Получаем user_id из сохраненной информации
            message_id = ctx.message.id if ctx.message else None
            if not message_id:
                await ctx.send("❌ Не удалось получить ID сообщения", ephemeral=True)
                return
                
            user_id = self._profile_users.get(message_id)
            if not user_id:
                await ctx.send("❌ Не удалось определить пользователя", ephemeral=True)
                return
            
            # Проверяем, что кнопку нажал владелец профиля
            if ctx.author.id != user_id:
                await ctx.send("❌ Вы можете изменять только свой профиль!", ephemeral=True)
                return
            
            # Сохраняем информацию о пользователе для модального окна
            self._modal_users[ctx.author.id] = user_id
            
            # Создаем модальное окно для ввода дня рождения
            modal = Modal(
                title="Установить день рождения",
                custom_id="profile_birthday_modal"
            )
            modal.add_components(
                ShortText(
                    label="День рождения",
                    custom_id="birthday_input",
                    placeholder="Введите дату в формате DD.MM (например: 15.03)",
                    required=True,
                    max_length=5
                )
            )
            
            await ctx.send_modal(modal)
            
        except Exception as e:
            await ctx.send(f"❌ Ошибка: {str(e)}", ephemeral=True)

    @modal_callback("profile_birthday_modal")
    async def birthday_modal_callback(self, ctx: ModalContext, birthday_input: str):
        """Обработчик модального окна для установки дня рождения"""
        try:
            # Используем ID автора модального окна (пользователь может изменять только свой профиль)
            user_id = ctx.author.id
            
            # Очищаем сохраненную информацию (если есть)
            self._modal_users.pop(ctx.author.id, None)
            
            # Получаем введенную дату
            birthday_str = birthday_input.strip()
            
            if not birthday_str:
                await ctx.send("❌ Дата не может быть пустой", ephemeral=True)
                return
            
            # Устанавливаем день рождения
            result = await self.svc.set_birthday(user_id, birthday_str)
            
            if result == 1:
                await ctx.send(self._build_answer(result, birthday_str), ephemeral=True)
            else:
                await ctx.send(self._build_answer(result), ephemeral=True)
                
        except Exception as e:
            await ctx.send(f"❌ Ошибка: {str(e)}", ephemeral=True)

    @component_callback("profile_refresh")
    async def refresh_profile_callback(self, ctx: ComponentContext):
        """Обработчик кнопки обновления профиля"""
        try:
            # Получаем user_id из сохраненной информации
            message_id = ctx.message.id if ctx.message else None
            if not message_id:
                await ctx.send("❌ Не удалось получить ID сообщения", ephemeral=True)
                return
                
            user_id = self._profile_users.get(message_id)
            if not user_id:
                await ctx.send("❌ Не удалось определить пользователя", ephemeral=True)
                return
            
            # Получаем обновленные данные
            user_data = await self.svc.get_user_profile(user_id)
            
            if not user_data:
                await ctx.send("❌ Ошибка при получении данных профиля", ephemeral=True)
                return
            
            # Получаем пользователя для отображения
            user = await self.bot.fetch_user(user_id)
            if not user:
                await ctx.send("❌ Пользователь не найден", ephemeral=True)
                return
            
            embed = self.svc.format_profile_embed(user_data, user)
            
            # Создаем только кнопку обновления (как в profile show)
            buttons = [
                Button(
                    style=ButtonStyle.SECONDARY,
                    label="🔄 Обновить",
                    custom_id="profile_refresh"
                )
            ]
            
            action_row = ActionRow(*buttons)
            
            await ctx.edit_origin(embed=embed, components=[action_row])
            
        except Exception as e:
            await ctx.send(f"❌ Ошибка: {str(e)}", ephemeral=True)