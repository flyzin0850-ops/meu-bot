import os
import re
import time
import requests
from bs4 import BeautifulSoup
from datetime import datetime
from telegram import Bot

# 🔑 Pegando o token do Telegram e o chat_id das variáveis de ambiente
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
bot = Bot(token=TELEGRAM_TOKEN)

# Configurações
PALAVRAS_CHAVE = ["blackcell", "cp", "pack"]
DATA_CORTE = datetime.strptime("2024-01-01", "%Y-%m-%d")
PRECO_MAX = 5.0
URL_BASE = "https://lzt.market/battlenet/?page={}"

# Para evitar repetição
vistos = set()

def transacao_valida(texto, data_str):
    texto_lower = texto.lower()
    try:
        data = datetime.strptime(data_str, "%b %d, %Y")
    except:
        return False
    if any(p in texto_lower for p in ["cp", "pack"]) and data < DATA_CORTE:
        return False
    return any(p in texto_lower for p in PALAVRAS_CHAVE)

def buscar_pagina(pagina):
    url = URL_BASE.format(pagina)
    r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"})
    if r.status_code != 200:
        print(f"❌ Erro {r.status_code} na página {pagina}")
        return []

    soup = BeautifulSoup(r.text, "html.parser")
    links = []
    for a in soup.select("a.marketIndexItem--Title.PopupItemLink"):
        href = a.get("href")
        if href and href.startswith("https://lzt.market/"):
            links.append(href)
    return links

def processar_anuncio(url):
    if url in vistos:
        return
    vistos.add(url)

    r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"})
    if r.status_code != 200:
        return

    html = r.text

    # Preço
    preco_match = re.search(r'id="price">(.*?)</', html)
    preco = preco_match.group(1).strip() if preco_match else "N/A"

    try:
        preco_num = float(preco.replace("₽", "").replace(",", ".").strip())
    except:
        preco_num = 9999

    if preco_num > PRECO_MAX:
        return

    # Transações
    trs = re.findall(r"<tr class=\"dataRow.*?</tr>", html, re.DOTALL)
    transacoes_relevantes = []
    for tr in trs:
        cols = re.findall(r"<td.*?>(.*?)</td>", tr, re.DOTALL)
        if len(cols) >= 3:
            texto = re.sub(r"<.*?>", "", cols[0]).strip()
            data_match = re.search(r"title=\"(.*?) at", tr)
            if data_match:
                data_texto = data_match.group(1).strip()
                if transacao_valida(texto, data_texto):
                    transacoes_relevantes.append(f"{texto} ({data_texto})")

    if transacoes_relevantes:
        msg = f"✅ Conta encontrada!\n\n🔗 {url}\n💰 Preço: {preco}\n📦 Transações:\n"
        for t in transacoes_relevantes:
            msg += f" • {t}\n"
        print(msg)
        bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=msg)

def main():
    pagina = 1
    while True:
        print(f"\n📄 Buscando página {pagina}...")
        links = buscar_pagina(pagina)
        if not links:
            print("⚠️ Nenhum anúncio encontrado. Reiniciando...")
            pagina = 1
            time.sleep(10)
            continue

        for link in links:
            processar_anuncio(link)
            time.sleep(1)  # para não ser bloqueado

        pagina += 1
        if pagina > 200:  # limite pra não rodar infinito
            pagina = 1

if __name__ == "__main__":
    main()
