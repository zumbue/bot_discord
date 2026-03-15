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
    print("=======================================")
    print(f"🤖 Sistema inicializado com sucesso!")
    print(f"👤 Logado como: {bot.user}")
    print(f"🆔 ID do Bot: {bot.user.id}")
    print("=======================================")
    print("Aguardando eventos do servidor...")

@bot.event
async def on_message(message):
    if message.author == bot.user:
        return

    usuario = message.author.name
    canal = message.channel.name
    texto = message.content

    print(f'[{canal}] {usuario} disse: {texto}')

    await bot.process_commands(message)


if __name__ == "__main__":
    token = os.getenv('DISCORD_TOKEN')

    if not token:
        print('Sem token ou token incorreto')
    else:
        bot.run(token)    
    