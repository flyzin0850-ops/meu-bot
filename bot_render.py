import os
import re
import time
import logging
import requests
from telegram import Bot
from telegram.ext import Application, CommandHandler
import threading

# 🔹 Token e chat ID
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")  # seu ID ou do grupo

if not BOT_TOKEN or not CHAT_ID:
    raise ValueError("❌ BOT_TOKEN ou CHAT_ID não configurados!")

bot = Bot(token=BOT_TOKEN)

# Logs
logging.basicConfig(format="%(asctime)s - %(levelname)s - %(message)s", level=logging.INFO)

# Palavras-chave e preço máximo
PALAVRAS_CHAVE = ["blackcell", "cp", "pack"]
PRECO_MAXIMO = 5.0

# URL base da categoria
BASE_URL = "https://lzt.market/battlenet/"

# Função para validar transações
def transacao_valida(texto, preco_str):
    texto_lower = texto.lower()
    try:
        preco = float(preco_str.replace("R$", "").replace(",", ".").strip())
    except:
        return False
    if preco > PRECO_MAXIMO:
        return False
    return any(p in texto_lower for p in PALAVRAS_CHAVE)

# Comando /start
async def start(update, context):
    await update.message.reply_text("🤖 Bot rodando e monitorando anúncios! 🚀")

# Função de monitoramento turbo
def monitorar():
    vistos = set()  # links já enviados
    pagina = 1

    while True:
        try:
            url = f"{BASE_URL}?page={pagina}"
            r = requests.get(url, timeout=5)
            r.raise_for_status()
            html = r.text

            # Captura links e preços
            anuncios = re.findall(r'<a href="(https://lzt\.market/\d+/[^"]+)".*?</a>.*?id="price">(.*?)<', html, re.DOTALL)

            if not anuncios:
                pagina = 1  # volta para a primeira página se não houver anúncios
                time.sleep(0.5)
                continue

            for link, preco in anuncios:
                if (link, preco) in vistos:
                    continue

                if transacao_valida(link, preco):
                    msg = f"🔔 Conta boa encontrada!\n💰 Preço: {preco}\n🔗 {link}"
                    bot.send_message(chat_id=CHAT_ID, text=msg)
                    logging.info(f"Enviado: {link} | Preço: {preco}")

                vistos.add((link, preco))
                time.sleep(0.25)  # 4 anúncios por segundo

            pagina += 1

        except Exception as e:
            logging.error(f"Erro ao buscar anúncios: {e}")
            time.sleep(2)

# Main
def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))

    # Inicia monitoramento em thread separada
    threading.Thread(target=monitorar, daemon=True).start()

    app.run_polling()

if __name__ == "__main__":
    main()
