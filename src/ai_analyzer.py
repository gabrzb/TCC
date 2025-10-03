import requests
import os
import pandas as pd

class AIAnalyzer:
    def __init__(self):
        self.api_key = os.getenv('HF_API_KEY', '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')  # Configure sua chave
        self.api_url = "https://api-inference.huggingface.co/models/cardiffnlp/twitter-roberta-base-sentiment-latest"
        print("AIAnalyzer inicializado com API Hugging Face")
    
    def classificar_sentimento(self, texto):
        """
        Classifica o sentimento de um texto usando API externa
        """
        if pd.isna(texto) or not texto or str(texto).strip() == "":
            return "NEUTRO"
            
        try:
            # Prepara o texto
            texto_limpo = str(texto)[:512]
            
            # Faz a requisição para a API
            response = requests.post(
                self.api_url,
                headers={"Authorization": f"Bearer {self.api_key}"},
                json={"inputs": texto_limpo},
                timeout=30
            )
            
            if response.status_code == 200:
                resultado = response.json()
                return self._processar_resultado_api(resultado)
            else:
                print(f"Erro API: {response.status_code} - {response.text}")
                return "ERRO_API"
                
        except Exception as e:
            print(f"Erro na requisição: {e}")
            return "ERRO"
    
    def _processar_resultado_api(self, resultado):
        """
        Processa o resultado da API Hugging Face
        """
        try:
            if isinstance(resultado, list) and len(resultado) > 0:
                scores = resultado[0]
                
                # Encontra o sentimento com maior score
                maior_score = max(scores, key=lambda x: x['score'])
                label = maior_score['label'].upper()
                
                # Mapeia labels para categorias em português
                if 'POSITIVE' in label or 'POSITIVO' in label:
                    return "POSITIVO"
                elif 'NEGATIVE' in label or 'NEGATIVO' in label:
                    return "NEGATIVO"
                else:
                    return "NEUTRO"
            
            return "NEUTRO"
            
        except Exception as e:
            print(f"Erro ao processar resultado: {e}")
            return "ERRO"

# Cria uma instância global
ai_analyzer = AIAnalyzer()

# Função direta para compatibilidade
def classificar_sentimento(texto):
    """Função direta que usa a instância global"""
    return ai_analyzer.classificar_sentimento(texto)