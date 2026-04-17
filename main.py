# main.py
import discord
from discord.ext import commands
from config import TOKEN
from cogs.tasks_cog import TasksCog
from logger_setup import setup_root_logger
import threading
import sys

# ── Logger ────────────────────────────────────────────────────────────────────
geral_logger = setup_root_logger()

def global_exception_handler(exc_type, exc_value, exc_traceback):
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return
    geral_logger.critical("EXCEÇÃO NÃO TRATADA (CRITICAL BUG)", exc_info=(exc_type, exc_value, exc_traceback))

sys.excepthook = global_exception_handler

# ── Bot ───────────────────────────────────────────────────────────────────────
intents = discord.Intents.default()
intents.messages       = True
intents.guilds         = True
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)


@bot.event
async def on_ready():
    geral_logger.info(f"Bot online | user={bot.user} | guilds={len(bot.guilds)}")
    print(f"[BOT] {bot.user} online em {len(bot.guilds)} servidor(es).")


async def setup_hook():
    """Chamado pelo discord.py dentro do event loop — lugar correto para add_cog."""
    await bot.add_cog(TasksCog(bot, geral_logger))

bot.setup_hook = setup_hook


def run_dashboard():
    """Inicia o dashboard Flask em thread separada."""
    from dashboard.app import create_app
    from config import DASHBOARD_HOST, DASHBOARD_PORT
    app = create_app()
    app.run(host=DASHBOARD_HOST, port=DASHBOARD_PORT, debug=False, use_reloader=False)


def main():
    # Dashboard em thread daemon — encerra junto com o processo principal
    dash_thread = threading.Thread(target=run_dashboard, daemon=True)
    dash_thread.start()
    geral_logger.info("Dashboard iniciado em thread separada.")

    bot.run(TOKEN)


if __name__ == "__main__":
    main()
