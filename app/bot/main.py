import os
import discord
from discord.ext import commands
from dotenv import load_dotenv
from sqlalchemy import select, func, desc

# Imports do banco de dados
from app.db.database import init_db, AsyncSessionLocal
from app.db.models import Usuario, Mensagem

# Import da biblioteca de IA
from sentence_transformers import SentenceTransformer

load_dotenv()

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.presences = True

bot = commands.Bot(command_prefix="!", intents=intents)

# ==========================================
# 🧠 INICIALIZANDO O MOTOR DE IA
# ==========================================
print("🧠 Baixando/Carregando o modelo de Inteligência Artificial...")
print("(Isso pode demorar um pouquinho na primeira vez)")
# O modelo 'all-MiniLM-L6-v2' gera exatamente 384 dimensões (como definimos no banco)
ai_model = SentenceTransformer('all-MiniLM-L6-v2')

@bot.event
async def on_ready():
    print("=======================================")
    print(f"🤖 Sistema inicializado com sucesso!")
    print(f"👤 Logado como: {bot.user}")
    print("⚙️  Conectando ao Banco de Dados e verificando pgvector...")
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

    # ==========================================
    # 🪄 A MÁGICA DA MEMÓRIA SEMÂNTICA
    # ==========================================
    # Transforma o texto em um vetor matemático de 384 posições
    vetor_matematico = ai_model.encode(texto).tolist()

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

            # Salva a mensagem JUNTO com a interpretação vetorial
            nova_mensagem = Mensagem(
                message_id=message.id,
                user_id=usuario_db.id,
                channel_id=message.channel.id,
                content=message.content,
                embedding=vetor_matematico # <--- Guardando a coordenada matemática
            )
            session.add(nova_mensagem)
            await session.commit()
            print("✅ Texto e Vetor (Memória IA) salvos com sucesso!")
            
        except Exception as e:
            print(f"❌ Erro ao salvar no banco: {e}")
            await session.rollback()

    await bot.process_commands(message)

@bot.command(name="status")
async def status(ctx, membro: discord.Member = None):
    alvo = membro or ctx.author
    async with AsyncSessionLocal() as session:
        try:
            result_user = await session.execute(
                select(Usuario).where(Usuario.discord_id == alvo.id)
            )
            usuario_db = result_user.scalars().first()

            total_mensagens = 0
            if usuario_db:
                result_count = await session.execute(
                    select(func.count(Mensagem.id)).where(Mensagem.user_id == usuario_db.id)
                )
                total_mensagens = result_count.scalar()

            result_ranking = await session.execute(
                select(Usuario.username, func.count(Mensagem.id).label('total'))
                .join(Mensagem)
                .group_by(Usuario.id)
                .order_by(desc('total'))
                .limit(5)
            )
            ranking_db = result_ranking.all()

            resposta = f"📊 **Status de {alvo.display_name}**\n"
            resposta += f"Total de mensagens enviadas: **{total_mensagens}**\n\n"
            
            resposta += "🏆 **Ranking de Atividade (Top 5)**\n"
            for posicao, (nome, total) in enumerate(ranking_db, start=1):
                resposta += f"{posicao}º - {nome}: {total} mensagens\n"

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