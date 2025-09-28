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
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import random
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
            timeout=2
        )
        print(f"Progresso reportado: {percentual}% - {etapa}")
    except Exception as e:
        print(f"Erro ao reportar progresso: {e}")

def setup_driver():
    """Configura o driver do Chrome"""
    try:
        print("Configurando driver Chrome...")
        chrome_options = Options()
        
        # Opções que funcionaram no teste
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_argument("--start-maximized")
        
        # Opções de stealth
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        
        # User-Agent
        user_agent = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        chrome_options.add_argument(f'--user-agent={user_agent}')
        
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)
        driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        
        # Timeout implícito
        driver.implicitly_wait(10)
        
        print("Driver configurado com sucesso!")
        return driver
        
    except Exception as e:
        print(f"ERRO na configuracao do driver: {e}")
        traceback.print_exc()
        return None

def get_product_data(driver, product_url):
    """Extrai dados de um único produto"""
    print(f"Acessando: {product_url}")
    
    try:
        # Primeiro teste com Google para verificar conexão
        print("Testando conexao...")
        driver.get("https://www.google.com")
        time.sleep(2)
        
        # Agora acessa a Amazon
        driver.get(product_url)
        
        # Aguarda carregamento com timeout maior
        WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )
        
        # Verifica se não está bloqueado
        page_title = driver.title.lower()
        if "robot" in page_title or "captcha" in page_title or "bot" in page_title:
            print("AVISO: Possivel bloqueio detectado na pagina")
        
        time.sleep(3)
        print("Pagina carregada com sucesso")
        return driver.page_source
        
    except TimeoutException:
        print("Timeout - A pagina pode nao ter carregado corretamente, mas continuando...")
        return driver.page_source if driver else None
    except Exception as e:
        print(f"Erro ao acessar a pagina: {e}")
        traceback.print_exc()
        return None

def extract_reviews(driver):
    """Extrai comentários/reviews visíveis diretamente da página do produto"""
    reviews = []
    
    try:
        print("Procurando comentarios na pagina do produto...")
        
        time.sleep(3)  # Espera mais tempo para carregar
        
        # Tentar encontrar elementos de review
        review_selectors = [
            "[data-hook='review']",
            ".review",
            "[data-component-type='review']",
            ".a-section.review"
        ]
        
        review_elements = []
        for selector in review_selectors:
            try:
                elements = driver.find_elements(By.CSS_SELECTOR, selector)
                if elements:
                    print(f"Encontrados {len(elements)} comentarios com seletor: {selector}")
                    review_elements.extend(elements)
            except Exception as e:
                continue
        
        # Remover duplicatas
        unique_reviews = []
        seen_texts = set()
        for element in review_elements:
            try:
                element_text = element.text.strip()
                if element_text and element_text not in seen_texts:
                    seen_texts.add(element_text)
                    unique_reviews.append(element)
            except:
                continue
        
        print(f"Total de comentarios unicos encontrados: {len(unique_reviews)}")
        
        for i, review in enumerate(unique_reviews):
            try:
                review_data = {}
                
                # Título do review
                try:
                    title_elem = review.find_element(By.CSS_SELECTOR, "[data-hook='review-title'] span")
                    review_data['review_title'] = title_elem.text.strip() if title_elem else 'N/A'
                except:
                    review_data['review_title'] = 'N/A'
                
                # Rating
                try:
                    rating_elem = review.find_element(By.CSS_SELECTOR, "[class*='star']")
                    rating_text = rating_elem.get_attribute('aria-label') or ''
                    rating_match = re.search(r'(\d+\.?\d*)', rating_text)
                    review_data['rating'] = rating_match.group(1) if rating_match else 'N/A'
                except:
                    review_data['rating'] = 'N/A'
                
                # Texto do review
                try:
                    text_elem = review.find_element(By.CSS_SELECTOR, "[data-hook='review-body']")
                    review_data['review_text'] = text_elem.text.strip() if text_elem else 'N/A'
                except:
                    review_data['review_text'] = 'N/A'
                
                # Autor
                try:
                    author_elem = review.find_element(By.CSS_SELECTOR, "[data-hook='review-author']")
                    review_data['author'] = author_elem.text.strip() if author_elem else 'N/A'
                except:
                    review_data['author'] = 'N/A'
                
                # Data
                try:
                    date_elem = review.find_element(By.CSS_SELECTOR, "[data-hook='review-date']")
                    review_data['date'] = date_elem.text.strip() if date_elem else 'N/A'
                except:
                    review_data['date'] = 'N/A'
                
                # Verificação de compra
                try:
                    verified_elems = review.find_elements(By.CSS_SELECTOR, "[data-hook='avp-badge']")
                    review_data['verified_purchase'] = 'Sim' if verified_elems else 'Nao'
                except:
                    review_data['verified_purchase'] = 'N/A'
                
                # Filtra reviews vazios
                if (review_data['review_title'] != 'N/A' or 
                    review_data['review_text'] != 'N/A'):
                    reviews.append(review_data)
                
                print(f"Review {i+1} extraido: {review_data['review_title'][:50]}...")
                
            except Exception as e:
                print(f"Erro ao extrair review {i+1}: {e}")
                continue
                
    except Exception as e:
        print(f"Erro ao extrair reviews da pagina: {e}")
        traceback.print_exc()
    
    return reviews

def extract_product_details(soup, product_url):
    """Extrai detalhes do produto individual"""
    product_data = {}
    
    try:
        # Nome do produto
        title_element = soup.find('span', {'id': 'productTitle'})
        product_data['name'] = title_element.get_text(strip=True) if title_element else 'N/A'
        
        # Preço
        price_selectors = [
            '.a-price-whole',
            '.a-price .a-offscreen',
            '#priceblock_ourprice',
            '#priceblock_dealprice'
        ]
        
        product_data['price'] = 'N/A'
        for selector in price_selectors:
            price_element = soup.select_one(selector)
            if price_element and price_element.text.strip():
                product_data['price'] = price_element.text.strip()
                break
        
        # Avaliação geral
        rating_element = soup.find('span', {'data-hook': 'rating-out-of-text'})
        product_data['rating'] = rating_element.text.strip() if rating_element else 'N/A'
        
        # Número de avaliações
        reviews_element = soup.find('span', {'id': 'acrCustomerReviewText'})
        product_data['reviews_count'] = reviews_element.text.strip() if reviews_element else 'N/A'
        
        # Descrição
        description_element = soup.find('div', {'id': 'productDescription'})
        product_data['description'] = description_element.get_text(strip=True) if description_element else 'N/A'
        
        # ASIN da URL
        asin_match = re.search(r'/dp/([A-Z0-9]{10})', product_url)
        product_data['asin'] = asin_match.group(1) if asin_match else 'N/A'
        
        # Imagem
        image_element = soup.find('img', {'id': 'landingImage'})
        product_data['image_url'] = image_element.get('src') if image_element else 'N/A'
        
        print("Detalhes do produto extraidos com sucesso")
        
    except Exception as e:
        print(f"Erro ao extrair detalhes do produto: {e}")
        traceback.print_exc()
    
    return product_data

def main(product_url, process_id=None):
    """Função principal para um produto específico"""
    print("=== INICIANDO EXTRACAO DE PRODUTO ===")
    
    # Função helper para reportar progresso
    def reportar(etapa, percentual):
        if process_id:
            reportar_progresso(process_id, etapa, percentual)
        print(f"Progresso: {percentual}% - {etapa}")
    
    driver = None
    try:
        reportar("Configurando navegador", 10)
        driver = setup_driver()
        if not driver:
            reportar("Erro: Falha ao configurar navegador", 0, "erro")
            return False
        
        reportar("Acessando página da Amazon", 30)
        page_source = get_product_data(driver, product_url)
        
        if not page_source:
            reportar("Erro: Falha ao carregar página", 0, "erro")
            return False
            
        reportar("Extraindo dados do produto", 50)
        soup = BeautifulSoup(page_source, 'html.parser')
        product = extract_product_details(soup, product_url)
        
        if not product or product['name'] == 'N/A':
            reportar("Erro: Não foi possível extrair dados do produto", 0, "erro")
            return False
            
        print(f"Produto: {product['name']}")
        print(f"Preco: {product['price']}")
        
        reportar("Extraindo comentários", 70)
        reviews = extract_reviews(driver)
        
        print(f"Total de comentarios extraidos: {len(reviews)}")
        
        reportar("Salvando arquivos CSV", 90)
        
        # Salvar dados do produto (na pasta acima)
        product_df = pd.DataFrame([product])
        product_df.to_csv('../amazon_data/amazon_product.csv', index=False, encoding='utf-8')
        print("Dados do produto salvos em amazon_product.csv")
        
        # Salvar comentários se houver
        if reviews:
            reviews_df = pd.DataFrame(reviews)
            reviews_df.to_csv('../amazon_data/amazon_reviews.csv', index=False, encoding='utf-8')
            print("Comentarios salvos em amazon_reviews.csv")
        else:
            print("Nenhum comentario extraido")
            
        reportar("Processamento concluído", 100)
        return True
            
    except Exception as e:
        erro_msg = f"Erro durante a execucao: {e}"
        if process_id:
            reportar_progresso(process_id, erro_msg, 0, "erro")
        print(erro_msg)
        traceback.print_exc()
        return False
        
    finally:
        if driver:
            print("Fechando navegador...")
            driver.quit()

if __name__ == "__main__":
    try:
        if len(sys.argv) >= 2:
            product_url = sys.argv[1]
            process_id = sys.argv[2] if len(sys.argv) >= 3 else None
            
            print(f"URL do produto: {product_url}")
            if process_id:
                print(f"ID do processo: {process_id}")
            
            success = main(product_url, process_id)
            print(f"Processo finalizado: {'SUCESSO' if success else 'FALHA'}")
            sys.exit(0 if success else 1)
        else:
            print("Uso: python rpa.py <url_do_produto> [process_id]")
            sys.exit(1)
    except Exception as e:
        print(f"Erro geral: {e}")
        traceback.print_exc()
        sys.exit(1)