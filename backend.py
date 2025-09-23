# backend.py - VERSÃO CORRIGIDA (sem emojis)
from flask import Flask, jsonify
import datetime
import time

app = Flask(__name__)

@app.route('/')
def home():
    print("Requisição recebida na rota /")
    return jsonify({
        "mensagem": "Olá do Python!", 
        "hora": datetime.datetime.now().strftime("%H:%M:%S"),
        "status": "conectado"
    })

if __name__ == '__main__':
    print("=" * 50)
    print("INICIANDO BACKEND PYTHON")
    print("Servidor Flask iniciando na porta 5000...")
    print("=" * 50)
    
    import threading
    def print_ready():
        time.sleep(1)
        print("Flask está pronto e ouvindo na porta 5000!")
    
    thread = threading.Thread(target=print_ready)
    thread.daemon = True
    thread.start()
    
    app.run(host='127.0.0.1', port=5000, debug=False)