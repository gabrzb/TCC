from flask import Flask, jsonify, request
import datetime
import threading
import os
import re
import uuid
import subprocess
from src import ai_analyzer

app = Flask(__name__)

# Armazenamento de progresso em memória (para desenvolvimento)
progresso_processos = {}

def validar_url_amazon(url):
    """Valida se a URL é uma URL válida da Amazon"""
    padroes_amazon = [
        r'https?://www\.amazon\.com\.br/.*/dp/[A-Z0-9]{10}',
        r'https?://www\.amazon\.com\.br/dp/[A-Z0-9]{10}',
        r'https?://amazon\.com\.br/.*/dp/[A-Z0-9]{10}'
    ]
    
    for padrao in padroes_amazon:
        if re.match(padrao, url):
            return True
    return False

def atualizar_progresso(process_id, percentual, etapa, status='processando'):
    """Atualiza o progresso de um processo"""
    progresso_processos[process_id] = {
        'status': status,
        'progresso': percentual,
        'etapa_atual': etapa,
        'timestamp': datetime.datetime.now().isoformat(),
        'timestamp_lega': datetime.datetime.now().strftime('%H:%M:%S')
    }

def executar_rpa_em_separado(url_produto, process_id):
    """
    Executa o RPA em um processo separado usando subprocess
    """
    try:
        print(f"Iniciando processo RPA para: {url_produto}")
        
        # Atualiza progresso
        atualizar_progresso(process_id, 10, "Iniciando processo RPA")
        
        # Executa o rpa.py como um processo separado
        result = subprocess.run([
            'python', 'src/rpa.py', 
            url_produto,
            process_id
        ], capture_output=True, text=True, timeout=300)
        
        print(f"Processo RPA finalizado: {result.returncode}")
        
        # Verifica resultado
        if result.returncode == 0:
            # RPA terminou, agora roda análise de sentimento
            
            atualizar_progresso(process_id, 80, "Executando análise de sentimentos")
            import pandas as pd
            df = pd.read_csv('amazon_data/amazon_reviews.csv')
            df['sentimento'] = df['review_text'].apply(ai_analyzer.classificar_sentimento)
            df.to_csv('amazon_data/resultado.csv', index=False)
            print("Arquivo 'resultado.csv' gerado com sucesso!")
            
            atualizar_progresso(process_id, 100, "Processamento concluído com sucesso", "concluido")
            return True
        else:
            atualizar_progresso(process_id, 0, f"Erro no RPA: {result.stderr}", "erro")
            return False

    except Exception as e:
        atualizar_progresso(process_id, 0, f"Erro na análise de sentimentos: {e}", "erro")
        return False
    except subprocess.TimeoutExpired:
        erro_msg = "RPA excedeu o tempo limite (5 minutos)"
        atualizar_progresso(process_id, 0, erro_msg, "erro")
        print(erro_msg)
        return False
    except Exception as e:
        erro_msg = f"Erro ao executar RPA: {e}"
        atualizar_progresso(process_id, 0, erro_msg, "erro")
        print(erro_msg)
        return False

@app.route('/')
def home():
    return jsonify({
        "mensagem": "Olá do Python!", 
        "hora": datetime.datetime.now().strftime("%H:%M:%S"),
        "status": "conectado"
    })

@app.route('/registro', methods=['POST'])
def registrar():
    try:
        dados = request.get_json()
        
        if not dados:
            return jsonify({"sucesso": False, "erro": "Nenhum dado recebido"}), 400
        
        url_produto = dados.get('url', '').strip()
        
        if not url_produto:
            return jsonify({"sucesso": False, "erro": "URL é obrigatória"}), 400
        
        if not validar_url_amazon(url_produto):
            return jsonify({"sucesso": False, "erro": "URL da Amazon inválida"}), 400
        
        print(f"URL recebida: {url_produto}")
        
        # Gera um ID único para este processamento
        process_id = str(uuid.uuid4())[:8]
        
        # Inicializa progresso
        atualizar_progresso(process_id, 0, "Recebendo requisição")
        
        # Executa em thread separada
        def executar_em_thread():
            sucesso = executar_rpa_em_separado(url_produto, process_id)
            status = "concluido" if sucesso else "erro"
            print(f"Processamento {process_id}: {status}")
        
        thread = threading.Thread(target=executar_em_thread)
        thread.daemon = True
        thread.start()
        
        return jsonify({
            "sucesso": True,
            "mensagem": "Processamento iniciado com sucesso!",
            "url_recebida": url_produto,
            "process_id": process_id,
            "hora": datetime.datetime.now().strftime("%H:%M:%S"),
            "status": "processando"
        })
        
    except Exception as e:
        error_message = str(e).encode('ascii', 'ignore').decode('ascii')
        return jsonify({"sucesso": False, "erro": f"Erro interno: {error_message}"}), 500

@app.route('/status/<process_id>')
def verificar_status(process_id):
    """Endpoint para verificar status do processamento com progresso real"""
    if process_id not in progresso_processos:
        return jsonify({"erro": "Processo não encontrado"}), 404
    
    progresso = progresso_processos[process_id]
    
    # Verificação final baseada em arquivos (backup)
    if (progresso['status'] == 'processando' and 
        os.path.exists('../amazon_data/amazon_product.csv') and 
        os.path.exists('../amazon_data/amazon_reviews.csv')):
        
        progresso.update({
            'status': 'concluido',
            'progresso': 100,
            'etapa_atual': 'Processamento concluído (arquivos gerados)'
        })
    
    return jsonify(progresso)

@app.route('/progresso/<process_id>', methods=['POST'])
def receber_progresso(process_id):
    """Endpoint para o RPA reportar progresso em tempo real"""
    try:
        dados = request.get_json()
        atualizar_progresso(
            process_id, 
            dados.get('progresso', 0), 
            dados.get('etapa', 'Processando'),
            dados.get('status', 'processando')
        )
        return jsonify({"sucesso": True})
    except Exception as e:
        return jsonify({"erro": str(e)}), 500

if __name__ == '__main__':
    print("=" * 50)
    print("INICIANDO BACKEND PYTHON")
    print("Servidor Flask iniciando na porta 5000...")
    print("Rotas disponíveis:")
    print("GET  / - Página inicial")
    print("POST /registro - Receber URL para processamento RPA")
    print("GET  /status/<id> - Verificar status do processamento")
    print("POST /progresso/<id> - Reportar progresso do RPA")
    print("=" * 50)
    
    app.run(host='127.0.0.1', port=5000, debug=False)