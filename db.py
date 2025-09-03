from supabase import create_client, Client
from datetime import datetime, timedelta


supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# -------------------- Usuários --------------------
def add_user(chat_id, nome):
    # Verifica se o usuário já existe
    user = supabase.table("users").select("*").eq("chat_id", chat_id).execute()
    if user.data:
        return user.data[0]['id']
    
    # Se não existe, cria novo
    novo = supabase.table("users").insert({
        "chat_id": chat_id,
        "nome": nome
    }).execute()
    return novo.data[0]['id']

def get_user_id(chat_id):
    user = supabase.table("users").select("*").eq("chat_id", chat_id).execute()
    if user.data:
        return user.data[0]['id']
    return None

# -------------------- Transações --------------------
def add_transaction(user_id, valor, categoria, tipo):
    supabase.table("transactions").insert({
        "user_id": user_id,
        "valor": valor,
        "categoria": categoria,
        "tipo": tipo,
        "data": datetime.now().isoformat()
    }).execute()

def get_balance(user_id):
    resp = supabase.table("transactions").select("valor,tipo").eq("user_id", user_id).execute()
    saldo = 0
    for t in resp.data:
        if t['tipo'] == 'receita':
            saldo += float(t['valor'])
        else:
            saldo -= float(t['valor'])
    return saldo

def get_transactions(user_id):
    resp = supabase.table("transactions").select("*").eq("user_id", user_id).order("data", desc=True).execute()
    return resp.data

def get_transactions_week(user_id):
    semana_passada = datetime.now() - timedelta(days=7)
    resp = supabase.table("transactions")\
        .select("*")\
        .eq("user_id", user_id)\
        .gte("data", semana_passada.isoformat())\
        .execute()
    return resp.data
