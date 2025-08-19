import os
import discord
from discord.ext import commands
from groq import Groq

# ======== Configurações ========
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

# Cliente Groq
groq_client = Groq(api_key=GROQ_API_KEY)

# Intents do Discord
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# Memória de contexto (por canal)
conversation_history = {}

# Prompt fixo (personalidade do bot)
SYSTEM_PROMPT = """
Você é **LeDe_concursos**, um professor virtual especialista em **concursos públicos**.  
Seu papel é atuar como **tutor particular de alto nível**, ajudando candidatos a aprender matérias como **Direito, Português, Matemática, Raciocínio Lógico, Atualidades, Legislação e Administração Pública**.  

Suas respostas devem ser:  
- **Claras, objetivas e didáticas** (explique como se estivesse em uma aula particular).  
- Sempre em **português**.  
- **Conectadas à realidade dos concursos**, trazendo exemplos de questões e explicando pegadinhas comuns.  
- Quando possível, **mostrar como as diferentes bancas** (FGV, Cebraspe, FCC, Vunesp, FURG, etc.) cobram o tema, com suas particularidades.  
- Ter **conhecimento amplo sobre os concursos da FURG**, especialmente os cargos de **Técnico Administrativo em Educação** e **Técnico em Assuntos Educacionais**, destacando o estilo de prova e os conteúdos mais cobrados.  
- **Dar dicas práticas** de estudo, memorização e resolução de provas.  

Regras de conduta:  
- Nunca saia do papel de professor para concursos.  
- Se perguntarem algo fora do tema, responda de forma breve, mas redirecione o foco para o estudo.  
- Seja **motivador**, lembrando ao estudante que **persistência e prática** são a chave para aprovação.  
"""

# ========= Eventos =========
@bot.event
async def on_ready():
    print(f"✅ Bot conectado como {bot.user}")


@bot.event
async def on_message(message: discord.Message):
    if message.author.bot:
        return

    # O bot responde somente quando for mencionado
    if bot.user in message.mentions:
        channel_id = message.channel.id

        # Inicializa histórico do canal se não existir
        if channel_id not in conversation_history:
            conversation_history[channel_id] = []

        # Adiciona a mensagem do usuário no histórico
        conversation_history[channel_id].append({"role": "user", "content": message.content})

        # Mantém só as últimas 10 mensagens
        conversation_history[channel_id] = conversation_history[channel_id][-10:]

        try:
            # Chamada ao Groq
            completion = groq_client.chat.completions.create(
                model="llama2-70b-4096",
                messages=[{"role": "system", "content": SYSTEM_PROMPT}] + conversation_history[channel_id],
                max_completion_tokens=800,
                temperature=0.7
            )

            resposta = completion.choices[0].message.content

            # Adiciona resposta ao histórico
            conversation_history[channel_id].append({"role": "assistant", "content": resposta})

            # Envia resposta no Discord
            await message.channel.send(resposta)

        except Exception as e:
            await message.channel.send("⚠️ Ocorreu um erro ao gerar a resposta.")
            print("Erro no Groq:", e)

    await bot.process_commands(message)


# ========= Comando ping =========
@bot.command()
async def ping(ctx):
    await ctx.send("🏓 Pong! Estou online e pronto para estudar com você!")


# ========= Iniciar bot =========
bot.run(DISCORD_TOKEN)
