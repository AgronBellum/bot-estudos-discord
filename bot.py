# bot.py - Versão Completa Corrigida
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

if not DISCORD_TOKEN or not DISCORD_TOKEN.startswith('MT'):
    raise RuntimeError("Token Discord inválido ou faltando")
if not GROQ_API_KEY or len(GROQ_API_KEY) < 30:
    raise RuntimeError("Token Groq inválido ou faltando")

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
    return any(banca_valida in normalizar_banca(banca) for banca_valida in BANCAS_VALIDAS)

def validar_tema(tema: str) -> bool:
    """Validação básica do tema."""
    tema = tema.strip()
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
# Comandos do Bot
# =============================
@bot.event
async def on_ready():
    print(f"🤖 {bot.user.name} está online! Modo: Professor Concurseiro")

@bot.event
async def on_message(message: discord.Message):
    if message.author.bot:
        return

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

# =============================
# Sistema de Simulado
# =============================
sim_sessions: Dict[Tuple[int, int, int], Dict[str, Any]] = {}

def build_simulado_system_prompt() -> str:
    return BASE_PROMPT + """
## Agora você irá GERAR SIMULADO EM FORMATO JSON PURO.
Regras IMPORTANTES:
- Sempre 5 questões.
- Se a banca não for CERTO/ERRADO (CESPE), use múltipla escolha com 5 alternativas (A–E).
- Para CESPE/CEBRASPE: formato Certo/Errado, sem alternativas A–E.
- Cada questão deve ter enunciado, opcoes (quando aplicável), correta e comentario.
- Nunca quebre o JSON. Não adicione texto fora do JSON.
"""

async def gerar_simulado_json(banca: str, tema: str) -> Dict[str, Any]:
    try:
        user_prompt = f"Gerar simulado para {banca} sobre {tema}. Responda APENAS com JSON válido."
        messages = [
            {"role": "system", "content": build_simulado_system_prompt()},
            {"role": "user", "content": user_prompt}
        ]
        raw = await chat_groq(messages, 1200, 0.4)
        return extract_json(raw)
    except Exception as e:
        log_error(e, "gerar_simulado_json")
        raise

def normalize_simulado(data: Dict[str, Any]) -> Dict[str, Any]:
    """Garante estrutura consistente do simulado."""
    banca = (data.get("banca") or "").upper()
    formato = data.get("formato", "multipla_escolha")
    tema = data.get("tema", "geral")
    questoes = data.get("questoes", [])[:5]
    
    # Preenche com questões padrão se necessário
    while len(questoes) < 5:
        questoes.append({
            "enunciado": "Questão adicional (placeholder).",
            "opcoes": ["A) —", "B) —", "C) —", "D) —", "E) —"] if formato != "certo_errado" else ["Certo", "Errado"],
            "correta": "A" if formato != "certo_errado" else "Certo",
            "comentario": "Comentário não fornecido pela IA."
        })
    
    # Normaliza alternativas
    for q in questoes:
        if formato == "certo_errado":
            q["opcoes"] = ["Certo", "Errado"]
            q["correta"] = "Certo" if q.get("correta") not in ["Certo", "Errado"] else q["correta"]
        else:
            ops = [re.sub(r"^[A-Ea-e]\)\s*", "", str(s)).strip() for s in q.get("opcoes", [])][:5]
            while len(ops) < 5:
                ops.append("—")
            q["opcoes"] = [f"{chr(65+i)}) {ops[i]}" for i in range(5)]
            q["correta"] = "A" if q.get("correta") not in list("ABCDE") else q["correta"].upper()
        
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
        opts_text = "\n".join(q["opcoes"]) if isinstance(q["opcoes"], list) else str(q["opcoes"])
        embed.add_field(name="Alternativas", value=opts_text, inline=False)
    embed.set_footer(text="Escolha sua resposta abaixo.")
    return embed

class QuestionView(discord.ui.View):
    """View com botões para responder questões."""
    def __init__(self, key: Tuple[int, int, int], timeout: float = 300.0):
        super().__init__(timeout=timeout)
        self.key = key
        sess = sim_sessions.get(key)
        if not sess:
            return
        
        formato = sess["data"]["formato"]
        if formato == "certo_errado":
            self.add_item(AnswerButton(label="Certo", style=discord.ButtonStyle.primary, custom_id="CERTO", key=key))
            self.add_item(AnswerButton(label="Errado", style=discord.ButtonStyle.danger, custom_id="ERRADO", key=key))
        else:
            styles = [
                discord.ButtonStyle.primary,
                *[discord.ButtonStyle.secondary for _ in range(4)]
            ]
            for letter, style in zip("ABCDE", styles):
                self.add_item(AnswerButton(label=letter, style=style, custom_id=letter, key=key))

class AnswerButton(discord.ui.Button):
    def __init__(self, label: str, idx: int):
        super().__init__(label=label, style=discord.ButtonStyle.primary)
        self.idx = idx

    async def callback(self, interaction: discord.Interaction):
        user_id = str(interaction.user.id)
        session = sim_sessions.get(user_id)

        if not session:
            await interaction.response.send_message("⚠️ Sessão não encontrada.", ephemeral=True)
            return

        idx = session["current"]
        q = session["questions"][idx]

        # Resposta do usuário
        user_answer = self.label.split(")")[0]  # extrai só a letra A, B, C...
        correct = q["correta"].upper()

        # Obtém o texto completo das alternativas selecionadas
        user_label = next(
            (opt for opt in q["opcoes"] if str(opt).startswith(f"{user_answer})")),
            f"{user_answer}) [Alternativa não encontrada]"
        )
        correct_label = next(
            (opt for opt in q["opcoes"] if str(opt).startswith(f"{correct})")),
            f"{correct}) [Alternativa não encontrada]"
        )

        # Confere se acertou
        correct_bool = (user_answer == correct)

        # Pós-processa comentário para ficar didático
        comentario_texto = q.get("comentario", "Sem comentário disponível")
        if comentario_texto:
            comentario_texto = "📘 Explicação didática: " + comentario_texto

        # Atualização da sessão
        session["answers"].append({
            "idx": idx,
            "user": user_answer,
            "user_label": user_label,
            "correct": correct,
            "correct_label": correct_label,
            "ok": correct_bool,
            "comentario": comentario_texto
        })

        session["current"] += 1

        # Se ainda há questão, envia a próxima
        if session["current"] < len(session["questions"]):
            next_q = session["questions"][session["current"]]
            view = QuestionView(next_q, session["current"])
            await interaction.response.send_message(
                f"**Questão {session['current']+1}:** {next_q['enunciado']}",
                view=view,
                ephemeral=True
            )
        else:
            await interaction.response.send_message(
                "✅ Você finalizou o simulado! Use `!resultado` para ver seu desempenho.",
                ephemeral=True
            )


        # Próxima questão ou finalização
        sess["index"] += 1
        if sess["index"] < len(sess["data"]["questoes"]):
            next_q = sess["data"]["questoes"][sess["index"]]
            embed = make_question_embed(
                sess["index"],
                len(sess["data"]["questoes"]),
                sess["data"]["banca"],
                sess["data"]["tema"],
                next_q
            )
            await interaction.message.edit(embed=embed, view=QuestionView(self.sim_key))
        else:
            # Resultado final detalhado
            total = len(sess["data"]["questoes"])
            score = sess["score"]
            
            embed = discord.Embed(
                title=f"📊 Resultado Final - {sess['data']['banca']}",
                description=(
                    f"**Tema:** {sess['data']['tema']}\n"
                    f"**Acertos:** {score}/{total} ({score/total:.0%})\n"
                    f"**Nível:** {'👍 Aprovado!' if score >= total/2 else '👎 Precisa estudar mais'}"
                ),
                color=discord.Color.green() if score >= total/2 else discord.Color.red()
            )

            # Adiciona cada questão com detalhes
            for i, q in enumerate(sess["data"]["questoes"]):
                resp = sess["answers"][i]
                
                questao_info = [
                    f"**Enunciado:** {q['enunciado'][:150]}..." if len(q['enunciado']) > 150 else q['enunciado'],
                    "",
                    f"**Sua resposta:** {resp['user_label']}",
                    f"**Gabarito:** {resp['correct_label']}",
                    "",
                    f"**Explicação:** {q.get('comentario', 'Sem comentário disponível')}",
                    "―" * 30
                ]
                
                embed.add_field(
                    name=f"Questão {i+1} {'✅' if resp['ok'] else '❌'}",
                    value="\n".join(questao_info),
                    inline=False
                )

            embed.set_footer(text="Revise os comentários para consolidar seu aprendizado! 📚")
            await interaction.message.edit(embed=embed, view=None)
            sim_sessions.pop(self.sim_key, None)
@bot.command()
async def simulado(ctx: commands.Context, banca: str, *, tema: str = "geral"):
    """Inicia um simulado personalizado."""
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

        # Verifica sessão ativa
        key = (ctx.guild.id if ctx.guild else 0, ctx.channel.id, ctx.author.id)
        if key in sim_sessions:
            return await ctx.send("⚠️ Termine seu simulado atual antes de iniciar outro!")

        # Feedback de processamento
        msg = await ctx.send("⏳ Gerando seu simulado... (isso pode levar até 20 segundos)")

        # Gera simulado
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
        sim_sessions[key] = {
            "data": data,
            "index": 0,
            "score": 0,
            "answers": []
        }

        # Mostra primeira questão
        q0 = data["questoes"][0]
        embed = make_question_embed(0, len(data["questoes"]), data["banca"], data["tema"], q0)
        view = QuestionView(key)
        
        await msg.delete()
        await ctx.send(embed=embed, view=view)

    except Exception as e:
        log_error(e, "comando_simulado")
        await ctx.send("💥 Falha crítica ao criar simulado. Os desenvolvedores foram notificados.")
# ==========================================
# CLASSES DE INTERFACE (BOTÕES / VIEW) - CORRIGIDAS
# ==========================================

class AnswerButton(discord.ui.Button):
    def __init__(self, label: str, custom_id: str):
        super().__init__(label=label, style=discord.ButtonStyle.primary, custom_id=custom_id)

    async def callback(self, interaction: discord.Interaction):
        user_id = str(interaction.user.id)
        session = sim_sessions.get(user_id)

        if not session or session["current"] >= len(session["questions"]):
            await interaction.response.send_message("⚠️ Sessão não encontrada ou expirada.", ephemeral=True)
            return

        current_idx = session["current"]
        current_question = session["questions"][current_idx]

        # Processa resposta
        user_answer = self.custom_id
        correct_answer = current_question["correta"]
        is_correct = (user_answer.upper() == correct_answer.upper())

        # Encontra os textos completos das alternativas
        user_option = next((opt for opt in current_question["opcoes"] if opt.startswith(f"{user_answer})")), f"{user_answer}) [não encontrada]")
        correct_option = next((opt for opt in current_question["opcoes"] if opt.startswith(f"{correct_answer})")), f"{correct_answer}) [não encontrada]")

        # Registra resposta
        session["answers"].append({
            "question_idx": current_idx,
            "user_answer": user_answer,
            "user_option": user_option,
            "correct_answer": correct_answer,
            "correct_option": correct_option,
            "is_correct": is_correct,
            "comentario": current_question.get("comentario", "Sem comentário disponível")
        })

        session["current"] += 1

        # Responde à interação
        if is_correct:
            await interaction.response.send_message("✅ Resposta correta!", ephemeral=True)
        else:
            await interaction.response.send_message(f"❌ Resposta incorreta. A correta era: {correct_option}", ephemeral=True)

        # Prepara próxima questão ou finaliza
        if session["current"] < len(session["questions"]):
            # Agenda o envio da próxima questão
            asyncio.create_task(enviar_proxima_questao(interaction, user_id))
        else:
            # Finaliza o simulado
            asyncio.create_task(finalizar_simulado(interaction, user_id))

async def enviar_proxima_questao(interaction: discord.Interaction, user_id: str):
    """Envia a próxima questão após um pequeno delay"""
    await asyncio.sleep(2)  # Pequeno delay para feedback visual
    
    session = sim_sessions.get(user_id)
    if not session or session["current"] >= len(session["questions"]):
        return

    current_idx = session["current"]
    question = session["questions"][current_idx]
    
    view = QuestionView(question, current_idx)
    
    # Envia a próxima questão no canal original
    channel = interaction.channel
    await channel.send(f"**Questão {current_idx + 1}:** {question['enunciado']}", view=view)

async def finalizar_simulado(interaction: discord.Interaction, user_id: str):
    """Finaliza o simulado e mostra resultados"""
    await asyncio.sleep(2)
    
    session = sim_sessions.get(user_id)
    if not session:
        return

    channel = interaction.channel
    await channel.send("🎉 **Simulado finalizado!** Use `!resultado` para ver seu desempenho.")

class QuestionView(discord.ui.View):
    def __init__(self, question: Dict[str, Any], question_idx: int):
        super().__init__(timeout=180)  # 3 minutos de timeout
        self.question_idx = question_idx
        
        # Adiciona botões para cada alternativa
        for option in question["opcoes"]:
            letter = option.split(")")[0].strip()
            self.add_item(AnswerButton(label=option, custom_id=letter))

# ==========================================
# COMANDOS DO BOT - CORRIGIDOS
# ==========================================

@bot.command(name="simulado")
async def simulado(ctx: commands.Context, qtd: int = 5):
    """Inicia um simulado com N questões (default = 5)"""
    user_id = str(ctx.author.id)

    # Limita a quantidade de questões
    qtd = max(1, min(qtd, 10))  # Entre 1 e 10 questões

    # Verifica se já existe sessão
    if user_id in sim_sessions:
        await ctx.send("⚠️ Você já tem um simulado em andamento. Finalize-o primeiro.")
        return

    await ctx.send("📚 Gerando questões, aguarde...")

    questions = await gerar_questoes(qtd)
    if not questions:
        await ctx.send("💥 Erro ao gerar questões. Tente novamente.")
        return

    # Inicia nova sessão
    sim_sessions[user_id] = {
        "questions": questions,
        "current": 0,
        "answers": [],
        "start_time": discord.utils.utcnow()
    }

    # Envia primeira questão
    first_question = questions[0]
    view = QuestionView(first_question, 0)
    
    embed = discord.Embed(
        title="📝 Simulado Iniciado",
        description=f"**Questão 1/{len(questions)}**\n{first_question['enunciado']}",
        color=discord.Color.blue()
    )
    
    await ctx.send(embed=embed, view=view)

@bot.command(name="resultado")
async def resultado(ctx: commands.Context):
    """Mostra o resultado do simulado atual"""
    user_id = str(ctx.author.id)
    session = sim_sessions.get(user_id)

    if not session:
        await ctx.send("⚠️ Você não tem simulado em andamento. Use `!simulado` para começar.")
        return

    answers = session["answers"]
    total_questions = len(session["questions"])
    
    if not answers or len(answers) < total_questions:
        await ctx.send("⚠️ Você ainda não completou o simulado. Continue respondendo as questões.")
        return

    # Calcula resultados
    correct_answers = sum(1 for a in answers if a["is_correct"])
    score_percentage = (correct_answers / total_questions) * 100
    
    # Cria embed com resultados
    embed = discord.Embed(
        title="📊 Resultado do Simulado",
        description=f"**{ctx.author.display_name}** - {correct_answers}/{total_questions} acertos ({score_percentage:.1f}%)",
        color=discord.Color.green() if score_percentage >= 70 else discord.Color.orange() if score_percentage >= 50 else discord.Color.red()
    )
    
    # Adiciona detalhes por questão
    for i, answer in enumerate(answers):
        status = "✅" if answer["is_correct"] else "❌"
        embed.add_field(
            name=f"Questão {i+1} {status}",
            value=f"""**Sua resposta:** {answer['user_option']}
**Resposta correta:** {answer['correct_option']}
**Explicação:** {answer['comentario']}""",
            inline=False
        )
    
    # Limita a 25 fields (limite do Discord)
    if len(embed.fields) > 25:
        embed = discord.Embed(
            title="📊 Resultado do Simulado (Resumo)",
            description=f"**{correct_answers}/{total_questions}** acertos ({score_percentage:.1f}%)",
            color=embed.color
        )
        embed.add_field(name="Detalhes", value="*Muitas questões para mostrar detalhadamente*", inline=False)
    
    await ctx.send(embed=embed)
    
    # Limpa a sessão
    sim_sessions.pop(user_id, None)

@bot.command(name="cancelar")
async def cancelar_simulado(ctx: commands.Context):
    """Cancela o simulado atual"""
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
        await ctx.send("❌ Comando desconhecido! Tente: `!simulado`, `!piada`, `!setup`.")
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
