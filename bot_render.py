import os
import time
import re
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from telegram import Bot

# Configurações
PALAVRAS_CHAVE = ["blackcell", "cp", "pack"]
DATA_CORTE = datetime.strptime("2024-01-01", "%Y-%m-%d")
VISITADOS = set()

# Variáveis de ambiente
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
PRECO_MAXIMO = float(os.getenv("PRECO_MAXIMO", 5))

if not BOT_TOKEN or not CHAT_ID:
    raise ValueError("❌ BOT_TOKEN ou CHAT_ID não configurados!")

bot = Bot(token=BOT_TOKEN)

# Configurações do Chrome
chrome_options = Options()
chrome_options.add_argument("--headless=new")  # headless no servidor
chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument("--disable-dev-shm-usage")
chrome_options.add_argument("--disable-gpu")
chrome_options.add_argument("--disable-software-rasterizer")

driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)

# Função de validação
def transacao_valida(texto, data_str):
    texto_lower = texto.lower()
    try:
        data = datetime.strptime(data_str, "%b %d, %Y")
    except:
        return False
    if any(p in texto_lower for p in ["cp", "pack"]) and data < DATA_CORTE:
        return False
    return any(p in texto_lower for p in PALAVRAS_CHAVE)

# URL inicial
categoria_url = "https://lzt.market/battlenet/?page=1"
pagina = 1

while True:
    try:
        url_pag = re.sub(r"([?&]page=)\d+", f"?page={pagina}", categoria_url)
        print(f"📄 Página {pagina}: carregando {url_pag}...")
        driver.get(url_pag)
        time.sleep(1)  # espera JS carregar

        anuncios = driver.find_elements(By.CSS_SELECTOR, "a.marketIndexItem--Title.PopupItemLink")
        links = [a.get_attribute("href") for a in anuncios if a.get_attribute("href")]

        if not links:
            print("⚠️ Nenhum anúncio encontrado")
            break

        for link in links:
            if link in VISITADOS:
                continue
            VISITADOS.add(link)

            print(f"🔗 Visitando {link}")
            driver.get(link)
            time.sleep(0.2)

            trs = driver.find_elements(By.CSS_SELECTOR, "table tr.dataRow")
            transacoes_relevantes = []

            for tr in trs:
                tds = tr.find_elements(By.TAG_NAME, "td")
                if len(tds) >= 3:
                    texto = tds[0].text.strip()
                    try:
                        data_texto = tds[2].find_element(By.CLASS_NAME, "DateTime").get_attribute("title").split(" at ")[0].strip()
                    except:
                        continue

                    if transacao_valida(texto, data_texto):
                        transacoes_relevantes.append(f"{texto} ({data_texto})")

            if transacoes_relevantes:
                try:
                    preco_elem = driver.find_element(By.CSS_SELECTOR, "#price")
                    preco = float(preco_elem.text.replace("R$", "").replace(",", ".").strip())
                except:
                    preco = 0

                if preco <= PRECO_MAXIMO:
                    msg = f"💰 Preço: R${preco}\n🔗 {link}\n📦 Transações:\n" + "\n".join(transacoes_relevantes)
                    bot.send_message(chat_id=CHAT_ID, text=msg)
                    print("✅ Conta boa enviada para Telegram!")

        pagina += 1
        time.sleep(0.5)

    except KeyboardInterrupt:
        print("🛑 Bot parado manualmente")
        break
    except Exception as e:
        print(f"❌ Erro geral: {e}")
        break

driver.quit()
