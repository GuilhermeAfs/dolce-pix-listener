from flask import Flask, request
import requests
import firebase_admin
from firebase_admin import credentials, db
import os
import json
import datetime

ACCESS_TOKEN_MP = os.environ.get("ACCESS_TOKEN_MP")
FIREBASE_CREDENTIALS = os.environ.get("FIREBASE_CREDENTIALS")
DATABASE_URL = os.environ.get("DATABASE_URL")

# Inicializa Firebase com credenciais do JSON via env var
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
    log("📬 Webhook recebido!")
    
    try:
        body = request.get_json(force=True)
        log(f"📦 JSON recebido:\n{json.dumps(body, indent=2)}")
    except Exception as e:
        log(f"❌ Erro ao processar JSON: {e}")
        return "Erro no JSON", 400

    payment_id = body.get("data", {}).get("id")
    if not payment_id:
        log("⚠️ ID do pagamento ausente no JSON. Ignorando.")
        return "Sem payment_id", 200  # Evita erro 500

    log(f"🔎 Consultando pagamento ID: {payment_id}")

    response = requests.get(
        f"https://api.mercadopago.com/v1/payments/{payment_id}",
        headers={"Authorization": f"Bearer {ACCESS_TOKEN_MP}"}
    )

    if response.status_code != 200:
        log(f"⚠️ Erro ao consultar o pagamento na API. Status: {response.status_code}")
        log(f"📄 Resposta da API:\n{response.text}")
        return "Ignorado: pagamento inválido", 200

    data = response.json()
    valor = data.get("transaction_amount")
    status = data.get("status")
    metodo = data.get("payment_method_id")
    email = data.get("payer", {}).get("email")

    log(f"📄 Detalhes do pagamento:")
    log(f"   🧾 Valor: R$ {valor}")
    log(f"   ✅ Status: {status}")
    log(f"   💳 Método: {metodo}")
    log(f"   📧 Email: {email}")

    if status == "approved" and valor > 0.001:
        try:
            db.reference("/comando").set({"ligar": True})
            log("🔥 Firebase atualizado com sucesso!")
        except Exception as e:
            log(f"❌ Erro ao atualizar Firebase: {e}")
    else:
        log("⚠️ Pagamento não aprovado ou valor inválido.")

    return "OK", 200

# Roda no Render
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
