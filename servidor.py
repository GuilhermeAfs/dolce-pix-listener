from flask import Flask, request
import requests
import firebase_admin
from firebase_admin import credentials, db
import os
import json
import datetime

# Configurações por variável de ambiente
ACCESS_TOKEN_MP = os.environ.get("ACCESS_TOKEN_MP")
FIREBASE_CREDENTIALS = os.environ.get("FIREBASE_CREDENTIALS")
DATABASE_URL = os.environ.get("DATABASE_URL")

# Inicialização do Firebase via env var
cred_dict = json.loads(FIREBASE_CREDENTIALS)
cred = credentials.Certificate(cred_dict)
firebase_admin.initialize_app(cred, {
    'databaseURL': DATABASE_URL
})

app = Flask(__name__)

def log(msg):
    hora = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{hora}] {msg}")

@app.route("/webhook", methods=["POST"])
def webhook():
    log("🔔 Webhook recebido!")
    try:
        body = request.get_json(force=True)
        print("📦 Corpo recebido:", body)
    except Exception as e:
        print("❌ Erro ao processar JSON:", e)
        return "Erro no JSON", 400

    payment_id = body.get("data", {}).get("id")
    if not payment_id:
        print("❌ ID do pagamento não encontrado.")
        return "ID não encontrado", 400

    log(f"🔎 Consultando pagamento ID: {payment_id}")

    response = requests.get(
        f"https://api.mercadopago.com/v1/payments/{payment_id}",
        headers={"Authorization": f"Bearer {ACCESS_TOKEN_MP}"}
    )

    if response.status_code != 200:
        print("❌ Erro na requisição ao Mercado Pago")
        print("🔴 Status:", response.status_code)
        print("📄 Resposta:", response.text)
        return "Erro na API MP", 500

    data = response.json()
    valor = data.get("transaction_amount")
    status = data.get("status")
    metodo = data.get("payment_method_id")
    email = data.get("payer", {}).get("email")

    print(f"📄 Dados do pagamento:")
    print(f"   🧾 Valor: R$ {valor}")
    print(f"   ✅ Status: {status}")
    print(f"   💳 Método: {metodo}")
    print(f"   📧 Email: {email}")

    if status == "approved" and valor > 0.001:
        try:
            db.reference("/comando").set({"ligar": True})
            print("🔥 Firebase atualizado com sucesso!")
        except Exception as e:
            print("❌ Erro ao atualizar Firebase:", e)
    else:
        print("⚠️ Pagamento não aprovado ou valor inválido.")

    return "OK", 200

# Inicia o servidor com a porta exigida pelo Render
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
