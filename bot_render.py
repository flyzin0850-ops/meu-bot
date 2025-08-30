import os
import logging
from telegram.ext import Application, CommandHandler

# 🔹 Pega o token do Render
BOT_TOKEN = os.getenv("BOT_TOKEN")

# ❌ Se não existir, levanta erro
if not BOT_TOKEN:
    raise ValueError("❌ BOT_TOKEN não encontrado! Configure no Render em Environment Variables.")

# 🔹 Logs básicos
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)

# 🔹 Função que responde ao /start
async def start(update, context):
    await update.message.reply_text("🤖 Olá! Bot rodando no Render ✅")

# 🔹 Função principal
def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.run_polling()

if __name__ == "__main__":
    main()
