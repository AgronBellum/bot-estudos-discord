# simulado.py
import requests
from bs4 import BeautifulSoup
from groq import Groq
import random
import os
from dotenv import load_dotenv

load_dotenv()

# 🔑 Configuração Groq
groq = Groq(api_key=os.getenv("GROQ_API_KEY"))


# ------------------------------
# 1) Scraping (Qconcursos)
# ------------------------------
def buscar_questoes_qconcursos(qtd=5):
    """
    Busca questões do Qconcursos (exemplo simples).
    Retorna lista de tuplas: (enunciado, alternativas).
    """
    url = "https://www.qconcursos.com/questoes-de-concursos/disciplinas/direito-direito-constitucional"
    r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"})
    soup = BeautifulSoup(r.text, "html.parser")

    questoes = []
    blocos = soup.find_all("div", class_="question-enunciation", limit=qtd)

    for bloco in blocos:
        enunciado = bloco.get_text(strip=True)

        alternativas_tags = bloco.find_next("ul", class_="alternatives")
        if alternativas_tags:
            alternativas = [li.get_text(strip=True) for li in alternativas_tags.find_all("li")]
        else:
            alternativas = ["Alternativa A", "Alternativa B", "Alternativa C", "Alternativa D", "Alternativa E"]

        questoes.append((enunciado, alternativas))

    return questoes


# ------------------------------
# 2) IA gera gabarito
# ------------------------------
def analisar_com_ia(enunciado, alternativas):
    letras = ["A", "B", "C", "D", "E"]
    texto_alternativas = "\n".join([f"{letras[i]}) {alt}" for i, alt in enumerate(alternativas)])

    prompt = f"""
    Questão de concurso:

    {enunciado}

    Alternativas:
    {texto_alternativas}

    Responda:
    1. Qual alternativa é a correta?
    2. Justifique a resposta de forma objetiva, como faria uma banca de concurso.
    """

    resposta = groq.chat.completions.create(
        model="llama3-70b-8192",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=400,
    )

    return resposta.choices[0].message["content"]


# ------------------------------
# 3) Montar simulado
# ------------------------------
def gerar_simulado(qtd=5):
    questoes = buscar_questoes_qconcursos(qtd)
    resultado = "📚 **Simulado Oficial - Questões**\n\n"

    for i, (enunciado, alternativas) in enumerate(questoes, start=1):
        resposta_ia = analisar_com_ia(enunciado, alternativas)

        bloco = f"""
**Questão {i}**
---
📖 Enunciado:
{enunciado}

🔢 Alternativas:
A) {alternativas[0]}
B) {alternativas[1]}
C) {alternativas[2]}
D) {alternativas[3]}
E) {alternativas[4] if len(alternativas) > 4 else "N/A"}

✅ Gabarito IA:
{resposta_ia}

---
"""
        resultado += bloco

    return resultado
