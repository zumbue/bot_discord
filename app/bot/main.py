import os
import discord
from discord.ext import commands
from dotenv import load_dotenv

load_dotenv()

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.presences = True

bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print("================================")
    print(f"🤖 Sistema inicializado com sucesso!")
    print(f"👤 Logado como: {bot.user}")
    print(f"🆔 ID do Bot: {bot.user.id}")
    print("=======================================")
    print("Aguardando eventos do servidor...")

if __name__ == "__main__":
    token = os.getenv('DISCORD_TOKEN')

    if not token:
        print('Sem token ou token incorreto')
    else:
        bot.run(token)    
    