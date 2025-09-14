from interactions import (
    SlashCommand, slash_option,
    Extension, Permissions,
    OptionType, SlashContext,
    Member, Embed
)
from services.mod.warn import WarnService



from config import admin
_warn_perms = Permissions(int(admin.get("permissions.moderation")))



class WarnCog(Extension):
    """Система предупреждений

    Commands:
        /warn add <member> [count] [reason]: добавить предупреждения
        /warn remove <member> [count] [reason]: убрать предупреждения
        /warn clear <member> [reason]: очистить все предупреждения
        /warn check <member>: проверить предупреждения
    """

    def __init__(self, bot) -> None:
        self.svc = WarnService()



    warn = SlashCommand(
        name="warn",
        description="Система предупреждений",
        default_member_permissions=_warn_perms
    )



    @warn.subcommand(sub_cmd_name="add", sub_cmd_description="Добавить предупреждения")
    @slash_option(name="member",
                  description="Пользователь",
                  opt_type=OptionType.USER,
                  required=True)
    @slash_option(name="count",
                  description="Количество предупреждений (по умолчанию 1)",
                  opt_type=OptionType.INTEGER,
                  required=False)
    @slash_option(name="reason",
                  description="Причина",
                  opt_type=OptionType.STRING,
                  required=False)
    async def cmd_add(self,
                      ctx: SlashContext,
                      member: Member,
                      count: int = 1,
                      reason: str = "Не указана"):
        """Добавляет предупреждения пользователю"""

        if count <= 0:
            return await ctx.send("❗ Количество должно быть положительным", ephemeral=True)

        status, new_count = await self.svc.add(member, ctx.author, count, reason)
        
        if status == 1:
            embed = Embed(
                title="✅ Предупреждение добавлено",
                description=f"Пользователь: {member.mention}\n"
                           f"Добавлено: {count}\n"
                           f"Текущее количество: {new_count}",
                color=0x57F287
            )
            embed.set_footer(text=f"Причина: {reason}")
            await ctx.send(embed=embed, ephemeral=True)
        else:
            await ctx.send("❗ Произошла ошибка при добавлении предупреждений", ephemeral=True)



    @warn.subcommand(sub_cmd_name="remove", sub_cmd_description="Убрать предупреждения")
    @slash_option(name="member",
                  description="Пользователь",
                  opt_type=OptionType.USER,
                  required=True)
    @slash_option(name="count",
                  description="Количество предупреждений (по умолчанию 1)",
                  opt_type=OptionType.INTEGER,
                  required=False)
    @slash_option(name="reason",
                  description="Причина",
                  opt_type=OptionType.STRING,
                  required=False)
    async def cmd_remove(self,
                         ctx: SlashContext,
                         member: Member,
                         count: int = 1,
                         reason: str = "Не указана"):
        """Убирает предупреждения у пользователя"""

        if count <= 0:
            return await ctx.send("❗ Количество должно быть положительным", ephemeral=True)

        status, new_count = await self.svc.remove(member, ctx.author, count, reason)
        
        if status == 1:
            embed = Embed(
                title="✅ Предупреждение убрано",
                description=f"Пользователь: {member.mention}\n"
                           f"Убрано: {count}\n"
                           f"Текущее количество: {new_count}",
                color=0x57F287
            )
            embed.set_footer(text=f"Причина: {reason}")
            await ctx.send(embed=embed, ephemeral=True)
        else:
            await ctx.send("❗ Произошла ошибка при удалении предупреждений", ephemeral=True)



    @warn.subcommand(sub_cmd_name="clear", sub_cmd_description="Очистить все предупреждения")
    @slash_option(name="member",
                  description="Пользователь",
                  opt_type=OptionType.USER,
                  required=True)
    @slash_option(name="reason",
                  description="Причина",
                  opt_type=OptionType.STRING,
                  required=False)
    async def cmd_clear(self,
                        ctx: SlashContext,
                        member: Member,
                        reason: str = "Не указана"):
        """Очищает все предупреждения пользователя"""

        status = await self.svc.clear(member, ctx.author, reason)
        
        if status == 1:
            embed = Embed(
                title="✅ Все предупреждения очищены",
                description=f"Пользователь: {member.mention}",
                color=0x57F287
            )
            embed.set_footer(text=f"Причина: {reason}")
            await ctx.send(embed=embed, ephemeral=True)
        else:
            await ctx.send("❗ Произошла ошибка при очистке предупреждений", ephemeral=True)



    @warn.subcommand(sub_cmd_name="check", sub_cmd_description="Проверить предупреждения")
    @slash_option(name="member",
                  description="Пользователь",
                  opt_type=OptionType.USER,
                  required=True)
    async def cmd_check(self,
                        ctx: SlashContext,
                        member: Member):
        """Проверяет количество предупреждений пользователя"""

        warns = await self.svc.get_warns(member)
        
        embed = Embed(
            title="📊 Статистика предупреждений",
            description=f"Пользователь: {member.mention}",
            color=0x5865F2
        )
        embed.add_field(name="Количество предупреждений", value=str(warns), inline=True)
        
        await ctx.send(embed=embed, ephemeral=True)