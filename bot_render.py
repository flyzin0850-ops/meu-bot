import os
import re
import time
import requests
from datetime import datetime
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

# Função para validar transações
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
        print(f"📄 Página {pagina}: buscando anúncios...")
        url_pag = re.sub(r"([?&]page=)\d+", f"?page={pagina}", categoria_url)
        response = requests.get(url_pag, timeout=10)
        if response.status_code != 200:
            print("⚠️ Erro ao acessar página")
            break

        html = response.text
        links = re.findall(r'href="(https://lzt\.market/\d+/[^"]+)"', html)

        if not links:
            print("⚠️ Nenhum anúncio encontrado")
            break

        for link in links:
            if link in VISITADOS:
                continue
            VISITADOS.add(link)
            print(f"🔗 {link}")
            try:
                r = requests.get(link, timeout=10)
                trs = re.findall(r"<tr class=\"dataRow.*?</tr>", r.text, re.DOTALL)
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
                    preco_match = re.search(r"id=\"price\">(.*?)</", r.text)
                    preco = float(preco_match.group(1).replace("R$", "").replace(",", ".").strip()) if preco_match else 0

                    if preco <= PRECO_MAXIMO:
                        msg = f"💰 Preço: R${preco}\n🔗 {link}\n📦 Transações:\n" + "\n".join(transacoes_relevantes)
                        bot.send_message(chat_id=CHAT_ID, text=msg)
                        print("✅ Conta boa enviada para Telegram!")

            except Exception as e:
                print(f"❌ Erro em {link}: {e}")
            time.sleep(0.05)  # rápido: 3–4 anúncios/segundo

        pagina += 1
        time.sleep(0.5)

    except KeyboardInterrupt:
        print("🛑 Bot parado manualmente")
        break
    except Exception as e:
        print(f"❌ Erro geral: {e}")
        break
