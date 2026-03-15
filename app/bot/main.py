import os
import discord
from discord.ext import commands
from dotenv import load_dotenv
from sqlalchemy import select

from app.db.database import init_db, AsyncSessionLocal
from app.db.models import Usuario, Mensagem

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
    
    print("⚙️  Conectando ao Banco de Dados...")
    await init_db()
    
    print("=======================================")
    print("Aguardando eventos do servidor...")

@bot.event
async def on_message(message):
    if message.author == bot.user:
        return

    usuario_nome = message.author.name
    canal_nome = message.channel.name
    texto = message.content

    print(f"[{canal_nome}] {usuario_nome} disse: {texto}")

    async with AsyncSessionLocal() as session:
        try:
            result = await session.execute(
                select(Usuario).where(Usuario.discord_id == message.author.id)
            )
            usuario_db = result.scalars().first()

            if not usuario_db:
                usuario_db = Usuario(
                    discord_id=message.author.id, 
                    username=message.author.name
                )
                session.add(usuario_db)
                await session.commit()
                await session.refresh(usuario_db)

            nova_mensagem = Mensagem(
                message_id=message.id,
                user_id=usuario_db.id,
                channel_id=message.channel.id,
                content=message.content
            )
            session.add(nova_mensagem)
            await session.commit()
            print("✅ Mensagem salva no banco com sucesso!")
            
        except Exception as e:
            print(f"❌ Erro ao salvar no banco: {e}")
            await session.rollback()

    await bot.process_commands(message)

if __name__ == "__main__":
    token = os.getenv('DISCORD_TOKEN')
    if not token:
        print('Sem token ou token incorreto')
    else:
        bot.run(token)