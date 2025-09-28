# main.py
import os
import discord
import asyncio
import subprocess
import traceback
from discord.ext import commands
from dotenv import load_dotenv

def get_current_branch():
    try:
        return subprocess.check_output(['git', 'rev-parse', '--abbrev-ref', 'HEAD']).decode('utf-8').strip()
    except Exception:
        return None

BRANCH_NAME = get_current_branch()
is_dev = BRANCH_NAME == 'dev'
env_path = '.env.dev' if is_dev else '.env.main'
load_dotenv(dotenv_path=env_path)
print(f"--- EXECUTANDO EM AMBIENTE: {BRANCH_NAME.upper() if BRANCH_NAME else 'PRODUÇÃO'} ---")

TOKEN = os.getenv('DISCORD_TOKEN')
if not TOKEN:
    print("ERRO CRÍTICO: Token do Discord não encontrado. Verifique seu arquivo .env.*")
    exit()

intents = discord.Intents.default()
intents.message_content = True

prefix="!"
if is_dev:
    prefix="&"
bot = commands.Bot(command_prefix=prefix, intents=intents)

async def load_cogs():
    """Carrega todos os cogs da pasta /cogs/."""
    for filename in os.listdir('./cogs'):
        if filename.endswith('.py') and not filename.startswith('__'):
            try:
                await bot.load_extension(f'cogs.{filename[:-3]}')
                print(f"Cog '{filename[:-3]}' carregado com sucesso.")
            except Exception as e:
                print(f"!!!!!!!!!! FALHA AO CARREGAR O COG {filename} !!!!!!!!!!")
                traceback.print_exc()
                print("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")

async def main():
    async with bot:
        await load_cogs()
        await bot.start(TOKEN)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Bot desligado.")