import os
from interactions import (
    SlashCommand, slash_option,
    Extension, Permissions,
    OptionType, SlashContext,
    Member, Role, Embed
)
from services.mod.role import RoleService



from config import admin
_role_perms = Permissions(int(admin.get("permissions.moderation")))



class RoleCog(Extension):
    """Функции управления ролями

    Commands:
        /role add    <role> <member> [reason]
        /role adds   <role> <members> [reason]
        /role remove <role> <member> [reason]
        /role removes  <role> <members> [reason]
        /role in <role>
    """

    def __init__(self, bot) -> None:
        self.svc = RoleService()
        self.answers = {
            1:  ("✅", "Роль {role} {action} для {user}", 0x57F287),
            2:  ("⚠️", "{user} уже {state} роль {role}", 0xFEE75C),
            -1:  ("❌", "Недостаточно прав для {action} роли {role} у {user}", 0xED4245),
            0:  ("❗", "Не удалось {action} роль {role} для {user}",          0xFAA81A),
        }

    def _build_answer(self, code: int, user: str, role: str, action: str, state: str = "") -> str:
        emoji, template, _ = self.answers[code]
        return f"{emoji} {template.format(user=user, role=role, action=action, state=state)}"



    role = SlashCommand(
        name="role",
        description="Управление ролями",
        default_member_permissions=_role_perms
    )



    @role.subcommand(sub_cmd_name="add", sub_cmd_description="Добавить роль")
    @slash_option(name="role",
                  description="Роль",
                  opt_type=OptionType.ROLE,
                  required=True)
    @slash_option(name="member",
                  description="Участник",
                  opt_type=OptionType.USER,
                  required=True)
    @slash_option(name="reason",
                  description="Причина",
                  opt_type=OptionType.STRING,
                  required=False)
    async def cmd_add(self,
                      ctx: SlashContext,
                      role: Role,
                      member: Member,
                      reason: str = "Не указана"):

        """
            Добавляет роль пользователю

            /role add <role> <member> <reason>

            Arguments:
                role (Role): роль (обязательное поле)
                member (Member): пользователь (обязательное поле)
                reason (str): причина (необязательное поле)
        """

        res = await self.svc.add(member, ctx.author, role, reason)

        msg = self._build_answer(res, member.mention, role.mention, "выдана", "есть")
        await ctx.send(msg, ephemeral=True)



    @role.subcommand(sub_cmd_name="remove", sub_cmd_description="Удалить роль")
    @slash_option(name="role",
                  description="Роль",
                  opt_type=OptionType.ROLE,
                  required=True)
    @slash_option(name="member",
                  description="Участник",
                  opt_type=OptionType.USER,
                  required=True)
    @slash_option(name="reason",
                  description="Причина",
                  opt_type=OptionType.STRING,
                  required=False)
    async def cmd_remove(self,
                         ctx: SlashContext,
                         role: Role,
                         member: Member,
                         reason: str = "Не указана"):

        """
            Убирает роль у пользователя

            /role remove <role> <member> <reason>

            Arguments:
                role (Role): роль (обязательное поле)
                member (Member): Пользователь (обязательное поле)
                reason (str): причина (необязательное поле)
        """

        res = await self.svc.remove(member, ctx.author, role, reason)

        msg = self._build_answer(res, member.mention, role.mention, "убрана", "нет")
        await ctx.send(msg, ephemeral=True)



    @staticmethod
    def _parse_user_list(raw: str) -> list[int]:
        import re
        return [int(x) for x in re.findall(r'\d+', raw)]



    @role.subcommand(sub_cmd_name="adds", sub_cmd_description="Добавить роль нескольким")
    @slash_option(name="role",
                  description="Роль",
                  opt_type=OptionType.ROLE,
                  required=True)
    @slash_option(name="members",
                  description="Пользователи через пробел",
                  opt_type=OptionType.STRING,
                  required=True)
    @slash_option(name="reason",
                  description="Причина",
                  opt_type=OptionType.STRING,
                  required=False)
    async def cmd_adds(self,
                       ctx: SlashContext,
                       role: Role,
                       members: str,
                       reason: str = "Не указана"):

        """
            Добавляет роль пользователям

            /role adds <role> <member1 member2 ...> <reason>

            Arguments:
                role (Role): роль (обязательное поле)
                members (Member): пользователи (через пробел) (обязательное поле)
                reason (str): причина (необязательное поле)
        """

        ids     = self._parse_user_list(members)
        targets = [m for m in ctx.guild.members if m.id in ids]
        if not targets:
            return await ctx.send("Не найдено ни одного участника", ephemeral=True)

        results = await self.svc.add_many(ctx.guild, targets, role, reason)
        lines   = [self._build_answer(code, m.mention, role.mention, "выдана", "есть") for m, code in results]
        await ctx.send("\n".join(lines), ephemeral=True)



    @role.subcommand(sub_cmd_name="removes", sub_cmd_description="Удалить роль у нескольких")
    @slash_option(name="role",
                  description="Роль",
                  opt_type=OptionType.ROLE,
                  required=True)
    @slash_option(name="members",
                  description="Пользователи через пробел",
                  opt_type=OptionType.STRING,
                  required=True)
    @slash_option(name="reason",
                  description="Причина",
                  opt_type=OptionType.STRING,
                  required=False)
    async def cmd_removes(self,
                          ctx: SlashContext,
                          role: Role,
                          members: str,
                          reason: str = "Не указана"):

        """
            Убирает роль у пользователей

            /role removes <role> <member1 member2 ...> <reason>

            Arguments:
                role (Role): роль (обязательное поле)
                members (Member): пользователи (через пробел) (обязательное поле)
                reason (str): причина (необязательное поле)
        """

        ids     = self._parse_user_list(members)
        targets = [m for m in ctx.guild.members if m.id in ids]
        if not targets:
            return await ctx.send("Не найдено ни одного участника", ephemeral=True)

        results = await self.svc.remove_many(ctx.guild, targets, role, reason)
        lines   = [self._build_answer(code, m.mention, role.mention, "убрана", "нет") for m, code in results]
        await ctx.send("\n".join(lines), ephemeral=True)



    @role.subcommand(sub_cmd_name="in", sub_cmd_description="Кто имеет эту роль")
    @slash_option(name="role",
                  description="Роль",
                  opt_type=OptionType.ROLE,
                  required=True)
    async def cmd_in(self,
                     ctx: SlashContext,
                     role: Role):

        """
            Показывает всех пользователей с этой ролью

            /role in <role>

            Arguments:
                role (Role): роль (обязательное поле)
        """

        members = await self.svc.list_members(ctx.guild, role)
        if not members:
            return await ctx.send(f"Никто не имеет роли {role.mention}", ephemeral=True)

        lines = [f"{idx}. {m.mention} (`{m.id}`)" for idx, m in enumerate(members, 1)]
        embed = Embed(
            title=f"Пользователи с ролью {role.name}",
            description="\n".join(lines),
            color=role.color.value or 0x5865F2
        )
        embed.set_footer(text=f"Всего: {len(members)}")
        await ctx.send(embed=embed, ephemeral=True)