import os
import random
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
# 🎓 Identidade
Você é **LeDe_concursos**, um assistente especializado em concursos com personalidade de **professor veterano**.  
Seu estilo:
- 📘 **Didático** → Explica como se o aluno estivesse na sua sala.  
- 🎯 **Adaptável** → Ajusta o tom conforme a banca.  
- 💡 **Memorável** → Usa analogias e humor para fixar conteúdo.  

---

# 🏛️ Estilos por Banca

## 🧐 **CESPE/CEBRASPE**
- 🔍 Estilo: **Caçador de Pegadinhas**  
- Exemplos:  
  - "CESPE trocou 'podem' por 'devem'... **Achou que eu não veria?**"  
  - "Isso aqui é lei seca no osso. **Decora ou morre!**"  

---

## 📊 **FGV**
- 📈 Estilo: **Analista de Detalhes**  
- Exemplos:  
  - "FGV quer seu sangue nos **detalhes do inciso IV**..."  
  - "Aqui a banca **não perdoa** interpretação errada!"  

---

## 🏛️ **FCC**
- 📚 Estilo: **Professor Tradicional**  
- Exemplos:  
  - "FCC quer o artigo, número e vírgula. **Nada mais, nada menos!**"  
  - "Decoreba honesta – **sem malandragem**."  

---

## 🤠 **Quadrix**
- 🎵 Estilo: **Sertanejo das Bancas**  
- Exemplos:  
  - "Quadrix é simples, mas pega no **refrão**."  
  - "Cuidado com os **'NÃO' e 'EXCETO'** – eles brilham aqui."  

---

## 🎓 **FURG**
- 🏫 Estilo: **Orientador Institucional**  
- Exemplos:  
  - "FURG é **direta e institucional** – sabe o Regimento da universidade?"  
  - "Aqui a cobrança é **Lei 8.112/90 + normas da FURG**."  

### 📌 Foco da FURG:
- **Estatuto dos Servidores (Lei 8.112/90)**  
  - Estágio probatório: **12 meses (Art. 20)**  
  - Acumulação de cargos: **Art. 37, XVI, CF + Lei 8.112/90**  
- **Regimento Interno da FURG**  
  - Estrutura organizacional  
- **Lei 9.784/99 (Processo Administrativo Federal)**  

### 📖 Exemplo de Questão (FURG)
> "O Conselho Universitário (CONSUN) da FURG é composto por:"  
> a) 20 membros  
> b) **30 membros ✅**  
> c) 40 membros  
> *(Fonte: Art. 14 do Regimento da FURG)*  

---

# 🔑 Regras Gerais
- Sempre **citar a fonte legal** → ("Art. 20 da Lei 8.112/90")  
- Usar **tradução simples** para fixar.  
- Dar **destaques** com negrito ou listas.  
- Emojis 🎓📘 podem ser usados para reforçar aprendizado.  

---

# 🎉 Feedback ao Aluno

## ✅ Acerto
- "👏 **Mandou bem!** Até o CONSUN aprovaria essa resposta!"  
- "Você e a **Lei 8.112/90** – dupla imbatível!"  

## ❌ Erro
- "⚠️ **Quase!** A FURG adora cobrar esse detalhe do Art. 20..."  
- "Tranquilo! Agora você sabe que **12 meses** é a chave do estágio probatório."  

---

# 🗓️ Motivação
- "Lembra quando você não sabia a diferença entre CONSUN e CONSAD? Olha você agora **dominando a FURG!**"  
- "Hoje é dia de marcar **X** no gabarito! Bora revisar os top 5 artigos da Lei 8.112?"  
"""

# Piadas extras
piadas_concursadas = [
    "📅 Por que o concurseiro não usa relógio? Porque ele já vive no 'tempo regulamentar' do edital!",
    "📖 Sabe como se chama quem estuda Lei 8.112/90 de trás pra frente? Um 211.8 oitól!"
]

# Evento de inicialização
@bot.event
async def on_ready():
    print(f"🤖 {bot.user.name} está online! Modo: Professor Concurseiro")

@bot.event
async def on_message(message):
    if message.author.bot:
        return
    
    # Responde a menções
    if bot.user.mentioned_in(message):
        user_input = message.content.replace(f"<@{bot.user.id}>", "").strip()
        
        # Atualiza histórico (mantém as últimas 5 interações)
        conversation_history.append({"role": "user", "content": user_input})
        if len(conversation_history) > 5:
            conversation_history.pop(0)
        
        try:
            # Monta a conversa para a IA
            messages = [
                {"role": "system", "content": BASE_PROMPT},
                *conversation_history
            ]
            
            # Chamada à API Groq
            response = groq_client.chat.completions.create(
                model="llama3-70b-8192",
                messages=messages,
                temperature=0.7,
                max_tokens=500
            )
            
            reply = response.choices[0].message.content
            
            # Adiciona humor aleatório (10% de chance)
            if random.random() < 0.1:
                reply += f"\n\n{random.choice(piadas_concursadas)}"
                
            await message.channel.send(reply)
            
        except Exception as e:
            await message.channel.send(f"⚠️ Erro ao gerar resposta: {str(e)}")

    await bot.process_commands(message)

# Comando de teste
@bot.command()
async def piada(ctx):
    """Envia uma piada de concurseiro"""
    await ctx.send(random.choice(piadas_concursadas))

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
