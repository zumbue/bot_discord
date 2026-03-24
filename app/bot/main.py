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

# INICIALIZANDO O MOTOR DE IA
print("🧠 Baixando/Carregando o modelo de Inteligência Artificial...")
print("(Isso pode demorar um pouquinho na primeira vez)")
# O modelo 'all-MiniLM-L6-v2' gera exatamente 384 dimensões
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
    # 1. Ignora o próprio bot
    if message.author == bot.user:
        return

    # 2. Ignora mensagens vazias (Gifs, figurinhas, anexos sem texto)
    if not message.content or not message.content.strip():
        await bot.process_commands(message)
        return

    # 3. Trava de segurança para DMs ou canais sem nome
    canal_nome = getattr(message.channel, "name", "Mensagem Direta")
    usuario_nome = message.author.name
    texto = message.content

    print(f"Recebido de {usuario_nome}: {texto[:30]}...")

    # MEMÓRIA SEMÂNTICA
    try:
        vetor_matematico = ai_model.encode(texto).tolist()
    except Exception as e:
        print(f"❌ Erro ao passar texto na IA: {e}")
        await bot.process_commands(message)
        return

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

            nova_msg = Mensagem(
                message_id=message.id,
                user_id=usuario_db.id,
                channel_id=message.channel.id,
                content=texto,
                embedding=vetor_matematico,
                timestamp=message.created_at.replace(tzinfo=None)
            )
            
            session.add(nova_msg)
            await session.commit()
            print("✅ Nova mensagem salva com sucesso no banco!")
            
        except Exception as e:
            print(f"❌ Erro crítico no banco de dados: {e}")
            await session.rollback()

    # Processa os comandos normalmente (ex: !status)
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

@bot.command(name="lembrar")
async def lembrar(ctx, *, busca: str):
    # Avisa no chat que está pensando
    mensagem_espera = await ctx.send("🧠 Vasculhando minhas memórias semânticas...")

    try:
        # 384 dimensões
        vetor_busca = ai_model.encode(busca).tolist()

        async with AsyncSessionLocal() as session:
            # Busca as 3 mensagens com o menor "ângulo" de diferença
            resultados = await session.execute(
                select(Mensagem, Usuario.username)
                .join(Usuario)
                .order_by(Mensagem.embedding.cosine_distance(vetor_busca)) # Ordena pela similaridade
                .limit(3) # Traz o Top 3
            )
            
            mensagens_encontradas = resultados.all()

            # 3. Formata a resposta
            if not mensagens_encontradas:
                await mensagem_espera.edit(content="Não encontrei nenhuma memória parecida com isso.")
                return

            resposta = f"🔍 **Resultados para:** '{busca}'\n\n"
            
            for msg, autor_nome in mensagens_encontradas:
                data_formatada = msg.timestamp.strftime("%d/%m/%Y %H:%M")
                resposta += f"👤 **{autor_nome}** ({data_formatada}): {msg.content}\n"

            # Edita a mensagem de espera com os resultados finais
            await mensagem_espera.edit(content=resposta)

    except Exception as e:
        print(f"❌ Erro na busca vetorial: {e}")
        await mensagem_espera.edit(content="Ocorreu um erro ao acessar o banco de memórias.")

@bot.command(name="sincronizar")
async def sincronizar(ctx, limite: int = 999999):
    await ctx.send(f"⏳ Iniciando a leitura das últimas {limite} mensagens...")
    salvas = 0
    ignoradas = 0

    async with AsyncSessionLocal() as session:
        async for msg in ctx.channel.history(limit=limite):
            if msg.author == bot.user or not msg.content.strip():
                continue

            try:
                result = await session.execute(
                    select(Mensagem).where(Mensagem.message_id == msg.id)
                )
                if result.scalars().first():
                    ignoradas += 1
                    continue
                
                res_user = await session.execute(
                    select(Usuario).where(Usuario.discord_id == msg.author.id)
                )
                usuario_db = res_user.scalars().first()
                
                if not usuario_db:
                    usuario_db = Usuario(discord_id=msg.author.id, username=msg.author.name)
                    session.add(usuario_db)
                    await session.commit()
                    await session.refresh(usuario_db)
                
                vetor = ai_model.encode(msg.content).tolist()
                
                # TEMPO ISOLADO
                data_limpa = msg.created_at.replace(tzinfo=None)

                nova_msg = Mensagem(
                    message_id=msg.id,
                    user_id=usuario_db.id,
                    channel_id=msg.channel.id,
                    content=msg.content,
                    embedding=vetor,
                    timestamp=data_limpa
                )
                session.add(nova_msg)
                await session.commit()
                salvas += 1
                print(f"📥 Processado: {msg.author.name} - {msg.content[:30]}...")

            except Exception as e:
                print(f"❌ Erro na msg {msg.id}: {e}")
                await session.rollback()

    await ctx.send(f"✅ Sincronização: **{salvas}** salvas, **{ignoradas}** ignoradas.")

if __name__ == "__main__":
    token = os.getenv('DISCORD_TOKEN')
    if not token:
        print('Sem token ou token incorreto')
    else:
        bot.run(token)
