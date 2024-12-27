from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from bs4 import BeautifulSoup
import requests
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By 
from webdriver_manager.chrome import ChromeDriverManager

app = Flask(__name__)
CORS(app)

# Utility function to create Selenium driver
def create_selenium_driver():
    options = Options()
    options.headless = True
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    return webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

# Amazon Scraper
def scrape_amazon(search_term):
    try:
        base_url = f"https://www.amazon.in/s?k={search_term.replace(' ', '+')}"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/87.0.4280.88 Safari/537.36",
            "Accept-Language": "en-US,en;q=0.9",
        }
        response = requests.get(base_url, headers=headers)
        soup = BeautifulSoup(response.content, 'html.parser')

        product = soup.find('div', {'data-component-type': 's-search-result'})
        if not product:
            return {'Website': 'Amazon', 'Error': 'No products found'}

        return {
            'Website': 'Amazon',
            'Title': product.h2.text.strip() if product.h2 else "Title not found",
            'Image': product.find('img')['src'] if product.find('img') else 'N/A',
            'Price': product.find('span', class_='a-price a-text-price').text.strip() if product.find('span', class_='a-price a-text-price') else 'N/A',
            'Offer Price': product.find('span', class_='a-price-whole').text.strip() if product.find('span', class_='a-price-whole') else 'N/A',
            'Rating': product.find('span', class_='a-icon-alt').text.strip() if product.find('span', class_='a-icon-alt') else 'N/A',
            'Reviews': product.find('span', {'class': 'a-size-base'}).text.strip() if product.find('span', {'class': 'a-size-base'}) else 'N/A',
            'Product Link': "https://www.amazon.in" + product.find('a', {'class': 'a-link-normal'})['href'] if product.find('a', {'class': 'a-link-normal'}) else "Link not found",
        }
    except Exception as e:
        return {'Website': 'Amazon', 'Error': str(e)}

# Generic Selenium-based scraper
def scrape_with_selenium(base_url, product_selector, fields):
    driver = create_selenium_driver()
    try:
        driver.get(base_url)
        WebDriverWait(driver, 30).until(
            EC.presence_of_element_located((By.CLASS_NAME, product_selector))
        )
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        product = soup.find('li', class_=product_selector)
        if not product:
            return {'Error': 'No products found'}

        result = {}
        for field_name, query in fields.items():
            element = product.select_one(query['selector'])
            result[field_name] = element.text.strip() if element else query.get('default', 'N/A')

        return result
    except Exception as e:
        return {'Error': str(e)}
    finally:
        driver.quit()

# Croma Scraper
def scrape_croma(search_term):
    base_url = f"https://www.croma.com/searchB?q={search_term.replace(' ', '%20')}"
    fields = {
        'Title': {'selector': 'h3.product-title'},
        'Price': {'selector': 'span.old-price'},
        'Offer Price': {'selector': 'span.amount'},
        'Rating': {'selector': 'a.pr-review.review-text'},
        'Product Link': {'selector': 'a', 'default': base_url},
    }
    return scrape_with_selenium(base_url, 'product-item', fields)

# Myntra Scraper
def scrape_myntra(search_term):
    base_url = f"https://www.myntra.com/{search_term.replace(' ', '-')}"
    fields = {
        'Title': {'selector': 'h4.product-product'},
        'Price': {'selector': 'span.product-strike'},
        'Offer Price': {'selector': 'span.product-discountedPrice'},
        'Rating': {'selector': 'div.index-overallRating'},
        'Product Link': {'selector': 'a', 'default': base_url},
    }
    return scrape_with_selenium(base_url, 'product-base', fields)

@app.route('/')
def home():
    return send_from_directory('.', 'index.html')

@app.route('/search', methods=['POST'])
def search():
    search_term = request.form.get('search_term')
    website = request.form.get('website', 'all')

    scrapers = {
        'amazon': scrape_amazon,
        'croma': scrape_croma,
        'myntra': scrape_myntra,
    }

    data = []
    if website == 'all':
        for scraper in scrapers.values():
            data.append(scraper(search_term))
    elif website in scrapers:
        data.append(scrapers[website](search_term))
    return jsonify(data)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
