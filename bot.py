from telegram import Update
from telegram.ext import CommandHandler
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, MessageHandler, filters
from db import add_user, get_user_id, add_transaction, get_balance, get_transactions, get_transactions_week
import matplotlib.pyplot as plt
from io import BytesIO
import os
from dotenv import load_dotenv

load_dotenv()  


TOKEN = "SEU_TELEGRAM_TOKEN_AQUI"
SUPABASE_URL = "SUA_SUPABASE_URL_AQUI"
SUPABASE_KEY = "SUA_SUPABASE_KEY_AQUI"

# -------------------- COMANDOS DO BOT

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    nome = update.effective_user.first_name
    
   
    user_id = add_user(chat_id, nome)  

# ----------------Primeiras intruções do Bot
    mensagem = f"""
    Olá {nome}! 👋
    Seu usuário foi cadastrado com sucesso. ID: {user_id}

    Aqui estão algumas coisas que você pode fazer:
    💰 Ver saldo: digite 'saldo'
    ➕ Adicionar transação: digite 'adicionar <valor> <categoria> <tipo>'
    Ex: adicionar 50 alimentacao despesa
    📊 Ver gráfico de gastos: digite 'grafico'

    Vamos começar? 😄
    """
    await update.message.reply_text(mensagem)

async def saldo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user_id = get_user_id(chat_id)
    if user_id:
        saldo_atual = get_balance(user_id)
        await update.message.reply_text(f"💰 Seu saldo atual é: R$ {saldo_atual:.2f}")
    else:
        await update.message.reply_text("Usuário não encontrado. Use /start primeiro.")

async def adicionar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user_id = get_user_id(chat_id)
    if not user_id:
        await update.message.reply_text("Usuário não encontrado. Use /start primeiro.")
        return

    try:
        valor = float(context.args[0])
        categoria = context.args[1]
        tipo = context.args[2].lower()
        if tipo not in ["receita", "despesa"]:
            await update.message.reply_text("Tipo inválido! Use 'receita' ou 'despesa'.")
            return

        add_transaction(user_id, valor, categoria, tipo)
        await update.message.reply_text(f"✅ {tipo.capitalize()} de R$ {valor:.2f} adicionada na categoria '{categoria}'!")

    except (IndexError, ValueError):
        await update.message.reply_text("Uso correto: /adicionar <valor> <categoria> <tipo>")

# -------------------- Respostas mais naturais
async def responder(update: Update, context: ContextTypes.DEFAULT_TYPE):
    texto = update.message.text.lower()
    chat_id = update.effective_chat.id
    user_id = get_user_id(chat_id)

    await resumo_semanal(update, context)


    # enviar instruções a novos users
    if not user_id:
        nome = update.effective_user.first_name
        user_id = add_user(chat_id, nome)
        mensagem = f"""
Olá {nome}! 👋
Seu usuário foi cadastrado com sucesso. ID: {user_id}

Aqui estão algumas coisas que você pode fazer:
💰 Ver saldo: digite 'saldo'
➕ Adicionar transação: digite 'adicionar <valor> <categoria> <tipo>'
   Ex: adicionar 50 alimentacao despesa
📊 Ver gráfico de gastos: digite 'grafico'

Vamos começar? 😄
"""
        await update.message.reply_text(mensagem)
        return  # interrompe aqui, usuário novo só recebe instruções

    # ---------------- Usuário já cadastrado ----------------
    if "oi" in texto or "olá" in texto:
        await update.message.reply_text(f"Olá {update.effective_user.first_name}! Quer adicionar uma transação ou ver seu saldo?")

    elif "saldo" in texto:
        saldo_atual = get_balance(user_id)
        await update.message.reply_text(f"💰 Seu saldo atual é: R$ {saldo_atual:.2f}")

    elif "adicionar" in texto:
        partes = texto.split()
        if len(partes) == 4:
            try:
                valor = float(partes[1])
                categoria = partes[2]
                tipo = partes[3].lower()
                if tipo not in ["receita", "despesa"]:
                    await update.message.reply_text("Tipo inválido! Use 'receita' ou 'despesa'.")
                    return
                add_transaction(user_id, valor, categoria, tipo)
                await update.message.reply_text(f"✅ {tipo.capitalize()} de R$ {valor:.2f} adicionada na categoria '{categoria}'!")
            except ValueError:
                await update.message.reply_text("Não consegui entender o valor. Exemplo: adicionar 50 alimentação despesa")
        else:
            await update.message.reply_text("Formato correto: adicionar <valor> <categoria> <tipo>")

    elif "grafico" in texto or "gráfico" in texto:
        await gerar_grafico(update, context)

    else:
        await update.message.reply_text("Desculpe, não entendi 😅. Você pode me mandar 'saldo', 'adicionar <valor> <categoria> <tipo>' ou 'grafico' para ver seus gastos.")

#---------------------Graficos Para o bot gerar
async def gerar_grafico(update, context):
    chat_id = update.effective_chat.id
    user_id = get_user_id(chat_id)

    if not user_id:
        await update.message.reply_text("Usuário não encontrado. Use /start primeiro.")
        return


    transacoes = get_transactions(user_id)

 
    despesas = [t for t in transacoes if t['tipo'] == 'despesa']

    if not despesas:
        await update.message.reply_text("Você ainda não tem despesas cadastradas.")
        return

 
    categorias = {}
    for d in despesas:
        categorias[d['categoria']] = categorias.get(d['categoria'], 0) + float(d['valor'])


    labels = list(categorias.keys())
    valores = list(categorias.values())

    # Criar gráfico de pizza
    plt.figure(figsize=(6,6))
    plt.pie(valores, labels=labels, autopct='%1.1f%%', startangle=140)
    plt.title("Gastos por Categoria")

    # Salva na memoria
    buffer = BytesIO()
    plt.savefig(buffer, format='png')
    buffer.seek(0)
    plt.close()

    
    await update.message.reply_photo(photo=buffer)

#---------------------Gastos Semanais do User
async def resumo_semanal(update, context):
    chat_id = update.effective_chat.id
    user_id = get_user_id(chat_id)

    if not user_id:
        nome = update.effective_user.first_name
        user_id = add_user(chat_id, nome)
        await update.message.reply_text(f"Olá {nome}! Você foi cadastrado. Use 'adicionar' para registrar suas transações.")
        return

    # Saldo atual
    saldo_atual = get_balance(user_id)

    # Transações da semana
    transacoes = get_transactions_week(user_id)
    despesas = [t for t in transacoes if t['tipo'] == 'despesa']

    if despesas:
        resumo = {}
        for d in despesas:
            resumo[d['categoria']] = resumo.get(d['categoria'], 0) + float(d['valor'])
        mensagem = f"💰 Seu saldo atual: R$ {saldo_atual:.2f}\n\n📊 Gastos da semana:\n"
        for cat, val in resumo.items():
            mensagem += f"- {cat}: R$ {val:.2f}\n"
    else:
        mensagem = f"💰 Seu saldo atual: R$ {saldo_atual:.2f}\n\nVocê não teve despesas esta semana."

    await update.message.reply_text(mensagem)
# -------------------- bot
def main():
    app = ApplicationBuilder().token(TOKEN).build()

  
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("saldo", saldo))
    app.add_handler(CommandHandler("adicionar", adicionar))
    app.add_handler(CommandHandler("grafico", gerar_grafico))

 
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, responder))

    print("🤖 Bot iniciado...")
    app.run_polling()

if __name__ == "__main__":
    main()
