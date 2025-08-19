import os
import discord
from discord.ext import commands
from groq import Groq
from dotenv import load_dotenv
from flask import Flask
import threading

# Carregar variáveis de ambiente
load_dotenv()
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

# Configurar cliente Groq
groq_client = Groq(api_key=GROQ_API_KEY)

# Configurar intents do Discord
intents = discord.Intents.default()
intents.messages = True
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# Histórico de mensagens
conversation_history = []

# Prompt fixo para especialização do bot
BASE_PROMPT = """
Você é LeDe_concursos, um especialista em concursos públicos.
- Responda de forma didática, clara e aprofundada.
- Domine as principais bancas: CESPE, FGV, FCC, Quadrix e FURG.
- Para a FURG, tenha atenção especial às provas de Técnico Administrativo e Técnico em Assuntos Educacionais.
- Dê dicas práticas de resolução, chame atenção para pegadinhas e diferenças sutis que confundem candidatos.
- Seja humano, atencioso e motivador.
"""

# Evento de inicialização
@bot.event
async def on_ready():
    print(f"🤖 Bot {bot.user} está online!")

# Evento para responder quando for mencionado
@bot.event
async def on_message(message):
    if message.author.bot:
        return
    
    if bot.user.mentioned_in(message):
        user_input = message.content.replace(f"<@{bot.user.id}>", "").strip()

        # Salvar histórico (últimas 10 mensagens)
        conversation_history.append({"role": "user", "content": user_input})
        if len(conversation_history) > 10:
            conversation_history.pop(0)

        # Montar mensagens para enviar ao Groq
        messages = [{"role": "system", "content": BASE_PROMPT}] + conversation_history

        try:
            # Requisição ao Groq
            response = groq_client.chat.completions.create(
                model="llama3-70b-8192",
                messages=messages,
                max_tokens=500,
            )

            # 🔥 CORREÇÃO AQUI
            reply = response.choices[0].message.content
            await message.channel.send(reply)

        except Exception as e:
            await message.channel.send(f"⚠️ Ocorreu um erro ao gerar a resposta: {str(e)}")

    await bot.process_commands(message)

# --- Servidor Flask fake só pra Render não matar ---
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot LeDe_concursos rodando!"

def run_web():
    app.run(host="0.0.0.0", port=10000)

threading.Thread(target=run_web).start()

# Rodar bot
bot.run(DISCORD_TOKEN)
