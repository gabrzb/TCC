import pandas as pd
from bs4 import BeautifulSoup
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
import re
import sys
import traceback
import requests
import os

def reportar_progresso(process_id, etapa, percentual, status='processando'):
    """Reporta progresso para o backend"""
    try:
        requests.post(
            f'http://localhost:5000/progresso/{process_id}',
            json={
                'etapa': etapa, 
                'progresso': percentual,
                'status': status
            },
            timeout=1
        )
    except Exception:
        pass

def setup_driver():
    """Configura o driver do Chrome otimizado"""
    try:
        chrome_options = Options()
        
        # OPÇÕES PARA MÁXIMA PERFORMANCE
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--disable-extensions")
        chrome_options.add_argument("--disable-images")
        chrome_options.add_argument("--blink-settings=imagesEnabled=false")
        chrome_options.add_argument("--window-size=1024,768")
        
        # Performance e memory
        chrome_options.add_argument("--memory-pressure-off")
        chrome_options.add_argument("--max_old_space_size=1024")
        
        # Opções de stealth
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        
        user_agent = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        chrome_options.add_argument(f'--user-agent={user_agent}')
        
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)
        driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        
        # Timeouts agressivos
        driver.set_page_load_timeout(15)
        driver.implicitly_wait(3)
        
        return driver
        
    except Exception as e:
        print(f"ERRO na configuracao do driver: {e}")
        return None

def get_product_data_fast(driver, product_url):
    """Acesso rápido à página do produto"""
    try:
        driver.get(product_url)
        
        # Aguarda apenas o elemento body com timeout curto
        WebDriverWait(driver, 8).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )
        
        # Espera mínima para conteúdo dinâmico
        time.sleep(1.5)
        return driver.page_source
        
    except TimeoutException:
        print("Timeout - usando pagina carregada parcialmente")
        return driver.page_source
    except Exception as e:
        print(f"Erro ao acessar a pagina: {e}")
        return None

def extract_reviews_ultra_fast(driver):
    """Extrai comentários de forma ultra rápida"""
    reviews = []
    
    try:
        # Busca direta pelos reviews sem esperas longas
        review_elements = driver.find_elements(By.CSS_SELECTOR, "[data-hook='review']")
        
        # Se não encontrou, tenta seletor alternativo rapidamente
        if not review_elements:
            review_elements = driver.find_elements(By.CSS_SELECTOR, ".a-section.review")
        
        print(f"Elementos de review encontrados: {len(review_elements)}")
        
        # Limita para os primeiros 10 comentários
        for i, review in enumerate(review_elements[:10]):
            try:
                review_data = {}
                
                # Título (método mais direto)
                try:
                    title_elems = review.find_elements(By.CSS_SELECTOR, "[data-hook='review-title']")
                    if title_elems:
                        review_data['review_title'] = title_elems[0].text.strip()[:100]
                    else:
                        review_data['review_title'] = 'N/A'
                except:
                    review_data['review_title'] = 'N/A'
                
                # Rating (busca simplificada)
                try:
                    rating_elems = review.find_elements(By.CSS_SELECTOR, "i[data-hook*='star']")
                    if rating_elems:
                        rating_text = rating_elems[0].get_attribute('textContent') or ''
                        rating_match = re.search(r'(\d+\.?\d*)', rating_text)
                        review_data['rating'] = rating_match.group(1) if rating_match else 'N/A'
                    else:
                        review_data['rating'] = 'N/A'
                except:
                    review_data['rating'] = 'N/A'
                
                # Texto do review
                try:
                    text_elems = review.find_elements(By.CSS_SELECTOR, "[data-hook='review-body']")
                    if text_elems:
                        review_data['review_text'] = text_elems[0].text.strip()[:300]
                    else:
                        review_data['review_text'] = 'N/A'
                except:
                    review_data['review_text'] = 'N/A'
                
                # Autor
                try:
                    author_elems = review.find_elements(By.CSS_SELECTOR, "[data-hook='review-author']")
                    review_data['author'] = author_elems[0].text.strip()[:50] if author_elems else 'N/A'
                except:
                    review_data['author'] = 'N/A'
                
                # Data
                try:
                    date_elems = review.find_elements(By.CSS_SELECTOR, "[data-hook='review-date']")
                    review_data['date'] = date_elems[0].text.strip()[:30] if date_elems else 'N/A'
                except:
                    review_data['date'] = 'N/A'
                
                # Verificação de compra
                try:
                    verified_elems = review.find_elements(By.CSS_SELECTOR, "[data-hook='avp-badge']")
                    review_data['verified_purchase'] = 'Sim' if verified_elems else 'Nao'
                except:
                    review_data['verified_purchase'] = 'N/A'
                
                # Adiciona apenas se tiver conteúdo válido
                if review_data['review_title'] != 'N/A' or review_data['review_text'] != 'N/A':
                    reviews.append(review_data)
                
            except Exception as e:
                print(f"Erro no review {i+1}: {e}")
                continue
                
    except Exception as e:
        print(f"Erro geral ao extrair reviews: {e}")
    
    return reviews

def extract_product_details_fast(soup, product_url):
    """Extrai detalhes do produto de forma rápida"""
    product_data = {}
    
    try:
        # Nome do produto
        title_element = soup.find('span', {'id': 'productTitle'})
        product_data['name'] = title_element.get_text(strip=True)[:200] if title_element else 'N/A'
        
        # Preço
        price_element = soup.select_one('.a-price-whole, .a-price .a-offscreen')
        product_data['price'] = price_element.text.strip() if price_element else 'N/A'
        
        # Avaliação geral
        rating_element = soup.find('span', {'data-hook': 'rating-out-of-text'})
        product_data['rating'] = rating_element.text.strip()[:10] if rating_element else 'N/A'
        
        # Número de avaliações
        reviews_element = soup.find('span', {'id': 'acrCustomerReviewText'})
        product_data['reviews_count'] = reviews_element.text.strip()[:20] if reviews_element else 'N/A'
        
        # ASIN
        asin_match = re.search(r'/dp/([A-Z0-9]{10})', product_url)
        product_data['asin'] = asin_match.group(1) if asin_match else 'N/A'
        
    except Exception as e:
        print(f"Erro ao extrair detalhes: {e}")
    
    return product_data

def clean_text(text):
    """Limpa texto removendo caracteres problemáticos"""
    if text == 'N/A':
        return text
    # Remove caracteres Unicode problemáticos mas mantém acentos
    cleaned = re.sub(r'[^\x00-\x7Fáéíóúàèìòùâêîôûãõç\s]', '', str(text))
    return cleaned.strip()

def save_data_safe(product_data, reviews_data):
    """Salva dados de forma segura criando diretório se necessário"""
    try:
        # Define o diretório de saída
        output_dir = 'amazon_data'
        
        # Cria o diretório se não existir
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
            print(f"Diretorio criado: {output_dir}")
        
        # Limpa dados do produto antes de salvar
        if product_data:
            cleaned_product = {}
            for key, value in product_data.items():
                cleaned_product[key] = clean_text(value)
            
            product_df = pd.DataFrame([cleaned_product])
            product_path = os.path.join(output_dir, 'amazon_product.csv')
            product_df.to_csv(product_path, index=False, encoding='utf-8-sig')  # utf-8-sig para Excel
            print(f"Dados do produto salvos em: {product_path}")
        
        # Limpa e salva reviews
        if reviews_data:
            cleaned_reviews = []
            for review in reviews_data:
                cleaned_review = {}
                for key, value in review.items():
                    cleaned_review[key] = clean_text(value)
                cleaned_reviews.append(cleaned_review)
            
            reviews_df = pd.DataFrame(cleaned_reviews)
            reviews_path = os.path.join(output_dir, 'amazon_reviews.csv')
            reviews_df.to_csv(reviews_path, index=False, encoding='utf-8-sig')  # utf-8-sig para Excel
            print(f"Reviews salvos em: {reviews_path}")
            print(f"Total de reviews salvos: {len(cleaned_reviews)}")
            
        return True
        
    except Exception as e:
        print(f"ERRO ao salvar arquivos: {e}")
        traceback.print_exc()
        return False

def main(product_url, process_id=None):
    """Função principal otimizada"""
    print("=== EXTRACAO ULTRA RAPIDA ===")
    
    def reportar(etapa, percentual):
        if process_id:
            reportar_progresso(process_id, etapa, percentual)
        print(f"Progresso: {percentual}% - {etapa}")
    
    driver = None
    try:
        reportar("Iniciando navegador", 10)
        driver = setup_driver()
        if not driver:
            reportar("Erro no navegador", 0, "erro")
            return False
        
        reportar("Carregando pagina", 30)
        page_source = get_product_data_fast(driver, product_url)
        
        if not page_source:
            reportar("Erro ao carregar", 0, "erro")
            return False
            
        reportar("Extraindo dados", 50)
        soup = BeautifulSoup(page_source, 'html.parser')
        product = extract_product_details_fast(soup, product_url)
        
        reportar("Coletando comentarios", 70)
        reviews = extract_reviews_ultra_fast(driver)
        
        print(f"PRODUTO: {product.get('name', 'N/A')}")
        print(f"COMENTARIOS EXTRAIDOS: {len(reviews)}")
        
        reportar("Salvando dados", 90)
        
        # Salva dados de forma segura
        success = save_data_safe(product, reviews)
        if not success:
            reportar("Erro ao salvar", 0, "erro")
            return False
            
        reportar("Concluido", 100)
        return True
            
    except Exception as e:
        error_msg = f"Erro: {str(e)}"
        print(error_msg)
        if process_id:
            reportar_progresso(process_id, error_msg, 0, "erro")
        return False
        
    finally:
        if driver:
            try:
                driver.quit()
                print("Navegador fechado")
            except:
                pass

if __name__ == "__main__":
    try:
        if len(sys.argv) >= 2:
            product_url = sys.argv[1]
            process_id = sys.argv[2] if len(sys.argv) >= 3 else None
            
            success = main(product_url, process_id)
            print(f"PROCESSO FINALIZADO: {'SUCESSO' if success else 'FALHA'}")
            sys.exit(0 if success else 1)
        else:
            print("Uso: python rpa.py <url_do_produto> [process_id]")
            sys.exit(1)
    except Exception as e:
        print(f"ERRO GERAL: {e}")
        sys.exit(1)