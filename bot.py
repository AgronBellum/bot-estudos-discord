import os
import random
import discord
from discord.ext import commands
from groq import Groq
from dotenv import load_dotenv
from flask import Flask
import threading

# =============================
# 🔧 Configuração Inicial
# =============================
load_dotenv()
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

groq_client = Groq(api_key=GROQ_API_KEY)

intents = discord.Intents.default()
intents.messages = True
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

conversation_history = []

# =============================
# 🧠 Identidade do Bot
# =============================
BASE_PROMPT = """
# 🎓 Identidade
Você é **LeDe_concursos**, um assistente especializado em concursos com personalidade de **professor veterano**.

Seu estilo:
- 📘 **Didático** → Explica como se o aluno estivesse na sua sala.
- 🎯 **Adaptável** → Ajusta o tom conforme a banca.
- 💡 **Memorável** → Usa analogias e humor para fixar conteúdo.

# 🏛️ Estilos por Banca
- **CESPE/Cebraspe** → Questões de Certo/Errado, anulando se errar. Seja rigoroso.
- **FGV** → Enunciados longos, interpretativos. Use texto rebuscado.
- **FCC** → Questões objetivas, pegadinhas sutis.
- **Quadrix** → Bem diretas, cobrança de letra de lei.
- **Vunesp** → Questões medianas, foco em literalidade.
- **IBFC** → Mistura entre direto e interpretativo.
- **IADES** → Bem próximas das apostilas, estilo previsível.
- **Cesgranrio** → Bastante interpretação de texto.
- **FURG** → Banca própria, valoriza contexto regional e leis locais.
- **CPNU** → Questões modelo ENEM, contextualizadas.

# 🎉 Feedback ao Aluno
## ✅ Acerto
- "👏 **Mandou bem!** Até o CONSUN aprovaria essa resposta!"
- "Você e a **Lei 8.112/90** – dupla imbatível!"

## ❌ Erro
- "⚠️ **Quase!** A FURG adora cobrar esse detalhe do Art. 20..."
- "Tranquilo! Agora você sabe que **12 meses** é a chave do estágio probatório."

# 🗓️ Motivação
- "Hoje é dia de marcar **X** no gabarito! Bora revisar os top 5 artigos da Lei 8.112?"
- "Você já venceu editais piores que esse, bora pra cima!"
"""

piadas_concursadas = [
    "📅 Por que o concurseiro não usa relógio? Porque ele já vive no 'tempo regulamentar' do edital!",
    "📖 Sabe como se chama quem estuda Lei 8.112/90 de trás pra frente? Um 211.8 oitól!"
]

# =============================
# 📂 Estrutura do Servidor
# =============================
server_structure = {
    "🏛️ Gerais": [
        "📢-avisos",
        "💬-bate-papo",
        "📎-links-úteis"
    ],
    "📚 Disciplinas Básicas": [
        "português",
        "raciocínio-lógico",
        "matemática",
        "informática",
        "direito-constitucional",
        "direito-administrativo",
        "direito-penal",
        "direito-processual-penal",
        "direito-civil",
        "direito-processual-civil",
        "direitos-humanos",
        "ética-no-serviço-público",
        "atualidades"
    ],
    "📝 Simulados": [
        "instruções",
        "simulados-cespe",
        "simulados-fgv",
        "simulados-fcc",
        "simulados-quadrix",
        "simulados-furg",
        "simulados-vunesp",
        "simulados-ibfc",
        "simulados-idecan",
        "simulados-iades",
        "simulados-cesgranrio",
        "simulados-cpnu",
        "simulados-outros"
    ],
    "📊 Bancas": [
        "cespe-cebraspe",
        "fgv",
        "fcc",
        "quadrix",
        "furg",
        "vunesp",
        "ibfc",
        "idecan",
        "iades",
        "cesgranrio",
        "funrio",
        "objetiva",
        "cpnu",
        "outros"
    ],
    "🎯 Concursos Específicos": [
        "trf4-2025",
        "tjrs-2025",
        "pf-agente",
        "prf-2026"
    ],
    "😂 Motivação": [
        "frases-motivacionais",
        "piadas-concurseiras"
    ]
}

useful_links = [
    "🔗 PCI Concursos → https://www.pciconcursos.com.br/",
    "🔗 QConcursos → https://www.qconcursos.com/",
    "🔗 Drive de Provas Antigas → [adicione seu link aqui]",
    "🔗 Estratégia Questões → https://questoes.estrategia.com/",
    "🔗 Gran Cursos Questões → https://questoes.grancursosonline.com.br/"
]

# =============================
# 🤖 Eventos
# =============================
@bot.event
async def on_ready():
    print(f"🤖 {bot.user.name} está online! Modo: Professor Concurseiro")

@bot.event
async def on_message(message):
    if message.author.bot:
        return

    if bot.user.mentioned_in(message):
        user_input = message.content.replace(f"<@{bot.user.id}>", "").strip()
        conversation_history.append({"role": "user", "content": user_input})
        if len(conversation_history) > 5:
            conversation_history.pop(0)

        try:
            messages = [
                {"role": "system", "content": BASE_PROMPT},
                *conversation_history
            ]

            response = groq_client.chat.completions.create(
                model="llama3-70b-8192",
                messages=messages,
                temperature=0.7,
                max_tokens=500
            )

            reply = response.choices[0].message.content

            if random.random() < 0.1:
                reply += f"\n\n{random.choice(piadas_concursadas)}"

            await message.channel.send(reply)

        except Exception as e:
            await message.channel.send(f"⚠️ Erro ao gerar resposta: {str(e)}")

    await bot.process_commands(message)

# =============================
# 📂 Comandos
# =============================
@bot.command()
async def piada(ctx):
    await ctx.send(random.choice(piadas_concursadas))

@bot.command()
@commands.has_permissions(administrator=True)
async def setup(ctx):
    guild = ctx.guild
    for category_name, channels in server_structure.items():
        category = discord.utils.get(guild.categories, name=category_name)
        if not category:
            category = await guild.create_category(category_name)
        for channel_name in channels:
            existing_channel = discord.utils.get(category.channels, name=channel_name)
            if not existing_channel:
                await guild.create_text_channel(channel_name, category=category)
    await ctx.send("✅ Estrutura de estudos criada com sucesso!")

@bot.command()
async def simulado(ctx, banca: str, *, tema: str = "geral"):
    try:
        simulado_prompt = f"""
        Você é a banca {banca}.
        Crie 5 questões sobre o tema: {tema}.
        Use o formato oficial da banca.
        Depois forneça o gabarito comentado.
        """

        response = groq_client.chat.completions.create(
            model="llama3-70b-8192",
            messages=[
                {"role": "system", "content": BASE_PROMPT},
                {"role": "user", "content": simulado_prompt}
            ],
            temperature=0.7,
            max_tokens=1000
        )

        simulado_text = response.choices[0].message.content

        # Divide em Perguntas e Gabarito
        if "Gabarito" in simulado_text:
            partes = simulado_text.split("Gabarito", 1)
            perguntas = partes[0]
            gabarito = "Gabarito" + partes[1]
        else:
            perguntas = simulado_text
            gabarito = "(⚠️ A IA não separou gabarito desta vez)"

        embed_perguntas = discord.Embed(
            title=f"📝 Simulado - {banca.upper()}",
            description=f"Tema: **{tema}**\n\n{perguntas[:4000]}",
            color=discord.Color.blue()
        )
        embed_perguntas.set_footer(text="Questões geradas com IA para prática 📚")

        embed_gabarito = discord.Embed(
            title="📖 Gabarito Comentado",
            description=gabarito[:4000],
            color=discord.Color.green()
        )

        await ctx.send(embed=embed_perguntas)
        await ctx.send(embed=embed_gabarito)

    except Exception as e:
        await ctx.send(f"⚠️ Erro ao gerar simulado: {str(e)}")

# =============================
# 🌐 Servidor Flask Fake
# =============================
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot LeDe_concursos rodando!"

def run_web():
    app.run(host="0.0.0.0", port=10000)

threading.Thread(target=run_web).start()

# =============================
# ▶️ Rodar Bot
# =============================
bot.run(DISCORD_TOKEN)
