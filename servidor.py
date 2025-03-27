from flask import Flask, request
import requests
import firebase_admin
from firebase_admin import credentials, db
import os
import json
import datetime

# Carrega configs via variáveis de ambiente
ACCESS_TOKEN_MP = os.environ.get("ACCESS_TOKEN_MP")
FIREBASE_CREDENTIALS = os.environ.get("FIREBASE_CREDENTIALS")
DATABASE_URL = os.environ.get("DATABASE_URL")

# Inicializa Firebase com JSON vindo da env var
cred_dict = json.loads(FIREBASE_CREDENTIALS)
cred = credentials.Certificate(cred_dict)
firebase_admin.initialize_app(cred, {
    'databaseURL': DATABASE_URL
})

app = Flask(__name__)

@app.route("/webhook", methods=["POST"])
def webhook():
    print("📬 Webhook recebido!", flush=True)

    try:
        body = request.get_json(force=True)
        print("📦 JSON recebido:", json.dumps(body, indent=2), flush=True)
    except Exception as e:
        print("❌ Erro ao processar JSON:", e, flush=True)
        return "Erro no JSON", 400

    payment_id = body.get("data", {}).get("id")
    if not payment_id:
        print("⚠️ ID do pagamento ausente no JSON. Ignorando.", flush=True)
        return "Sem payment_id", 200

    print(f"🔎 Consultando pagamento ID: {payment_id}", flush=True)

    response = requests.get(
        f"https://api.mercadopago.com/v1/payments/{payment_id}",
        headers={"Authorization": f"Bearer {ACCESS_TOKEN_MP}"}
    )

    if response.status_code != 200:
        print(f"⚠️ Erro ao consultar o pagamento. Status: {response.status_code}", flush=True)
        print("📄 Resposta:", response.text, flush=True)
        return "Ignorado: pagamento inválido", 200

    data = response.json()
    valor = data.get("transaction_amount")
    status = data.get("status")
    metodo = data.get("payment_method_id")
    email = data.get("payer", {}).get("email")

    print("📄 Detalhes do pagamento:", flush=True)
    print(f"   🧾 Valor: R$ {valor}", flush=True)
    print(f"   ✅ Status: {status}", flush=True)
    print(f"   💳 Método: {metodo}", flush=True)
    print(f"   📧 Email: {email}", flush=True)

    if status == "approved" and valor > 0.001:
        try:
            db.reference("/comando").set({"ligar": True})
            print("🔥 Firebase atualizado com sucesso!", flush=True)
        except Exception as e:
            print("❌ Erro ao atualizar Firebase:", e, flush=True)
    else:
        print("⚠️ Pagamento não aprovado ou valor inválido.", flush=True)

    return "OK", 200

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    print(f"✅ Servidor iniciado na porta {port}", flush=True)
    app.run(host="0.0.0.0", port=port)
