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

def setup_driver():
    """Configura o driver do Chrome"""
    chrome_options = Options()
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option('useAutomationExtension', False)
    chrome_options.add_argument("--window-size=1920,1080")
    
    # User-Agent aleatório
    user_agents = [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    ]
    chrome_options.add_argument(f'--user-agent={random.choice(user_agents)}')
    
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    
    return driver

def get_product_data(driver, product_url):
    """Extrai dados de um único produto"""
    print(f"🌐 Acessando: {product_url}")
    
    try:
        driver.get(product_url)
        
        # Aguardar carregamento da página
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.ID, "productTitle"))
        )
        
        time.sleep(3)
        
        return driver.page_source
        
    except TimeoutException:
        print("⏰ Timeout - A página pode não ter carregado corretamente")
        return driver.page_source
    except Exception as e:
        print(f"❌ Erro ao acessar a página: {e}")
        return None

def extract_reviews(driver):
    """Extrai comentários/reviews visíveis diretamente da página do produto"""
    reviews = []
    
    try:
        print("📖 Procurando comentários na página do produto...")
        
        # Aguardar um pouco para garantir que a página carregou completamente
        time.sleep(2)
        
        # Tentar encontrar elementos de review com vários seletores possíveis
        review_selectors = [
            "[data-hook='review']",
            ".review",
            "[data-component-type='review']",
            ".a-section.review",
            ".customer_review",
            "#cm-cr-dp-review-list .a-section"
        ]
        
        review_elements = []
        for selector in review_selectors:
            try:
                elements = driver.find_elements(By.CSS_SELECTOR, selector)
                if elements:
                    print(f"✅ Encontrados {len(elements)} comentários com seletor: {selector}")
                    review_elements.extend(elements)
                    # Não break para tentar todos os seletores
            except Exception as e:
                continue
        
        # Remover duplicatas (pode acontecer com múltiplos seletores)
        unique_reviews = []
        seen_elements = set()
        for element in review_elements:
            element_id = element.id
            if element_id not in seen_elements:
                seen_elements.add(element_id)
                unique_reviews.append(element)
        
        print(f"📝 Total de comentários únicos encontrados: {len(unique_reviews)}")
        
        for review in unique_reviews:
            try:
                review_data = {}
                
                # Título do review
                try:
                    title_selectors = [
                        "[data-hook='review-title']",
                        ".review-title",
                        ".a-text-bold span",
                        "a[data-hook='review-title']"
                    ]
                    title_elem = None
                    for selector in title_selectors:
                        try:
                            title_elem = review.find_element(By.CSS_SELECTOR, selector)
                            if title_elem and title_elem.text.strip():
                                break
                        except:
                            continue
                    review_data['review_title'] = title_elem.text.strip() if title_elem else 'N/A'
                except:
                    review_data['review_title'] = 'N/A'
                
                # Rating
                try:
                    rating_selectors = [
                        "[data-hook='review-star-rating']",
                        ".a-icon-star",
                        ".review-rating",
                        "i[data-hook='review-star-rating']"
                    ]
                    rating_elem = None
                    for selector in rating_selectors:
                        try:
                            rating_elem = review.find_element(By.CSS_SELECTOR, selector)
                            if rating_elem:
                                break
                        except:
                            continue
                    
                    if rating_elem:
                        rating_text = rating_elem.get_attribute('text') or rating_elem.get_attribute('innerText') or rating_elem.get_attribute('aria-label') or ''
                        if rating_text:
                            rating_match = re.search(r'(\d+\.?\d*)', rating_text)
                            review_data['rating'] = rating_match.group(1) if rating_match else 'N/A'
                        else:
                            review_data['rating'] = 'N/A'
                    else:
                        review_data['rating'] = 'N/A'
                except:
                    review_data['rating'] = 'N/A'
                
                # Texto do review
                try:
                    text_selectors = [
                        "[data-hook='review-body']",
                        ".review-text",
                        ".review-text-content",
                        "span[data-hook='review-body']"
                    ]
                    text_elem = None
                    for selector in text_selectors:
                        try:
                            text_elem = review.find_element(By.CSS_SELECTOR, selector)
                            if text_elem and text_elem.text.strip():
                                break
                        except:
                            continue
                    review_data['review_text'] = text_elem.text.strip() if text_elem else 'N/A'
                except:
                    review_data['review_text'] = 'N/A'
                
                # Autor
                try:
                    author_selectors = [
                        "[data-hook='review-author']",
                        ".author",
                        ".a-profile-name",
                        "a[data-hook='review-author']"
                    ]
                    author_elem = None
                    for selector in author_selectors:
                        try:
                            author_elem = review.find_element(By.CSS_SELECTOR, selector)
                            if author_elem and author_elem.text.strip():
                                break
                        except:
                            continue
                    review_data['author'] = author_elem.text.strip() if author_elem else 'N/A'
                except:
                    review_data['author'] = 'N/A'
                
                # Data
                try:
                    date_selectors = [
                        "[data-hook='review-date']",
                        ".review-date",
                        ".a-size-base.a-color-secondary"
                    ]
                    date_elem = None
                    for selector in date_selectors:
                        try:
                            date_elem = review.find_element(By.CSS_SELECTOR, selector)
                            if date_elem and date_elem.text.strip():
                                break
                        except:
                            continue
                    review_data['date'] = date_elem.text.strip() if date_elem else 'N/A'
                except:
                    review_data['date'] = 'N/A'
                
                # Verificação de compra
                try:
                    verified_selectors = [
                        "[data-hook='avp-badge']",
                        ".a-size-mini.a-color-state",
                        "[data-hook='avp-badge'] span"
                    ]
                    verified = False
                    for selector in verified_selectors:
                        try:
                            verified_elems = review.find_elements(By.CSS_SELECTOR, selector)
                            for elem in verified_elems:
                                text = elem.text.lower()
                                if "compra verificada" in text or "verified purchase" in text:
                                    verified = True
                                    break
                            if verified:
                                break
                        except:
                            continue
                    review_data['verified_purchase'] = 'Sim' if verified else 'Não'
                except:
                    review_data['verified_purchase'] = 'N/A'
                
                # Apenas adicionar se tiver pelo menos algum conteúdo relevante
                if (review_data['review_title'] != 'N/A' or 
                    review_data['review_text'] != 'N/A' or 
                    review_data['rating'] != 'N/A'):
                    reviews.append(review_data)
                
            except Exception as e:
                print(f"⚠️ Erro ao extrair um review: {e}")
                continue
                
    except Exception as e:
        print(f"❌ Erro ao extrair reviews da página: {e}")
    
    return reviews

def extract_product_details(soup, product_url):
    """Extrai detalhes do produto individual"""
    product_data = {}
    
    try:
        # Nome do produto
        title_element = soup.find('span', {'id': 'productTitle'})
        product_data['name'] = title_element.text.strip() if title_element else 'N/A'
        
        # Preço
        price_selectors = [
            'span.a-price .a-offscreen',
            '#priceblock_ourprice',
            '#priceblock_dealprice',
            '.a-price-range'
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
        product_data['description'] = description_element.text.strip() if description_element else 'N/A'
        
        # ASIN
        asin_element = soup.find('th', string='ASIN')
        if asin_element:
            product_data['asin'] = asin_element.find_next_sibling('td').text.strip()
        else:
            # Tentar extrair ASIN da URL
            asin_match = re.search(r'/dp/([A-Z0-9]{10})', product_url)
            product_data['asin'] = asin_match.group(1) if asin_match else 'N/A'
        
        # Imagem
        image_element = soup.find('img', {'id': 'landingImage'})
        product_data['image_url'] = image_element['src'] if image_element and image_element.has_attr('src') else 'N/A'
        
    except Exception as e:
        print(f"⚠️ Erro ao extrair detalhes do produto: {e}")
    
    return product_data

def main(product_url):
    """Função principal para um produto específico"""
    print("🚀 Iniciando extração de produto...")
    
    driver = setup_driver()
    
    try:
        # Extrair dados principais do produto
        page_source = get_product_data(driver, product_url)
        
        if page_source:
            soup = BeautifulSoup(page_source, 'html.parser')
            product = extract_product_details(soup, product_url)
            
            if product:
                print(f"\n🎉 Dados do produto extraídos:")
                print(f"📦 Nome: {product['name']}")
                print(f"💰 Preço: {product['price']}")
                print(f"⭐ Avaliação: {product['rating']}")
                print(f"📊 Total de avaliações: {product['reviews_count']}")
                print(f"🔖 ASIN: {product['asin']}")
                
                # Extrair comentários DA PRÓPRIA PÁGINA (sem navegar para outra)
                print("\n📖 Extraindo comentários da página atual...")
                reviews = extract_reviews(driver)
                
                if reviews:
                    print(f"✅ Extraídos {len(reviews)} comentários da página")
                    
                    # Salvar dados do produto
                    product_df = pd.DataFrame([product])
                    product_df.to_csv('amazon_product.csv', index=False, encoding='utf-8')
                    
                    # Salvar comentários
                    reviews_df = pd.DataFrame(reviews)
                    reviews_df.to_csv('amazon_reviews.csv', index=False, encoding='utf-8')
                    
                    print(f"💾 Dados do produto salvos em 'amazon_product.csv'")
                    print(f"💾 Comentários salvos em 'amazon_reviews.csv'")
                    
                    # Mostrar alguns comentários
                    print(f"\n📋 Exemplo de comentários extraídos:")
                    for i, review in enumerate(reviews[:3], 1):
                        print(f"\n--- Comentário {i} ---")
                        print(f"Título: {review['review_title']}")
                        print(f"Avaliação: {review['rating']}/5")
                        print(f"Texto: {review['review_text'][:100]}...")
                        print(f"Autor: {review['author']}")
                        print(f"Data: {review['date']}")
                        print(f"Compra verificada: {review['verified_purchase']}")
                        
                else:
                    print("❌ Não foi possível extrair comentários")
                    
            else:
                print("❌ Não foi possível extrair dados do produto")
                
        else:
            print("❌ Falha ao acessar a página do produto")
            
    except Exception as e:
        print(f"💥 Erro durante a execução: {e}")
        import traceback
        traceback.print_exc()
        
    finally:
        driver.quit()
        print("👋 Driver fechado")

# Exemplo de uso:
if __name__ == "__main__":
    product_link = "https://www.amazon.com.br/Controle-Dualshock-PlayStation-4-Preto/dp/B07FN1MZBH/"
    main(product_link)