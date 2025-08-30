import os
import requests
from bs4 import BeautifulSoup
from telegram import Bot
from telegram.error import TelegramError
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
PRECO_MAXIMO = float(os.getenv("PRECO_MAXIMO", 5))

if not BOT_TOKEN or not CHAT_ID:
    raise ValueError("❌ BOT_TOKEN ou CHAT_ID não configurados!")

bot = Bot(token=BOT_TOKEN)

PALAVRAS_CHAVE = ["blackcell", "cp", "pack"]
DATA_CORTE = datetime.strptime("2024-01-01", "%Y-%m-%d")
VISITADOS = set()  # evita repetições

def transacao_valida(texto, data_str):
    texto_lower = texto.lower()
    try:
        data = datetime.strptime(data_str, "%b %d, %Y")
    except:
        return False

    if any(p in texto_lower for p in ["cp", "pack"]) and data < DATA_CORTE:
        return False
    return any(p in texto_lower for p in PALAVRAS_CHAVE)

def buscar_anuncios(url):
    try:
        r = requests.get(url, timeout=10)
        r.raise_for_status()
    except Exception as e:
        print(f"❌ Erro ao acessar {url}: {e}")
        return []

    soup = BeautifulSoup(r.text, "html.parser")
    links = [a["href"] for a in soup.select("a.marketIndexItem--Title.PopupItemLink") if a.get("href")]
    return links

def processar_conta(link):
    if link in VISITADOS:
        return
    VISITADOS.add(link)

    try:
        r = requests.get(link, timeout=10)
        r.raise_for_status()
    except Exception as e:
        print(f"❌ Erro em {link}: {e}")
        return

    soup = BeautifulSoup(r.text, "html.parser")
    trs = soup.select("table tr.dataRow")
    transacoes_relevantes = []

    for tr in trs:
        tds = tr.find_all("td")
        if len(tds) >= 3:
            texto = tds[0].get_text(strip=True)
            data_elem = tds[2].find(class_="DateTime")
            if not data_elem:
                continue
            data_texto = data_elem.get("title", "").split(" at ")[0].strip()
            if transacao_valida(texto, data_texto):
                transacoes_relevantes.append(f"{texto} ({data_texto})")

    if transacoes_relevantes:
        preco_elem = soup.select_one("#price")
        preco = preco_elem.get_text(strip=True) if preco_elem else "N/A"

        try:
            preco_float = float(preco.replace("R$", "").replace(",", "."))
        except:
            preco_float = float("inf")

        if preco_float <= PRECO_MAXIMO:
            msg = f"🔗 {link}\n💰 Preço: {preco}\n📦 Transações:\n" + "\n".join(f"• {t}" for t in transacoes_relevantes)
            try:
                bot.send_message(chat_id=CHAT_ID, text=msg)
                print(f"✅ Conta enviada: {link}")
            except TelegramError as e:
                print(f"❌ Erro ao enviar Telegram: {e}")

# 🚀 Loop principal
CATEGORIAS = [
    "https://lzt.market/battlenet/?page=1",
]

for categoria_url in CATEGORIAS:
    pagina = 1
    while True:
        url_pag = re.sub(r"([?&]page=)\d+", f"?page={pagina}", categoria_url)
        print(f"📄 Página {pagina}: {url_pag}")
        links = buscar_anuncios(url_pag)
        if not links:
            print("⚠️ Nenhum anúncio visível. Encerrando categoria.")
            break
        for link in links:
            processar_conta(link)
        pagina += 1
