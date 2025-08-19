# bot.py
import os
import re
import json
import random
import asyncio
from typing import Dict, Any, List, Tuple

import discord
from discord.ext import commands
from discord import app_commands

from groq import Groq
from dotenv import load_dotenv

# --- Keep-alive para Render ---
from flask import Flask
import threading

# =============================
# Carregar variáveis de ambiente
# =============================
load_dotenv()
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

if not DISCORD_TOKEN:
    raise RuntimeError("Faltando DISCORD_TOKEN no ambiente.")
if not GROQ_API_KEY:
    raise RuntimeError("Faltando GROQ_API_KEY no ambiente.")

# =============================
# Groq client
# =============================
groq_client = Groq(api_key=GROQ_API_KEY)
GROQ_MODEL = "llama3-70b-8192"

# =============================
# Discord bot
# =============================
intents = discord.Intents.default()
intents.messages = True
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# =============================
# BASE PROMPT do assistente
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

# Histórico breve só para menções
conversation_history: List[Dict[str, str]] = []

# Piadas
piadas_concursadas = [
    "📅 Por que o concurseiro não usa relógio? Porque já vive no 'tempo regulamentar' do edital!",
    "📖 Como se chama quem estuda a 8.112/90 ao contrário? Um 211.8 oitól!"
]

# =============================
# Estrutura do servidor (setup)
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
# Util: IA chat helper
# =============================
async def chat_groq(messages: List[Dict[str, str]], max_tokens: int = 700, temperature: float = 0.6) -> str:
    resp = groq_client.chat.completions.create(
        model=GROQ_MODEL,
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens,
    )
    # Groq SDK: choices[0].message.content
    return resp.choices[0].message.content

# =============================
# Menções: responder sempre puxando pro estudo
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
            reply = await asyncio.to_thread(chat_groq, msgs, 500, 0.6)

            # 10% com piada
            if random.random() < 0.1:
                reply += f"\n\n{random.choice(piadas_concursadas)}"

            await message.channel.send(reply)
        except Exception as e:
            await message.channel.send(f"⚠️ Erro ao gerar resposta: {e}")

    await bot.process_commands(message)

# =============================
# Piada
# =============================
@bot.command()
async def piada(ctx: commands.Context):
    await ctx.send(random.choice(piadas_concursadas))

# =============================
# Setup de categorias/canais
# =============================
@bot.command()
@commands.has_permissions(administrator=True)
async def setup(ctx: commands.Context):
    guild = ctx.guild
    for category_name, channels in server_structure.items():
        category = discord.utils.get(guild.categories, name=category_name)
        if not category:
            category = await guild.create_category(category_name)
        for channel_name in channels:
            # discord transforma em slug; vamos comparar pelo 'name' mesmo
            existing = discord.utils.get(category.channels, name=channel_name)
            if not existing:
                await guild.create_text_channel(channel_name, category=category)
    await ctx.send("✅ Estrutura de estudos criada com sucesso!")

# =============================
# SIMULADO: IA + Embed + Botões
# =============================

# Armazena sessões de simulado: chave = (guild_id, channel_id, user_id)
SimKey = Tuple[int, int, int]
sim_sessions: Dict[SimKey, Dict[str, Any]] = {}

def extract_json(text: str) -> Any:
    """
    Tenta extrair JSON de:
    - bloco ```json ... ```
    - bloco ``` ... ```
    - texto direto
    Retorna dict carregado ou lança ValueError.
    """
    # ```json ... ```
    m = re.search(r"```json\s*(\{.*?\})\s*```", text, flags=re.S | re.I)
    if m:
        return json.loads(m.group(1))
    # ``` ... ```
    m = re.search(r"```+\s*(\{.*?\})\s*```+", text, flags=re.S | re.I)
    if m:
        return json.loads(m.group(1))
    # texto cru
    return json.loads(text)

def build_simulado_system_prompt() -> str:
    return (
        BASE_PROMPT
        + """

## Agora você irá **GERAR SIMULADO EM FORMATO JSON PURO**.

Regras IMPORTANTES:
- Sempre 5 questões.
- Se a banca não for CERTO/ERRADO (CESPE), use múltipla escolha com **5 alternativas (A–E)**.
- Para CESPE/CEBRASPE: formato **Certo/Errado**, sem alternativas A–E.
- Cada questão deve ter **enunciado**, **opcoes** (lista de strings) quando aplicável, **correta** (letra ou "Certo"/"Errado"), e **comentario** (objetivo e didático, com fontes quando possível).
- Nunca quebre o JSON. Não adicione texto fora do JSON.

Modelo de resposta (exemplos):

# Múltipla escolha (bancas tipo FGV/FCC/etc)
{
  "banca": "FGV",
  "formato": "multipla_escolha",
  "tema": "Direito Administrativo",
  "questoes": [
    {
      "enunciado": "Pergunta aqui...",
      "opcoes": ["A) ...", "B) ...", "C) ...", "D) ...", "E) ..."],
      "correta": "B",
      "comentario": "Explicação curta e referência legal."
    }
    // total: 5 questões
  ]
}

# Certo/Errado (CESPE/CEBRASPE)
{
  "banca": "CESPE",
  "formato": "certo_errado",
  "tema": "Direito Constitucional",
  "questoes": [
    {
      "enunciado": "Afirmação...",
      "opcoes": ["Certo", "Errado"],
      "correta": "Errado",
      "comentario": "Motivo e referência."
    }
  ]
}

Respeite o idioma PT-BR e o tema solicitado.
"""
    )

async def gerar_simulado_json(banca: str, tema: str) -> Dict[str, Any]:
    user_prompt = (
        f"Gerar simulado para a banca '{banca}' sobre o tema '{tema}'. "
        f"Responda **apenas** com o JSON no modelo exigido, sem texto extra."
    )
    messages = [
        {"role": "system", "content": build_simulado_system_prompt()},
        {"role": "user", "content": user_prompt},
    ]
    raw = await asyncio.to_thread(chat_groq, messages, 1200, 0.4)
    try:
        data = extract_json(raw)
    except Exception:
        # fallback: tentar forçar a IA a repetir em JSON puro
        messages.append({"role": "assistant", "content": raw})
        messages.append({
            "role": "user",
            "content": "Reenvie o mesmo conteúdo **somente como JSON válido**, sem comentários ou markdown."
        })
        raw2 = await asyncio.to_thread(chat_groq, messages, 1200, 0.2)
        data = extract_json(raw2)
    return data

def normalize_simulado(data: Dict[str, Any]) -> Dict[str, Any]:
    """Garante chaves esperadas e 5 questões."""
    banca = data.get("banca", "").upper()
    formato = data.get("formato", "multipla_escolha")
    tema = data.get("tema", "geral")
    questoes = data.get("questoes", [])
    # corta ou completa com dummy se não vier 5
    questoes = questoes[:5]
    while len(questoes) < 5:
        questoes.append({
            "enunciado": "Questão adicional (placeholder).",
            "opcoes": ["A) —", "B) —", "C) —", "D) —", "E) —"] if formato != "certo_errado" else ["Certo", "Errado"],
            "correta": "A" if formato != "certo_errado" else "Certo",
            "comentario": "Comentário não fornecido pela IA."
        })
    # normaliza alternativas
    for q in questoes:
        if formato == "certo_errado":
            q["opcoes"] = ["Certo", "Errado"]
            if q.get("correta") not in ["Certo", "Errado"]:
                q["correta"] = "Certo"
        else:
            # 5 alternativas A–E
            ops = q.get("opcoes") or []
            # remove prefixos A)/B) se vierem repetidos e repõe padronizado
            ops = [re.sub(r"^[A-Ea-e]\)\s*", "", s).strip() for s in ops]
            # garante 5
            while len(ops) < 5:
                ops.append("—")
            ops = ops[:5]
            q["opcoes"] = [f"{chr(65+i)}) {ops[i]}" for i in range(5)]
            # corrige letra
            corr = (q.get("correta") or "A").strip().upper()
            if corr not in list("ABCDE"):
                corr = "A"
            q["correta"] = corr
        if not q.get("comentario"):
            q["comentario"] = "Comentário não fornecido pela IA."
    return {
        "banca": banca,
        "formato": formato,
        "tema": tema,
        "questoes": questoes
    }

def make_question_embed(idx: int, total: int, banca: str, tema: str, q: Dict[str, Any]) -> discord.Embed:
    title = f"📝 Simulado {banca} — Q{idx+1}/{total}"
    desc = f"**Tema:** {tema}\n\n**Enunciado:** {q['enunciado']}"
    embed = discord.Embed(title=title, description=desc, color=discord.Color.blurple())
    if q.get("opcoes"):
        # Mostrar opções
        if isinstance(q["opcoes"], list):
            opts_text = "\n".join(q["opcoes"])
        else:
            opts_text = str(q["opcoes"])
        embed.add_field(name="Alternativas", value=opts_text, inline=False)
    embed.set_footer(text="Escolha sua resposta abaixo.")
    return embed

class QuestionView(discord.ui.View):
    def __init__(self, key: SimKey, timeout: float = 600.0):
        super().__init__(timeout=timeout)
        self.key = key
        sess = sim_sessions.get(key)
        if not sess:
            return
        formato = sess["data"]["formato"]
        # cria botões conforme formato
        if formato == "certo_errado":
            self.add_item(AnswerButton(label="Certo", style=discord.ButtonStyle.primary, custom_id="CERTO", key=key))
            self.add_item(AnswerButton(label="Errado", style=discord.ButtonStyle.danger, custom_id="ERRADO", key=key))
        else:
            for letter, style in zip(list("ABCDE"),
                                     [discord.ButtonStyle.primary,
                                      discord.ButtonStyle.secondary,
                                      discord.ButtonStyle.secondary,
                                      discord.ButtonStyle.secondary,
                                      discord.ButtonStyle.secondary]):
                self.add_item(AnswerButton(label=letter, style=style, custom_id=letter, key=key))

class AnswerButton(discord.ui.Button):
    def __init__(self, label: str, style: discord.ButtonStyle, custom_id: str, key: SimKey):
        super().__init__(label=label, style=style, custom_id=custom_id)
        self.sim_key = key

    async def callback(self, interaction: discord.Interaction):
        # Apenas o autor pode responder sua sessão
        sess = sim_sessions.get(self.sim_key)
        if not sess:
            return await interaction.response.send_message("Sessão expirada.", ephemeral=True)
        if interaction.user.id != self.sim_key[2]:
            return await interaction.response.send_message("Este simulado pertence a outro usuário.", ephemeral=True)

        idx = sess["index"]
        q = sess["data"]["questoes"][idx]
        formato = sess["data"]["formato"]

        # Determina resposta do usuário
        if formato == "certo_errado":
            user_answer = "Certo" if self.custom_id.upper() == "CERTO" else "Errado"
            correct = q["correta"]
            correct_bool = (user_answer == correct)
            chosen_label = user_answer
        else:
            user_answer = self.custom_id.upper()  # A..E
            correct = q["correta"].upper()
            correct_bool = (user_answer == correct)
            chosen_label = user_answer

        # Salva resposta
        sess["answers"].append({"idx": idx, "user": user_answer, "correct": correct, "ok": correct_bool})
        if correct_bool:
            sess["score"] += 1

        # Feedback rápido
        feedback = "✅ **Correto!**" if correct_bool else f"❌ **Incorreto.** Gabarito: **{correct}**"
        comment = q.get("comentario", "")
        await interaction.response.send_message(f"{feedback}\n\n**Comentário:** {comment}", ephemeral=True)

        # Próxima questão ou finalizar
        sess["index"] += 1
        if sess["index"] < len(sess["data"]["questoes"]):
            # Edita a mensagem com a próxima
            next_q = sess["data"]["questoes"][sess["index"]]
            embed = make_question_embed(sess["index"], len(sess["data"]["questoes"]), sess["data"]["banca"], sess["data"]["tema"], next_q)
            await interaction.message.edit(embed=embed, view=QuestionView(self.sim_key))
        else:
            # Finaliza e mostra resultado + gabarito
            total = len(sess["data"]["questoes"])
            score = sess["score"]
            banca = sess["data"]["banca"]
            tema = sess["data"]["tema"]

            result = discord.Embed(
                title=f"🏁 Resultado — Simulado {banca}",
                description=f"**Tema:** {tema}\n\n**Acertos:** {score}/{total}",
                color=discord.Color.green() if score >= total/2 else discord.Color.red()
            )

            # Monta gabarito resumido
            lines = []
            for i, q in enumerate(sess["data"]["questoes"]):
                correct = q["correta"] if sess["data"]["formato"] != "certo_errado" else q["correta"]
                user = sess["answers"][i]["user"]
                status = "✅" if sess["answers"][i]["ok"] else "❌"
                # Mostra só prefixo do enunciado pra não lotar
                enun = q["enunciado"].strip()
                if len(enun) > 110:
                    enun = enun[:110] + "..."
                lines.append(f"**Q{i+1}** {status} — Você: **{user}** | Gabarito: **{correct}**\n*{enun}*")

            result.add_field(name="Gabarito", value="\n\n".join(lines), inline=False)
            result.set_footer(text="Revisão concluída. Bora pra próxima! 🎓")

            # Apaga botões
            await interaction.message.edit(embed=result, view=None)

            # Limpa sessão
            sim_sessions.pop(self.sim_key, None)

@bot.command()
async def simulado(ctx: commands.Context, banca: str, *, tema: str = "geral"):
    """Gera simulado por banca e tema, com botões interativos.
    Uso: !simulado FGV Direito Administrativo
    """
    # Cria sessão única por user no canal
    key: SimKey = (ctx.guild.id if ctx.guild else 0, ctx.channel.id, ctx.author.id)
    if key in sim_sessions:
        return await ctx.send("⚠️ Você já tem um simulado em andamento neste canal. Termine-o antes de iniciar outro.")

    await ctx.trigger_typing()
    try:
        raw_data = await gerar_simulado_json(banca, tema)
        data = normalize_simulado(raw_data)
    except Exception as e:
        return await ctx.send(f"💥 Não consegui gerar o simulado agora. Tente novamente. Detalhe: {e}")

    # Cria sessão
    sim_sessions[key] = {
        "data": data,           # banca, formato, tema, questoes[5]
        "index": 0,             # questão atual
        "score": 0,             # acertos
        "answers": []           # lista de respostas
    }

    # Primeira questão
    q0 = data["questoes"][0]
    embed = make_question_embed(0, len(data["questoes"]), data["banca"], data["tema"], q0)
    view = QuestionView(key)
    await ctx.send(embed=embed, view=view)

# =============================
# Tratamento de erros amigável
# =============================
@bot.event
async def on_command_error(ctx: commands.Context, error: commands.CommandError):
    if isinstance(error, commands.CommandNotFound):
        await ctx.send("❌ Comando desconhecido! Tente: `!simulado`, `!piada`, `!setup`.")
    elif isinstance(error, commands.MissingPermissions):
        await ctx.send("⛔ Você não tem permissão para executar este comando.")
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send(f"⚠️ Faltou argumento! Exemplo: `!{ctx.command} FGV Direito Administrativo`")
    else:
        await ctx.send("💥 Erro interno! Já registrei aqui no console.")
        print(f"[ERRO] {error}")

# =============================
# Flask keep-alive (Render)
# =============================
app = Flask(__name__)

@app.route("/")
def home():
    return "Bot LeDe_concursos rodando!"

def run_web():
    app.run(host="0.0.0.0", port=10000)

threading.Thread(target=run_web, daemon=True).start()

# =============================
# RUN
# =============================
if __name__ == "__main__":
    bot.run(DISCORD_TOKEN)
