import os
from interactions import Client, Intents
from dotenv import load_dotenv
from services.events.morning import MorningService


intents = Intents.DEFAULT | Intents.GUILD_MODERATION
bot = Client(intents=intents, sync_interactions=True,
             sync_ext=True, debug_scope="1282677851820134546",
             delete_unused_application_cmds=True)


load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "..", ".env"))

# Cogs
bot.load_extension("exts.mod.moderation")
bot.load_extension("exts.mod.role")
bot.load_extension("exts.mod.warn")
bot.load_extension("exts.events.events")
bot.load_extension("exts.events.movie")
bot.load_extension("exts.profile.profile")

# Инициализация сервиса утренних уведомлений
morning_service = MorningService()

@bot.event
async def on_ready():
    """Событие готовности бота"""
    print(f"Бот {bot.user} готов!")
    # Запускаем задачу ежедневных уведомлений
    morning_service.setup_morning_task(bot)

if __name__ == "__main__":
    token = os.getenv("DS_API")
    bot.start(token)