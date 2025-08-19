# bot.py - Versão Consolidada e Corrigida
import os
import re
import json
import random
import asyncio
import logging
import threading
import unicodedata
from typing import Dict, Any, List, Tuple

import discord
from discord.ext import commands
from groq import Groq
from dotenv import load_dotenv
from flask import Flask

# =============================
# Configuração Inicial
# =============================
# Logging
logging.basicConfig(
    filename='bot_errors.log',
    level=logging.ERROR,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

def log_error(error: Exception, context: str = ""):
    logging.error(f"{context} - {type(error).__name__}: {str(error)}", exc_info=True)

# Flask Keep-Alive
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot LeDe_concursos rodando!"

def run_web():
    try:
        app.run(host='0.0.0.0', port=10000, use_reloader=False)
    except OSError as e:
        if 'Address already in use' in str(e):
            print("⚠️ Servidor Flask já em execução")
        else:
            raise

threading.Thread(target=run_web, daemon=True).start()

# =============================
# Variáveis de Ambiente
# =============================
load_dotenv()
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

# Valida de maneira mais robusta (comprimento mínimo)
if not DISCORD_TOKEN or len(DISCORD_TOKEN) < 50:
    raise RuntimeError("Token do Discord inválido ou faltando (verifique .env)")
if not GROQ_API_KEY or len(GROQ_API_KEY) < 30:
    raise RuntimeError("Token Groq inválido ou faltando (verifique .env)")

# =============================
# Constantes e Configurações
# =============================
BANCAS_VALIDAS = {
    "CESPE", "CEBRASPE", "FGV", "FCC", "QUADRIX", "FURG",
    "VUNESP", "IBFC", "IDECAN", "IADES", "CESGRANRIO",
    "AOCP", "FUNRIO", "OBJETIVA", "CPNU"
}

GROQ_MODEL = "llama3-70b-8192"
groq_client = Groq(api_key=GROQ_API_KEY)
groq_semaphore = asyncio.Semaphore(5)  # Limite de chamadas simultâneas

# =============================
# Discord Bot
# =============================
intents = discord.Intents.default()
intents.messages = True
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# Histórico simples para menções
conversation_history: List[Dict[str, str]] = []

# =============================
# Base de Conhecimento
# =============================
BASE_PROMPT = """
# 🎓 Identidade
Você é **LeDe_concursos**, um assistente especializado em concursos com personalidade de **professor veterano**.
Estilo: 📘 Didático | 🎯 Adaptável por banca | 💡 Memorável (analogias e humor moderado).

# 🏛️ Estilos por Banca
- CESPE/CEBRASPE: Caçador de pegadinhas (cuidado com trocas "podem/devem"; certo/errado).
- FGV: Analista de detalhes (interpretação, letra de lei contextualizada).
- FCC: Professor tradicional (definições precisas, 5 alternativas).
- Quadrix: Objetivo, cuidado com "NÃO/EXCETO".
- FURG: Institucional (Lei 8.112/90, Lei 9.784/99, Regimento; linguagem direta).
- Outras (VUNESP, IBFC, IDECAN, IADES, CESGRANRIO, FUNRIO, OBJETIVA, AOCP, CPNu etc.) siga o padrão real (geralmente 5 alternativas A–E).

# Regras gerais de resposta
- Sempre puxe o papo para os estudos. Se a mensagem for genérica ("oi"), responda simpático e pergunte: "Qual banca/tema você quer focar hoje?"
- Nunca invente. Se não tiver certeza, diga e sugira onde verificar (lei seca, edital, sites de questões).
- Questões de múltipla escolha: **5 alternativas (A–E)** salvo banca explicitamente diferente.
- Sempre que citar norma: dê referência (ex.: Art. 20 da Lei 8.112/90) e traduza em linguagem simples.
"""

piadas_concursadas = [
    "📅 Por que o concurseiro não usa relógio? Porque já vive no 'tempo regulamentar' do edital!",
    "📖 Como se chama quem estuda a 8.112/90 ao contrário? Um 211.8 oitól!"
]

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
        "simulados-aocp",
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
        "aocp",
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

# =============================
# Funções Utilitárias
# =============================
def slugify_channel_name(name: str) -> str:
    """Converte nomes para formato válido no Discord."""
    nfkd = unicodedata.normalize("NFKD", name)
    s = "".join(ch for ch in nfkd if not unicodedata.combining(ch))
    s = s.lower()
    s = re.sub(r"\s+", "-", s)
    s = re.sub(r"[^a-z0-9\-]", "-", s)
    s = re.sub(r"-{2,}", "-", s)
    s = s.strip("-")
    return s or "canal"

def normalizar_banca(banca: str) -> str:
    """Padroniza o nome da banca."""
    banca = banca.upper().strip()
    if banca in {"CESPE", "CEBRASPE"}:
        return "CESPE/CEBRASPE"
    return banca

def validar_banca(banca: str) -> bool:
    """Verifica se a banca é suportada."""
    b = normalizar_banca(banca)
    base = { "CESPE/CEBRASPE" if x in {"CESPE","CEBRASPE"} else x for x in BANCAS_VALIDAS }
    return b in base

def validar_tema(tema: str) -> bool:
    """Validação básica do tema."""
    tema = (tema or "").strip()
    return 2 <= len(tema) <= 100

async def chat_groq(messages: List[Dict[str, str]], max_tokens: int = 700, temperature: float = 0.6) -> str:
    """Chamada à API Groq com limitação de concorrência."""
    async with groq_semaphore:
        try:
            resp = await asyncio.to_thread(
                groq_client.chat.completions.create,
                model=GROQ_MODEL,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens
            )
            return resp.choices[0].message.content
        except Exception as e:
            log_error(e, "chat_groq")
            raise

def extract_json(text: str) -> Any:
    """Extrai JSON de blocos de código ou texto puro."""
    patterns = [
        r"```json\s*(\{.*?\})\s*```",
        r"```+\s*(\{.*?\})\s*```+"
    ]
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.S | re.I)
        if match:
            try:
                return json.loads(match.group(1))
            except json.JSONDecodeError:
                continue
    return json.loads(text)

# =============================
# Simulado - Geração
# =============================
def build_simulado_system_prompt() -> str:
    return BASE_PROMPT + """
## Agora você irá GERAR SIMULADO EM FORMATO JSON PURO.
Regras IMPORTANTES:
- Sempre 5 questões.
- Se a banca não for CERTO/ERRADO (CESPE), use múltipla escolha com 5 alternativas (A–E).
- Para CESPE/CEBRASPE: formato Certo/Errado, sem alternativas A–E.
- Cada questão deve ter: enunciado, opcoes (quando aplicável), correta e comentario.
- Nunca quebre o JSON. Não adicione texto fora do JSON.
- Estrutura esperada:
{"banca":"...", "formato":"multipla_escolha|certo_errado", "tema":"...", "questoes":[
  {"enunciado":"...", "opcoes":["A) ...","B) ...","C) ...","D) ...","E) ..."]|"opcoes":["Certo","Errado"], "correta":"A|B|C|D|E|Certo|Errado", "comentario":"..."},
  ...
]}
"""

async def gerar_simulado_json(banca: str, tema: str) -> Dict[str, Any]:
    try:
        user_prompt = f"Gerar simulado para {banca} sobre {tema}. Responda APENAS com JSON válido."
        messages = [
            {"role": "system", "content": build_simulado_system_prompt()},
            {"role": "user", "content": user_prompt}
        ]
        raw = await chat_groq(messages, 1500, 0.4)
        return extract_json(raw)
    except Exception as e:
        log_error(e, "gerar_simulado_json")
        raise

def normalize_simulado(data: Dict[str, Any]) -> Dict[str, Any]:
    """Garante estrutura consistente do simulado."""
    banca = normalizar_banca((data.get("banca") or "").upper())
    formato = data.get("formato", "multipla_escolha")
    tema = data.get("tema", "geral")
    questoes = data.get("questoes", [])[:5]

    # Preenche com questões padrão se necessário
    while len(questoes) < 5:
        questoes.append({
            "enunciado": "Questão adicional (placeholder).",
            "opcoes": ["Certo", "Errado"] if formato == "certo_errado" else ["A) —", "B) —", "C) —", "D) —", "E) —"],
            "correta": "Certo" if formato == "certo_errado" else "A",
            "comentario": "Comentário não fornecido pela IA."
        })

    # Normaliza alternativas e campos
    for q in questoes:
        q["enunciado"] = str(q.get("enunciado", "Sem enunciado")).strip()
        if formato == "certo_errado":
            q["opcoes"] = ["Certo", "Errado"]
            q["correta"] = "Certo" if q.get("correta") not in ["Certo", "Errado"] else q["correta"]
        else:
            ops = [re.sub(r"^[A-Ea-e]\)\s*", "", str(s)).strip() for s in (q.get("opcoes") or [])][:5]
            while len(ops) < 5:
                ops.append("—")
            q["opcoes"] = [f"{chr(65+i)}) {ops[i]}" for i in range(5)]
            q["correta"] = (q.get("correta") or "A").upper()
            if q["correta"] not in list("ABCDE"):
                q["correta"] = "A"
        if not q.get("comentario"):
            q["comentario"] = "Comentário não fornecido pela IA."

    return {
        "banca": banca,
        "formato": formato,
        "tema": tema,
        "questoes": questoes
    }

def make_question_embed(idx: int, total: int, banca: str, tema: str, q: Dict[str, Any]) -> discord.Embed:
    """Cria embed para questões."""
    embed = discord.Embed(
        title=f"📝 Simulado {banca} — Q{idx+1}/{total}",
        description=f"**Tema:** {tema}\n\n**Enunciado:** {q['enunciado']}",
        color=discord.Color.blurple()
    )
    if q.get("opcoes"):
        if isinstance(q["opcoes"], list):
            opts_text = "\n".join(q["opcoes"])
        else:
            opts_text = str(q["opcoes"])
        embed.add_field(name="Alternativas", value=opts_text, inline=False)
    embed.set_footer(text="Clique nos botões para responder.")
    return embed

# =============================
# Sessões de Simulado
# =============================
# chave: user_id (str)  → sessão
sim_sessions: Dict[str, Dict[str, Any]] = {}

# =============================
# UI: Botões e Views (únicas)
# =============================
class AnswerButton(discord.ui.Button):
    def __init__(self, label: str, custom_id: str):
        # label mostrado no botão; custom_id é a letra (A..E) ou "CERTO"/"ERRADO"
        super().__init__(label=label, style=discord.ButtonStyle.primary, custom_id=custom_id)

    async def callback(self, interaction: discord.Interaction):
        user_id = str(interaction.user.id)
        session = sim_sessions.get(user_id)

        if not session or session["current"] >= len(session["questions"]):
            await interaction.response.send_message("⚠️ Sessão não encontrada ou expirada.", ephemeral=True)
            return

        idx = session["current"]
        q = session["questions"][idx]
        formato = session["formato"]

        # Resposta do usuário
        user_answer = self.custom_id  # "A".."E" ou "Certo"/"Errado"
        correct = q["correta"]

        # Mapeia rótulos completos
        if formato == "certo_errado":
            user_label = user_answer
            correct_label = correct
            is_correct = (user_answer == correct)
        else:
            # encontra "A) texto"
            user_label = next((opt for opt in q["opcoes"] if opt.startswith(f"{user_answer})")), f"{user_answer}) [não encontrada]")
            correct_label = next((opt for opt in q["opcoes"] if opt.startswith(f"{correct})")), f"{correct}) [não encontrada]")
            is_correct = (user_answer.upper() == correct.upper())

        # Registra
        session["answers"].append({
            "idx": idx,
            "user": user_answer,
            "user_label": user_label,
            "correct": correct,
            "correct_label": correct_label,
            "ok": is_correct,
            "comentario": q.get("comentario", "Sem comentário disponível")
        })

        # Feedback imediato
        if is_correct:
            await interaction.response.send_message("✅ Resposta correta!", ephemeral=True)
        else:
            await interaction.response.send_message(f"❌ Resposta incorreta. Gabarito: {correct_label}", ephemeral=True)

        # Próxima
        session["current"] += 1
        if session["current"] < len(session["questions"]):
            await enviar_proxima_questao(interaction, user_id)
        else:
            await finalizar_simulado(interaction, user_id)

class QuestionView(discord.ui.View):
    def __init__(self, question: Dict[str, Any], formato: str):
        super().__init__(timeout=300)
        if formato == "certo_errado":
            self.add_item(AnswerButton(label="Certo", custom_id="Certo"))
            self.add_item(AnswerButton(label="Errado", custom_id="Errado"))
        else:
            # Para múltipla escolha, botões com letras A–E
            for letter in "ABCDE":
                self.add_item(AnswerButton(label=letter, custom_id=letter))

async def enviar_proxima_questao(interaction: discord.Interaction, user_id: str):
    session = sim_sessions.get(user_id)
    if not session:
        return
    idx = session["current"]
    q = session["questions"][idx]
    embed = make_question_embed(idx, len(session["questions"]), session["banca"], session["tema"], q)
    view = QuestionView(q, session["formato"])
    await interaction.channel.send(embed=embed, view=view)

async def finalizar_simulado(interaction: discord.Interaction, user_id: str):
    session = sim_sessions.get(user_id)
    if not session:
        return

    total = len(session["questions"])
    acertos = sum(1 for a in session["answers"] if a["ok"])
    perc = (acertos / total) * 100 if total else 0.0

    embed = discord.Embed(
        title=f"📊 Resultado Final - {session['banca']}",
        description=(f"**Tema:** {session['tema']}\n"
                     f"**Acertos:** {acertos}/{total} ({perc:.1f}%)\n"
                     f"**Nível:** {'👍 Bom desempenho' if perc >= 70 else '🟠 Mediano' if perc >= 50 else '🔴 Precisa reforçar'}"),
        color=discord.Color.green() if perc >= 70 else discord.Color.orange() if perc >= 50 else discord.Color.red()
    )

    for i, q in enumerate(session["questions"]):
        if i >= 25:  # limite do Discord
            embed.add_field(name="…", value="*Muitas questões para detalhar em um único embed.*", inline=False)
            break
        resp = session["answers"][i]
        resumo_enunciado = (q["enunciado"][:150] + "...") if len(q["enunciado"]) > 150 else q["enunciado"]
        bloco = "\n".join([
            f"**Enunciado:** {resumo_enunciado}",
            f"**Sua resposta:** {resp['user_label']}",
            f"**Gabarito:** {resp['correct_label']}",
            f"**Explicação:** {resp.get('comentario','Sem comentário')}"
        ])
        status = "✅" if resp["ok"] else "❌"
        embed.add_field(name=f"Questão {i+1} {status}", value=bloco, inline=False)

    embed.set_footer(text="Revise os comentários para consolidar seu aprendizado! 📚")
    await interaction.channel.send(embed=embed)

    # Encerra sessão
    sim_sessions.pop(user_id, None)

# =============================
# Eventos
# =============================
@bot.event
async def on_ready():
    print(f"🤖 {bot.user.name} está online! Modo: Professor Concurseiro")

@bot.event
async def on_message(message: discord.Message):
    if message.author.bot:
        return

    # Resposta quando for mencionado @bot
    if bot.user.mentioned_in(message):
        user_input = message.content.replace(f"<@{bot.user.id}>", "").strip()
        conversation_history.append({"role": "user", "content": user_input})
        if len(conversation_history) > 6:
            conversation_history.pop(0)

        try:
            msgs = [{"role": "system", "content": BASE_PROMPT}, *conversation_history]
            reply = await chat_groq(msgs, 500, 0.6)
            if random.random() < 0.1:
                reply += f"\n\n{random.choice(piadas_concursadas)}"
            await message.channel.send(reply)
        except Exception as e:
            log_error(e, "on_message")
            await message.channel.send("💥 Erro interno! Já registrei aqui no console.")

    await bot.process_commands(message)

# =============================
# Comandos
# =============================
@bot.command()
async def piada(ctx: commands.Context):
    """Envia uma piada de concurseiro."""
    await ctx.send(random.choice(piadas_concursadas))

@bot.command()
@commands.has_permissions(administrator=True)
async def setup(ctx: commands.Context):
    """Configura a estrutura do servidor."""
    guild = ctx.guild
    if not guild:
        return await ctx.send("⚠️ Rode este comando dentro de um servidor.")
    created = 0
    for category_name, channels in server_structure.items():
        category = discord.utils.get(guild.categories, name=category_name)
        if not category:
            category = await guild.create_category(category_name)
        for original_name in channels:
            slug = slugify_channel_name(original_name)
            existing = discord.utils.get(category.channels, name=slug)
            if not existing:
                await guild.create_text_channel(slug, category=category)
                created += 1
    await ctx.send(f"✅ Estrutura criada! ({created} canais novos)")

@bot.command(name="simulado")
async def simulado_cmd(ctx: commands.Context, banca: str, *, tema: str = "geral"):
    """Inicia um simulado personalizado.
    Uso: !simulado FGV Direito Administrativo
    Para CESPE/CEBRASPE o formato é Certo/Errado. Demais bancas: A–E.
    """
    try:
        # Validação
        if not validar_banca(banca):
            bancas = ", ".join(sorted(BANCAS_VALIDAS))
            return await ctx.send(
                f"⚠️ Banca inválida! Escolha entre:\n{bancas}\n"
                f"Exemplo: `!simulado CESPE Direito Constitucional`"
            )
        if not validar_tema(tema):
            return await ctx.send("⚠️ Tema deve ter 2-100 caracteres. Ex: `Direito Administrativo`")

        user_id = str(ctx.author.id)
        if user_id in sim_sessions:
            return await ctx.send("⚠️ Você já tem um simulado em andamento. Use `!cancelar` para abortar.")

        # Feedback
        msg = await ctx.send("⏳ Gerando seu simulado...")

        try:
            banca_norm = normalizar_banca(banca)
            raw_data = await gerar_simulado_json(banca_norm, tema)
            data = normalize_simulado(raw_data)
        except json.JSONDecodeError:
            await msg.delete()
            return await ctx.send("🔴 Erro: Não consegui formatar o simulado. Tente um tema mais específico.")
        except Exception as e:
            await msg.delete()
            log_error(e, "simulado_json")
            return await ctx.send("⏳ Servidor de IA sobrecarregado. Tente novamente em 1 minuto.")

        # Inicia sessão
        sim_sessions[user_id] = {
            "banca": data["banca"],
            "formato": data["formato"],
            "tema": data["tema"],
            "questions": data["questoes"],
            "current": 0,
            "answers": [],
            "start_time": discord.utils.utcnow()
        }

        # Primeira questão
        q0 = data["questoes"][0]
        embed = make_question_embed(0, len(data["questoes"]), data["banca"], data["tema"], q0)
        view = QuestionView(q0, data["formato"])

        await msg.delete()
        await ctx.send(embed=embed, view=view)

    except Exception as e:
        log_error(e, "comando_simulado")
        await ctx.send("💥 Falha crítica ao criar simulado. Os desenvolvedores foram notificados.")

@bot.command(name="resultado")
async def resultado(ctx: commands.Context):
    """Mostra o resultado parcial/final do simulado atual."""
    user_id = str(ctx.author.id)
    session = sim_sessions.get(user_id)
    if not session:
        return await ctx.send("⚠️ Você não tem simulado em andamento. Use `!simulado` para começar.")

    total = len(session["questions"])
    if not session["answers"]:
        return await ctx.send("⚠️ Você ainda não respondeu nenhuma questão.")
    acertos = sum(1 for a in session["answers"] if a["ok"])
    perc = (acertos / total) * 100 if total else 0.0

    await ctx.send(f"📊 Parcial: **{acertos}/{total}** ({perc:.1f}%). Para encerrar automaticamente, responda todas as questões.")

@bot.command(name="cancelar")
async def cancelar_simulado(ctx: commands.Context):
    """Cancela o simulado atual."""
    user_id = str(ctx.author.id)
    if user_id in sim_sessions:
        sim_sessions.pop(user_id)
        await ctx.send("❌ Simulado cancelado.")
    else:
        await ctx.send("⚠️ Você não tem simulado em andamento.")

# =============================
# Tratamento de Erros Global
# =============================
@bot.event
async def on_command_error(ctx: commands.Context, error: commands.CommandError):
    if isinstance(error, commands.CommandNotFound):
        await ctx.send("❌ Comando desconhecido! Tente: `!simulado`, `!piada`, `!setup`, `!resultado`, `!cancelar`.")
    elif isinstance(error, commands.MissingPermissions):
        await ctx.send("⛔ Você não tem permissão para executar este comando.")
    elif isinstance(error, commands.MissingRequiredArgument):
        cmd = ctx.command.name if ctx.command else "simulado"
        await ctx.send(f"⚠️ Argumento faltando! Exemplo: `!{cmd} CESPE Direito Constitucional`")
    else:
        log_error(error, "on_command_error")
        await ctx.send("🔴 Erro interno. Já registrei os detalhes.")

# =============================
# Inicialização
# =============================
if __name__ == "__main__":
    try:
        bot.run(DISCORD_TOKEN)
    except Exception as e:
        log_error(e, "bot_startup")
        print(f"❌ Falha ao iniciar bot: {e}")
        raise
