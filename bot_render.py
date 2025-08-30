import os
import re
import time
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from telegram import Bot
from telegram.ext import Application, CommandHandler, ContextTypes

# ----------------------------
# Variáveis de ambiente
# ----------------------------
BOT_TOKEN = os.environ.get("BOT_TOKEN")
CHAT_ID = int(os.environ.get("CHAT_ID"))
PORT = int(os.environ.get("PORT", 5000))
URL = os.environ.get("RENDER_EXTERNAL_URL")

if not BOT_TOKEN or not CHAT_ID or not URL:
    raise ValueError("❌ BOT_TOKEN, CHAT_ID ou RENDER_EXTERNAL_URL não configurados!")

bot = Bot(token=BOT_TOKEN)

# ----------------------------
# Configurações de scraping
# ----------------------------
PALAVRAS_CHAVE = ["blackcell", "cp", "pack"]
DATA_CORTE = datetime.strptime("2024-01-01", "%Y-%m-%d")

options = Options()
options.add_argument("--disable-gpu")
options.add_argument("--disable-software-rasterizer")
driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
wait = WebDriverWait(driver, 5)

# ----------------------------
# Funções utilitárias
# ----------------------------
def transacao_valida(texto, data_str):
    texto_lower = texto.lower()
    try:
        data = datetime.strptime(data_str, "%b %d, %Y")
    except:
        return False
    if any(p in texto_lower for p in ["cp", "pack"]) and data < DATA_CORTE:
        return False
    return any(p in texto_lower for p in PALAVRAS_CHAVE)

async def start(update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(chat_id=update.effective_chat.id, text="🤖 Bot rodando!")

async def buscar_anuncios(update=None, context=None):
    """
    Função principal para buscar anúncios e enviar alertas no Telegram
    """
    categoria_url = "https://lzt.market/battlenet/?page=1"  # você pode alterar ou pegar de input
    pagina = 1
    encontrados = 0

    while True:
        driver.get(categoria_url)
        time.sleep(0.2)
        html = driver.page_source
        links = re.findall(r'href="(https://lzt\.market/\d+/[^"]+)"', html)
        if not links:
            break

        for link in links:
            try:
                driver.get(link)
                time.sleep(0.1)
                html = driver.page_source
                trs = re.findall(r"<tr class=\"dataRow.*?</tr>", html, re.DOTALL)
                transacoes_relevantes = []

                for tr in trs:
                    cols = re.findall(r"<td.*?>(.*?)</td>", tr, re.DOTALL)
                    if len(cols) >= 3:
                        texto = re.sub(r"<.*?>", "", cols[0]).strip()
                        data_match = re.search(r'title="(.*?) at', tr)
                        if data_match:
                            data_texto = data_match.group(1).strip()
                            if transacao_valida(texto, data_texto):
                                transacoes_relevantes.append(f"{texto} ({data_texto})")

                if transacoes_relevantes:
                    preco_match = re.search(r'id="price">(.*?)<', html)
                    preco = preco_match.group(1).strip() if preco_match else "N/A"
                    mensagem = f"🔔 Nova conta!\n💰 Preço: {preco}\n🔗 {link}\n📦 Transações:\n" + "\n".join(transacoes_relevantes)
                    await bot.send_message(chat_id=CHAT_ID, text=mensagem)
                    encontrados += 1
            except:
                continue
            time.sleep(0.05)

        pagina += 1
        if "?" in categoria_url:
            categoria_url = re.sub(r"([?&]page=)\d+", f"?page={pagina}", categoria_url)
        else:
            categoria_url += f"?page={pagina}"

# ----------------------------
# Configuração Telegram
# ----------------------------
application = Application.builder().token(BOT_TOKEN).build()
application.add_handler(CommandHandler("start", start))

# Inicia scraping periodicamente
import asyncio
async def scraping_loop():
    while True:
        await buscar_anuncios()
        await asyncio.sleep(30)  # espera 30s entre verificações

application.create_task(scraping_loop())

# ----------------------------
# Inicia webhook
# ----------------------------
application.run_webhook(
    listen="0.0.0.0",
    port=PORT,
    url_path=BOT_TOKEN,
    webhook_url=f"{URL}/webhook/{BOT_TOKEN}"
)



 