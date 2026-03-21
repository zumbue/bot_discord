import os
import discord
from discord.ext import commands
from dotenv import load_dotenv
from sqlalchemy import select, func, desc

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

@bot.command(name="status")
async def status(ctx, membro: discord.Member = None):
    # Se você não marcar ninguém (ex: digitar apenas !status), ele pega os seus dados
    alvo = membro or ctx.author

    # Abre a conexão com o banco
    async with AsyncSessionLocal() as session:
        try:
            # ==========================================
            # 1. DADOS DO USUÁRIO ALVO
            # ==========================================
            # Primeiro, achamos o ID interno do usuário no banco
            result_user = await session.execute(
                select(Usuario).where(Usuario.discord_id == alvo.id)
            )
            usuario_db = result_user.scalars().first()

            total_mensagens = 0
            if usuario_db:
                # Conta quantas mensagens tem o ID desse usuário
                result_count = await session.execute(
                    select(func.count(Mensagem.id)).where(Mensagem.user_id == usuario_db.id)
                )
                total_mensagens = result_count.scalar() # scalar() extrai o número direto

            # ==========================================
            # 2. RANKING GERAL DO SERVIDOR (TOP 5)
            # ==========================================
            result_ranking = await session.execute(
                select(Usuario.username, func.count(Mensagem.id).label('total'))
                .join(Mensagem) # Junta a tabela de usuários com a de mensagens
                .group_by(Usuario.id) # Agrupa por pessoa
                .order_by(desc('total')) # Ordena do maior para o menor
                .limit(5) # Pega apenas os 5 primeiros
            )
            ranking_db = result_ranking.all() # Retorna uma lista com (Nome, Total)

            # ==========================================
            # 3. FORMATANDO A RESPOSTA NO DISCORD
            # ==========================================
            resposta = f"📊 **Status de {alvo.display_name}**\n"
            resposta += f"Total de mensagens enviadas: **{total_mensagens}**\n\n"
            
            resposta += "🏆 **Ranking de Atividade (Top 5)**\n"
            for posicao, (nome, total) in enumerate(ranking_db, start=1):
                # Formatação simples para mostrar a posição e o nome
                resposta += f"{posicao}º - {nome}: {total} mensagens\n"

            # O bot envia a mensagem de volta no mesmo canal onde o comando foi digitado
            await ctx.send(resposta)

        except Exception as e:
            print(f"❌ Erro ao buscar status no banco: {e}")
            await ctx.send("Ocorreu um erro ao buscar os dados no banco.")

if __name__ == "__main__":
    token = os.getenv('DISCORD_TOKEN')
    if not token:
        print('Sem token ou token incorreto')
    else:
        bot.run(token)