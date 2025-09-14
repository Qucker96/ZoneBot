import os
from interactions import (
    SlashCommand, slash_option,
    Extension, Permissions,
    OptionType, SlashContext,
    Member
)
from services.mod.moderation import ModerationService



from config import admin
_moder_perms = Permissions(int(admin.get("permissions.moderation")))



class ModerationCog(Extension):
    """ Функции модерации
       
        Commands:
            /m kick <member> [reason]: кинуть пользователя
            /m ban  <member> [reason]: забанить пользователя
            /m mute <member> [reason]: замьютить пользователя
            /m unmute <member> [reason]: размьютить пользователя
    """

    def __init__(self, bot) -> None:
        self.svc = ModerationService()

        self.answers = {
            1:  ("✅", "Успешно: {user} {action}", 0x57F287),
            2:  ("⚠️", "{user} уже {state}",       0xFEE75C),
            -1:  ("❌", "Недостаточно прав для {action} {user}", 0xED4245),
            0:  ("❗", "Не удалось {action} {user}",            0xFAA81A),
        }

    def _build_answer(self, code: int, user: str, action: str, state: str = "") -> str:
        emoji, template, _ = self.answers[code]
        return f"{emoji} {template.format(user=user, action=action, state=state)}"



    m = SlashCommand(name="m", 
                     description="Функции модерации",
                     default_member_permissions=_moder_perms)


 
    @m.subcommand(sub_cmd_name="kick", sub_cmd_description="Кикнуть пользователя")
    @slash_option(name="member", 
                  description="Пользователь", 
                  opt_type=OptionType.USER,
                  required=True)
    @slash_option(name="reason",
                  description="Причина кика",
                  opt_type=OptionType.STRING,
                  required=False)
    async def cmd_kick(self, 
                       ctx: SlashContext, 
                       member: Member,
                       reason: str = "Не указана"):

        """
            Кикает пользователя

            /m kick <member> <reason>

            Arguments:
                member (Member): пользователь (обязательное поле)
                reason (str): причина (необязательное поле)
        """

        res = await self.svc.kick(member=member,
                                  author=ctx.author,
                                  reason=reason)

        msg = self._build_answer(res, member.mention, "кикнут", "уже кикнут")
        await ctx.send(msg, ephemeral=True)



    @m.subcommand(sub_cmd_name="ban", sub_cmd_description="Забанить пользователя")
    @slash_option(name="member", 
                  description="Пользователь", 
                  opt_type=OptionType.USER,
                  required=True)
    @slash_option(name="reason",
                  description="Причина бана",
                  opt_type=OptionType.STRING,
                  required=False)
    @slash_option(name="delete_messages",
                  description="Удалить сообщения пользователя (0-7 дней)",
                  opt_type=OptionType.INTEGER,
                  required=False)
    async def cmd_ban(self, 
                      ctx: SlashContext, 
                      member: Member,
                      reason: str = "Не указана",
                      delete_messages: int = 0):

        """
            Банит пользователя

            /m ban <member> <reason>

            Arguments:
                member (Member): пользователь (обязательное поле)
                reason (str): причина (необязательное поле)
        """

        res = await self.svc.ban(member=member,
                                 author=ctx.author,
                                 reason=reason, 
                                 delete_messages=delete_messages)

        msg = self._build_answer(res, member.mention, "забанен", "уже забанен")
        await ctx.send(msg, ephemeral=True)



    @m.subcommand(sub_cmd_name="unban", sub_cmd_description="Разбанить пользователя")
    @slash_option(name="member",
                description="ID или упоминание забаненного пользователя",
                opt_type=OptionType.STRING,
                required=True)
    @slash_option(name="reason",
                description="Причина разбана",
                opt_type=OptionType.STRING,
                required=False)
    async def cmd_unban(self,
                        ctx: SlashContext,
                        member: str,
                        reason: str = "Не указана"):

        """
            Разбанивает пользователя по ID/упоминанию.

            /m unban <member> <reason>

            Arguments:
                member (str): ID или упоминание (обязательное поле)
                reason (str): причина (необязательное поле)
        """

        try:
            uid = int(''.join(filter(str.isdigit, member)))
        except ValueError:
            return await ctx.send("❗ Неверный формат пользователя", ephemeral=True)

        res = await self.svc.unban(guild=ctx.guild, 
                                   author=ctx.author, 
                                   user_id=uid, 
                                   reason=reason)

        msg = self._build_answer(res, f"<@{uid}>", "разбанен", "уже разбанен")
        await ctx.send(msg, ephemeral=True)



    @m.subcommand(sub_cmd_name="mute", sub_cmd_description="Замьютить пользователя")
    @slash_option(name="member",
                  description="Пользователь",
                  opt_type=OptionType.USER,
                  required=True)
    @slash_option(name="reason",
                  description="Причина мьюта",
                  opt_type=OptionType.STRING,
                  required=False)
    async def cmd_mute(self,
                       ctx: SlashContext,
                       member: Member,
                       reason: str = "Не указана"):

        """
            Мьютит пользователя

            /m mute <member> <reason>

            Arguments:
                member (Member): пользователь (обязательное поле)
                reason (str): причина (необязательное поле)
        """

        res = await self.svc.mute(guild=ctx.guild,
                                  member=member,
                                  author=ctx.author,
                                  reason=reason)

        msg = self._build_answer(res, member.mention, "замьючен", "уже замьючен")
        await ctx.send(msg, ephemeral=True)



    @m.subcommand(sub_cmd_name="unmute", sub_cmd_description="Размьютить пользователя")
    @slash_option(name="member",
                  description="Пользователь",
                  opt_type=OptionType.USER,
                  required=True)
    @slash_option(name="reason",
                  description="Причина размьюта",
                  opt_type=OptionType.STRING,
                  required=False)
    async def cmd_unmute(self,
                       ctx: SlashContext,
                       member: Member,
                       reason: str = "Не указана"):

        """
            Размьютит пользователя

            /m unmute <member> <reason>

            Arguments:
                member (Member): пользователь (обязательное поле)
                reason (str): причина (необязательное поле)
        """

        res = await self.svc.unmute(guild=ctx.guild,
                                    member=member,
                                    author=ctx.author,
                                    reason=reason)

        msg = self._build_answer(res, member.mention, "размьючен", "уже размьючен")
        await ctx.send(msg, ephemeral=True)
                        
            

