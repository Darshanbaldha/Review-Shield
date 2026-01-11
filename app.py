import os

USE_SELENIUM = os.getenv("USE_SELENIUM", "false").lower() == "true"

def scrape_with_selenium_pagination(url, max_pages=50):
    """Selenium-based scraping with pagination and dynamic loading - Takes ALL reviews"""
    try:
        from selenium import webdriver
        from selenium.webdriver.chrome.options import Options
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC
        from selenium.common.exceptions import TimeoutException, NoSuchElementException
        
        print(f"Starting Selenium scraping with pagination (max {max_pages} pages)...")
        
        chrome_options = Options()
        chrome_options.add_argument('--headless')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--window-size=1920,1080')
        chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
        
        driver = webdriver.Chrome(options=chrome_options)
        driver.get(url)
        
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )
        
        all_reviews = []
        
        # Strategy 1: Infinite scroll loading
        print("Attempting infinite scroll strategy...")
        last_height = driver.execute_script("return document.body.scrollHeight")
        scroll_attempts = 0
        max_scrolls = 20
        
        while scroll_attempts < max_scrolls:
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(3)
            
            new_height = driver.execute_script("return document.body.scrollHeight")
            
            if new_height == last_height:
                print(f"No more content loaded after scroll {scroll_attempts + 1}")
                break
            
            last_height = new_height
            scroll_attempts += 1
            print(f"Scroll {scroll_attempts}: New content loaded")
        
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        reviews = extract_reviews_from_soup(soup, url)
        all_reviews.extend(reviews)
        
        # Strategy 2: Pagination buttons
        print("Attempting pagination strategy...")
        
        pagination_selectors = [
            'li.a-last a',
            '.a-pagination .a-normal',
            '[aria-label="Go to next page"]',
            '._1LKTO3',
            '.ge-49M',
            '[class*="next"]',
            '.pagination a',
            '[class*="page"][class*="next"]',
            'a[aria-label*="next"]'
        ]
        
        pages_scraped = 1
        consecutive_failures = 0
        
        while pages_scraped < max_pages and consecutive_failures < 3:
            next_button = None
            for selector in pagination_selectors:
                try:
                    next_button = driver.find_element(By.CSS_SELECTOR, selector)
                    if next_button and next_button.is_enabled():
                        break
                except NoSuchElementException:
                    continue
            
            if not next_button or not next_button.is_enabled():
                print("No more pages available")
                break
            
            try:
                driver.execute_script("arguments[0].click();", next_button)
                time.sleep(4)
                
                soup = BeautifulSoup(driver.page_source, 'html.parser')
                page_reviews = extract_reviews_from_soup(soup, url)
                
                if page_reviews:
                    all_reviews.extend(page_reviews)
                    print(f"Page {pages_scraped + 1}: Added {len(page_reviews)} reviews (Total: {len(all_reviews)})")
                    pages_scraped += 1
                    consecutive_failures = 0
                else:
                    print("No reviews on this page")
                    consecutive_failures += 1
                    
            except Exception as e:
                print(f"Pagination error: {e}")
                consecutive_failures += 1
        
        # Strategy 3: "Load More" buttons
        print("Looking for 'Load More' buttons...")
        
        load_more_selectors = [
            '[class*="load"][class*="more"]',
            '[id*="load"][id*="more"]',
            'button[class*="more"]',
            '.load-more-reviews',
            '[data-hook*="load"]'
        ]
    except Exception as e:
        print(f"Amazon scraping error: {e}")
# -*- coding: utf-8 -*-
from flask import Flask, render_template, request, url_for, send_file, jsonify
import pandas as pd
import uuid
import requests
from bs4 import BeautifulSoup
import re
import time
import json
from urllib.parse import urljoin, urlparse, parse_qs
from model import check_reviews

app = Flask(__name__)

# Create upload & results folders if not exist
UPLOAD_FOLDER = "uploads"
RESULT_FOLDER = "results"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(RESULT_FOLDER, exist_ok=True)


def get_session_with_headers():
    """Create a session with enhanced headers"""
    session = requests.Session()
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.9,hi;q=0.8',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'none',
        'Cache-Control': 'max-age=0',
        'DNT': '1'
    }
    session.headers.update(headers)
    return session


def scrape_amazon_reviews(url, session, max_pages=50):
    """Enhanced Amazon review scraping with pagination - Takes ALL reviews including duplicates"""
    all_reviews = []
    
    try:
        # Extract ASIN from URL
        asin_match = re.search(r'/dp/([A-Z0-9]{10})', url)
        if not asin_match:
            asin_match = re.search(r'/product/([A-Z0-9]{10})', url)
        
        if asin_match:
            asin = asin_match.group(1)
            print(f"Found ASIN: {asin}")
            
            # Try direct review page URLs
            review_urls = [
                f"https://www.amazon.in/product-reviews/{asin}/ref=cm_cr_dp_d_show_all_btm",
                f"https://www.amazon.in/product-reviews/{asin}/",
                f"https://www.amazon.in/{asin}/product-reviews/"
            ]
            
            for base_review_url in review_urls:
                print(f"Trying Amazon base URL: {base_review_url}")
                consecutive_failures = 0
                
                for page in range(1, max_pages + 1):
                    try:
                        # Construct paginated URL
                        if page > 1:
                            paginated_url = f"{base_review_url}?pageNumber={page}"
                        else:
                            paginated_url = base_review_url
                        
                        print(f"Scraping Amazon page {page}/{max_pages}: {paginated_url}")
                        response = session.get(paginated_url, timeout=20)
                        
                        if response.status_code != 200:
                            print(f"Page {page} returned status {response.status_code}")
                            consecutive_failures += 1
                            if consecutive_failures >= 3:
                                print("Too many consecutive failures, stopping")
                                break
                            continue
                        
                        consecutive_failures = 0  # Reset on success
                        soup = BeautifulSoup(response.content, 'html.parser')
                        
                        # Updated Amazon selectors for 2024/2025
                        amazon_selectors = [
                            '[data-hook="review-body"] > span',
                            '[data-hook="review-body"] span:not([class*="cr-lightbox"])',
                            'span[data-hook="review-body"] span',
                            '.cr-original-review-text',
                            '.review-text-content span',
                            '[data-hook="review-body"]'
                        ]
                        
                        page_reviews = []
                        for selector in amazon_selectors:
                            elements = soup.select(selector)
                            
                            for element in elements:
                                text = element.get_text(strip=True)
                                if (text and 20 <= len(text) <= 3000 and
                                    not any(skip in text.lower() for skip in [
                                        'verified purchase', 'helpful', 'report abuse',
                                        'comment', 'was this review helpful', 'see all photos',
                                        'by ', 'on '
                                    ])):
                                    # Add ALL reviews including duplicates
                                    page_reviews.append(text)
                            
                            if page_reviews:
                                print(f"Found {len(page_reviews)} reviews with selector '{selector}'")
                                break
                        
                        if page_reviews:
                            all_reviews.extend(page_reviews)
                            print(f"Page {page}: Added {len(page_reviews)} reviews (Total: {len(all_reviews)})")
                            time.sleep(2)  # Respectful delay
                        else:
                            print(f"Page {page}: No reviews found")
                            consecutive_failures += 1
                            if consecutive_failures >= 2:
                                print("No reviews on multiple consecutive pages, stopping")
                                break
                        
                        # Check for "Next page" button to confirm more pages exist
                        next_button = soup.select_one('li.a-last a, [aria-label="Next page"]')
                        if not next_button or 'a-disabled' in str(next_button.get('class', [])):
                            print("No more pages available (next button disabled)")
                            break
                    
                    except Exception as page_error:
                        print(f"Error on Amazon page {page}: {page_error}")
                        consecutive_failures += 1
                        if consecutive_failures >= 3:
                            break
                        time.sleep(3)
                        continue
                
                if all_reviews:
                    print(f"Successfully scraped {len(all_reviews)} Amazon reviews")
                    break  # Success with this URL pattern
        
        # Fallback: Try original URL if no ASIN found
        if not all_reviews:
            print("Trying original Amazon URL as fallback...")
            response = session.get(url, timeout=15)
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Look for "See all reviews" link and follow it
            see_all_link = soup.find('a', string=re.compile(r'See all.*reviews?', re.I))
            if see_all_link and see_all_link.get('href'):
                reviews_url = urljoin(url, see_all_link['href'])
                print(f"Found 'See all reviews' link: {reviews_url}")
                return scrape_amazon_reviews(reviews_url, session, max_pages)
    
    except Exception as e:
        print(f"Amazon scraping error: {e}")
    
    finally:
        print(f"Amazon scraping completed with {len(all_reviews)} total reviews")
    
    return all_reviews


def scrape_flipkart_reviews(url, session, max_pages=50):
    """Enhanced Flipkart review scraping with pagination - Takes ALL reviews including duplicates"""
    all_reviews = []
    
    try:
        # Extract product ID from Flipkart URL
        product_match = re.search(r'/p/([a-zA-Z0-9]+)', url)
        if product_match:
            product_id = product_match.group(1)
            print(f"Found Flipkart product ID: {product_id}")
            
            # Try direct review URLs
            base_review_url = url.replace('/p/', '/product-reviews/')
            consecutive_failures = 0
            
            for page in range(1, max_pages + 1):
                try:
                    if page > 1:
                        review_url = f"{base_review_url}?page={page}"
                    else:
                        review_url = base_review_url
                    
                    print(f"Scraping Flipkart page {page}/{max_pages}: {review_url}")
                    response = session.get(review_url, timeout=20)
                    
                    if response.status_code != 200:
                        # Try alternative pagination format
                        review_url = f"{base_review_url}&page={page}"
                        response = session.get(review_url, timeout=20)
                        
                    if response.status_code != 200:
                        print(f"Page {page} returned status {response.status_code}")
                        consecutive_failures += 1
                        if consecutive_failures >= 3:
                            break
                        continue
                    
                    consecutive_failures = 0
                    soup = BeautifulSoup(response.content, 'html.parser')
                    
                    # Updated Flipkart selectors
                    flipkart_selectors = [
                        '._2cLu-l',
                        '.t-ZTKy',
                        '._11pzQk',
                        '.qwjRop',
                        '.ZmyHeo',
                        'div[class*="_2cLu"]',
                        'div[class*="ZmyHeo"]',
                        '.RcXBOT'
                    ]
                    
                    page_reviews = []
                    for selector in flipkart_selectors:
                        elements = soup.select(selector)
                        
                        for element in elements:
                            text = element.get_text(strip=True)
                            if text and 20 <= len(text) <= 3000:
                                # Add ALL reviews including duplicates
                                page_reviews.append(text)
                        
                        if page_reviews:
                            print(f"Found {len(page_reviews)} reviews with selector '{selector}'")
                            break
                    
                    if page_reviews:
                        all_reviews.extend(page_reviews)
                        print(f"Page {page}: Added {len(page_reviews)} reviews (Total: {len(all_reviews)})")
                        time.sleep(2)
                    else:
                        print(f"Page {page}: No reviews")
                        consecutive_failures += 1
                        if consecutive_failures >= 2:
                            break
                
                except Exception as page_error:
                    print(f"Error on Flipkart page {page}: {page_error}")
                    consecutive_failures += 1
                    if consecutive_failures >= 3:
                        break
                    time.sleep(3)
                    continue
        
        # Fallback: Try original URL
        if not all_reviews:
            print("Trying original Flipkart URL as fallback...")
            response = session.get(url, timeout=15)
            soup = BeautifulSoup(response.content, 'html.parser')
            
            for selector in ['._2cLu-l', '.t-ZTKy', '._11pzQk']:
                elements = soup.select(selector)
                for element in elements:
                    text = element.get_text(strip=True)
                    if text and len(text) > 20:
                        all_reviews.append(text)
                if all_reviews:
                    break
    
    except Exception as e:
        print(f"Flipkart scraping error: {e}")
    
    finally:
        print(f"Flipkart scraping completed with {len(all_reviews)} total reviews")
    
    return all_reviews


def scrape_meesho_reviews(url, session, max_pages=30):
    """Enhanced Meesho review scraping - Takes ALL reviews including duplicates"""
    all_reviews = []
    
    try:
        consecutive_failures = 0
        
        for page in range(1, max_pages + 1):
            try:
                if page > 1:
                    paginated_urls = [
                        f"{url}?page={page}",
                        f"{url}&page={page}",
                        f"{url}#page-{page}"
                    ]
                else:
                    paginated_urls = [url]
                
                for paginated_url in paginated_urls:
                    print(f"Scraping Meesho page {page}/{max_pages}: {paginated_url}")
                    response = session.get(paginated_url, timeout=20)
                    
                    if response.status_code == 200:
                        break
                else:
                    consecutive_failures += 1
                    if consecutive_failures >= 3:
                        break
                    continue
                
                consecutive_failures = 0
                soup = BeautifulSoup(response.content, 'html.parser')
                
                meesho_selectors = [
                    '[data-testid*="review"]',
                    '.ReviewCard__reviewText',
                    '[class*="Review"][class*="Text"]',
                    '.review-content',
                    '[class*="review"][class*="text"]',
                    'div[class*="review"] p',
                    '[class*="ReviewCard"] div',
                    '[class*="UserReview"]'
                ]
                
                page_reviews = []
                for selector in meesho_selectors:
                    elements = soup.select(selector)
                    
                    for element in elements:
                        text = element.get_text(strip=True)
                        if text and 20 <= len(text) <= 3000:
                            # Add ALL reviews including duplicates
                            page_reviews.append(text)
                    
                    if page_reviews:
                        print(f"Found {len(page_reviews)} reviews with selector '{selector}'")
                        break
                
                if page_reviews:
                    all_reviews.extend(page_reviews)
                    print(f"Page {page}: Added {len(page_reviews)} reviews (Total: {len(all_reviews)})")
                    time.sleep(2)
                else:
                    consecutive_failures += 1
                    if consecutive_failures >= 2:
                        break
            
            except Exception as page_error:
                print(f"Error on Meesho page {page}: {page_error}")
                consecutive_failures += 1
                if consecutive_failures >= 3:
                    break
                time.sleep(3)
                continue
    
    except Exception as e:
        print(f"Meesho scraping error: {e}")
    
    finally:
        print(f"Meesho scraping completed with {len(all_reviews)} total reviews")
    
    return all_reviews


def scrape_with_selenium_pagination(url, max_pages=20):
    """Selenium-based scraping with pagination and dynamic loading - FIXED"""
    try:
        from selenium import webdriver
        from selenium.webdriver.chrome.options import Options
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC
        from selenium.common.exceptions import TimeoutException, NoSuchElementException
        
        print(f"Starting Selenium scraping with pagination (max {max_pages} pages)...")
        
        chrome_options = Options()
        chrome_options.add_argument('--headless')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--window-size=1920,1080')
        chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
        
        driver = webdriver.Chrome(options=chrome_options)
        driver.get(url)
        
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )
        
        all_reviews = []
        unique_reviews = set()
        
        # Strategy 1: Infinite scroll loading
        print("Attempting infinite scroll strategy...")
        last_height = driver.execute_script("return document.body.scrollHeight")
        scroll_attempts = 0
        max_scrolls = 20
        
        while scroll_attempts < max_scrolls:
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(3)
            
            new_height = driver.execute_script("return document.body.scrollHeight")
            
            if new_height == last_height:
                print(f"No more content loaded after scroll {scroll_attempts + 1}")
                break
            
            last_height = new_height
            scroll_attempts += 1
            print(f"Scroll {scroll_attempts}: New content loaded")
        
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        reviews = extract_reviews_from_soup(soup, url)
        for review in reviews:
            text_hash = hash(review.lower())
            if text_hash not in unique_reviews:
                unique_reviews.add(text_hash)
                all_reviews.append(review)
        
        # Strategy 2: Pagination buttons
        print("Attempting pagination strategy...")
        
        pagination_selectors = [
            'li.a-last a',
            '.a-pagination .a-normal',
            '[aria-label="Go to next page"]',
            '._1LKTO3',
            '.ge-49M',
            '[class*="next"]',
            '.pagination a',
            '[class*="page"][class*="next"]',
            'a[aria-label*="next"]'
        ]
        
        pages_scraped = 1
        consecutive_failures = 0
        
        while pages_scraped < max_pages and consecutive_failures < 3:
            next_button = None
            for selector in pagination_selectors:
                try:
                    next_button = driver.find_element(By.CSS_SELECTOR, selector)
                    if next_button and next_button.is_enabled():
                        break
                except NoSuchElementException:
                    continue
            
            if not next_button or not next_button.is_enabled():
                print("No more pages available")
                break
            
            try:
                driver.execute_script("arguments[0].click();", next_button)
                time.sleep(4)
                
                soup = BeautifulSoup(driver.page_source, 'html.parser')
                page_reviews = extract_reviews_from_soup(soup, url)
                
                new_reviews = []
                for review in page_reviews:
                    text_hash = hash(review.lower())
                    if text_hash not in unique_reviews:
                        unique_reviews.add(text_hash)
                        new_reviews.append(review)
                
                if new_reviews:
                    all_reviews.extend(new_reviews)
                    print(f"Page {pages_scraped + 1}: Added {len(new_reviews)} reviews (Total: {len(all_reviews)})")
                    pages_scraped += 1
                    consecutive_failures = 0
                else:
                    print("No new reviews on this page")
                    consecutive_failures += 1
                    
            except Exception as e:
                print(f"Pagination error: {e}")
                consecutive_failures += 1
        
        # Strategy 3: "Load More" buttons
        print("Looking for 'Load More' buttons...")
        
        load_more_selectors = [
            '[class*="load"][class*="more"]',
            '[id*="load"][id*="more"]',
            'button[class*="more"]',
            '.load-more-reviews',
            '[data-hook*="load"]'
        ]
        
        load_attempts = 0
        while load_attempts < 10:
            load_more_button = None
            
            for selector in load_more_selectors:
                try:
                    load_more_button = driver.find_element(By.CSS_SELECTOR, selector)
                    if load_more_button and load_more_button.is_displayed():
                        break
                except NoSuchElementException:
                    continue
            
            if not load_more_button:
                break
            
            try:
                driver.execute_script("arguments[0].click();", load_more_button)
                time.sleep(3)
                
                soup = BeautifulSoup(driver.page_source, 'html.parser')
                current_reviews = extract_reviews_from_soup(soup, url)
                
                if current_reviews and len(current_reviews) > len(all_reviews):
                    all_reviews = current_reviews
                    print(f"Load more {load_attempts + 1}: Total reviews now {len(all_reviews)}")
                    load_attempts += 1
                else:
                    break
                    
            except Exception as e:
                print(f"Load more error: {e}")
                break
        
        driver.quit()
        print(f"Selenium scraping complete: {len(all_reviews)} reviews")
        return all_reviews
        
    except ImportError:
        print("Selenium not installed. Install with: pip install selenium")
        return []
    except Exception as e:
        print(f"Selenium scraping error: {e}")
        try:
            driver.quit()
        except:
            pass
        return []


def extract_reviews_from_soup(soup, url):
    """Extract reviews from BeautifulSoup object with enhanced selectors"""
    reviews = []
    
    if 'amazon' in url.lower():
        amazon_selectors = [
            '[data-hook="review-body"] > span',
            '[data-hook="review-body"] span:not([class*="cr-lightbox"])',
            'span[data-hook="review-body"] span',
            '.cr-original-review-text',
            '[data-hook="review-body"]',
            '.review-text-content span',
            '.a-size-base.review-text span'
        ]
        
        for selector in amazon_selectors:
            elements = soup.select(selector)
            for element in elements:
                text = element.get_text(strip=True)
                if (text and 20 <= len(text) <= 3000 and
                    not any(skip in text.lower() for skip in [
                        'verified purchase', 'helpful', 'report abuse', 'by ', 'on ',
                        'was this review helpful', 'comment', 'see all photos'
                    ])):
                    reviews.append(text)
            if reviews:
                break
                
    elif 'flipkart' in url.lower():
        flipkart_selectors = [
            '._2cLu-l', '.t-ZTKy', '._11pzQk', '.qwjRop', '.ZmyHeo',
            'div[class*="_2cLu"]', 'div[class*="ZmyHeo"]', '.RcXBOT'
        ]
        
        for selector in flipkart_selectors:
            elements = soup.select(selector)
            for element in elements:
                text = element.get_text(strip=True)
                if text and 20 <= len(text) <= 3000:
                    reviews.append(text)
            if reviews:
                break
                
    elif 'meesho' in url.lower():
        meesho_selectors = [
            '[data-testid*="review"]', '.ReviewCard__reviewText', 
            '[class*="Review"][class*="Text"]', '.review-content',
            'div[class*="review"] p', '[class*="ReviewCard"] div'
        ]
        
        for selector in meesho_selectors:
            elements = soup.select(selector)
            for element in elements:
                text = element.get_text(strip=True)
                if text and 20 <= len(text) <= 3000:
                    reviews.append(text)
            if reviews:
                break
    
    else:
        generic_selectors = [
            '[class*="review"][class*="text"]', '[class*="review"][class*="content"]',
            '.review-content', '.user-review', '.customer-review',
            'div[class*="review"] p', 'div[class*="review"] span'
        ]
        
        for selector in generic_selectors:
            elements = soup.select(selector)
            for element in elements:
                text = element.get_text(strip=True)
                if text and 20 <= len(text) <= 3000:
                    reviews.append(text)
            if reviews:
                break
    
    return reviews


def scrape_reviews_from_url(url, max_reviews=10000):
    """Main function to scrape reviews with multiple strategies - Takes ALL reviews"""
    session = get_session_with_headers()
    all_reviews = []
    
    try:
        print(f"Starting comprehensive scraping for: {url}")
        print(f"Target: Up to {max_reviews} reviews")
        
        # Calculate pages needed (assume ~10-15 reviews per page)
        estimated_pages = min(50, (max_reviews // 10) + 5)
        
        # Strategy 1: Platform-specific scraping with pagination
        if 'amazon' in url.lower():
            all_reviews = scrape_amazon_reviews(url, session, max_pages=estimated_pages)
        elif 'flipkart' in url.lower():
            all_reviews = scrape_flipkart_reviews(url, session, max_pages=estimated_pages)
        elif 'meesho' in url.lower():
            all_reviews = scrape_meesho_reviews(url, session, max_pages=estimated_pages)
        else:
            print("Using generic scraping approach...")
            response = session.get(url, timeout=15)
            soup = BeautifulSoup(response.content, 'html.parser')
            all_reviews = extract_reviews_from_soup(soup, url)
        
        # Strategy 2: If basic scraping didn't get enough reviews, try Selenium
        # if len(all_reviews) < 20:
        #     print(f"Only found {len(all_reviews)} reviews with basic scraping, trying Selenium...")
        #     selenium_reviews = scrape_with_selenium_pagination(url, max_pages=estimated_pages)
        #     if len(selenium_reviews) > len(all_reviews):
        #         all_reviews = selenium_reviews

        if len(all_reviews) < 20 and USE_SELENIUM:
            print("Using Selenium fallback...")
            selenium_reviews = scrape_with_selenium_pagination(url, max_pages=estimated_pages)
            if len(selenium_reviews) > len(all_reviews):
                all_reviews = selenium_reviews
        else:
            if not USE_SELENIUM:
                print("Selenium disabled (deployment mode)")

        
        # Strategy 3: Enhanced text mining fallback
        if len(all_reviews) < 10:
            print("Attempting enhanced text mining fallback...")
            response = session.get(url, timeout=15)
            soup = BeautifulSoup(response.content, 'html.parser')
            
            for script in soup(["script", "style", "nav", "header", "footer"]):
                script.decompose()
            
            text_elements = soup.find_all(['p', 'span', 'div'], string=True)
            
            review_patterns = [
                r'\b(good|great|excellent|amazing|awesome|fantastic|wonderful|perfect|love|best|nice|satisfied)\b',
                r'\b(bad|terrible|awful|worst|hate|disappointed|poor|useless|waste|fake|broken)\b',
                r'\b(product|item|bought|purchase|order|delivery|service|quality|recommend)\b',
                r'\b\d+\s*(star|rating|out of)\b',
                r'\b(months?|weeks?|days?|years?)\s*(ago|later|back)\b'
            ]
            
            combined_pattern = '|'.join(review_patterns)
            pattern = re.compile(combined_pattern, re.IGNORECASE)
            
            for element in text_elements:
                text = element.get_text(strip=True)
                if (30 <= len(text) <= 1000 and 
                    len(pattern.findall(text)) >= 2 and
                    not any(skip in text.lower() for skip in [
                        'copyright', 'privacy', 'terms', 'navigation', 'menu',
                        'footer', 'header', 'advertisement', 'sponsored'
                    ])):
                    all_reviews.append(text)
                    if len(all_reviews) >= 100:
                        break
        
        # Clean and deduplicate reviews (minimal deduplication - only exact duplicates)
        cleaned_reviews = []
        seen_exact = set()
        
        for review in all_reviews:
            cleaned = re.sub(r'\s+', ' ', review).strip()
            cleaned = re.sub(r'[^\w\s.,!?()-]', '', cleaned)
            
            # Only remove EXACT duplicates (same text)
            if (20 <= len(cleaned) <= 2000 and 
                cleaned.lower() not in seen_exact and 
                not cleaned.lower().startswith(('by ', 'on ', 'verified', 'helpful', 'report', 'was this'))):
                seen_exact.add(cleaned.lower())
                cleaned_reviews.append(cleaned)
        
        print(f"Final result: {len(cleaned_reviews)} reviews extracted (removed only exact duplicates)")
        
        if cleaned_reviews:
            print("\nSample reviews found:")
            for i, review in enumerate(cleaned_reviews[:3]):
                print(f"{i+1}. {review[:150]}...")
        
        return cleaned_reviews[:max_reviews]
        
    except Exception as e:
        print(f"Error in scrape_reviews_from_url: {e}")
        return []

@app.route("/")
def home():
    """Home page with upload/link input"""
    return render_template("home.html")


@app.route("/about")
def about():
    """About page with developer details"""
    developers = [
        {
            "name": "Darshan Baldha", 
            "photo": "darshan.jpg", 
            "role": "Developer"
        },
    ]
    return render_template("about.html", developers=developers)


@app.route("/test-scraping", methods=["POST"])
def test_scraping():
    """Test endpoint for scraping without ML processing"""
    url = request.form.get("url", "").strip()
    
    if not url:
        return jsonify({"error": "No URL provided"}), 400
    
    if not (url.startswith('http://') or url.startswith('https://')):
        url = 'https://' + url
    
    print(f"Testing scraping for: {url}")
    reviews = scrape_reviews_from_url(url, max_reviews=100)
    
    return jsonify({
        "url": url,
        "reviews_found": len(reviews),
        "sample_reviews": reviews[:10] if reviews else [],
        "message": f"Successfully found {len(reviews)} reviews" if reviews else "No reviews found"
    })


@app.route("/process", methods=["POST"])
def process():
    """Process uploaded dataset or link and classify reviews"""
    reviews = []

    # Case 1: File Upload
    if "file" in request.files and request.files["file"].filename != "":
        file = request.files["file"]
        if not file.filename.endswith('.csv'):
            return jsonify({"error": "Please upload a CSV file"}), 400
            
        filepath = os.path.join(UPLOAD_FOLDER, file.filename)
        file.save(filepath)

        try:
            encodings = ['utf-8', 'latin1', 'iso-8859-1', 'cp1252']
            df = None
            
            for encoding in encodings:
                try:
                    print(f"Trying encoding: {encoding}")
                    
                    try:
                        df = pd.read_csv(filepath, usecols=["reviews.text"], encoding=encoding, nrows=1000)
                        reviews = df["reviews.text"].dropna().astype(str).tolist()
                        print(f"Found reviews in 'reviews.text' column with {encoding} encoding")
                        break
                    except:
                        df = pd.read_csv(filepath, encoding=encoding, nrows=1000)
                        
                        possible_cols = [
                            "reviews.text", "review", "Review", "reviews", "Reviews", 
                            "text", "Text", "comment", "Comment", "review_text", 
                            "reviewText", "content", "Content", "feedback", "Feedback"
                        ]
                        
                        col = None
                        for c in possible_cols:
                            if c in df.columns:
                                col = c
                                break
                        
                        if col:
                            reviews = df[col].dropna().astype(str).tolist()
                            print(f"Found reviews in '{col}' column with {encoding} encoding")
                            break
                        else:
                            available_cols = ", ".join(df.columns.tolist()[:10])
                            print(f"Available columns: {available_cols}")
                            continue
                            
                except Exception as e:
                    print(f"Error with encoding {encoding}: {e}")
                    continue
            
            if not reviews:
                if df is not None:
                    available_cols = ", ".join(df.columns.tolist()[:10])
                    return jsonify({
                        "error": f"No review column found. Available columns: {available_cols}. Please ensure your CSV has a column named 'reviews.text', 'review', or 'Review'."
                    }), 400
                else:
                    return jsonify({"error": "Could not read CSV file. Please check file format and encoding."}), 400
                
        except Exception as e:
            return jsonify({"error": f"Error reading CSV file: {str(e)}"}), 400

    # Case 2: URL Link Input - Enhanced Web Scraping with Pagination
    elif "link" in request.form and request.form["link"].strip() != "":
        link = request.form["link"].strip()
        
        if not (link.startswith('http://') or link.startswith('https://')):
            link = 'https://' + link
        
        url_pattern = re.compile(
            r'^https?://'
            r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'
            r'localhost|'
            r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'
            r'(?::\d+)?'
            r'(?:/?|[/?]\S+)', re.IGNORECASE)
        
        if not url_pattern.match(link):
            return jsonify({"error": "Invalid URL format. Please provide a valid product page URL (e.g., https://amazon.in/product-name/dp/XXXXXXXXXX)"}), 400
        
        print(f"Starting comprehensive web scraping for: {link}")
        
        # Enhanced scraping with NO limit - get ALL reviews
        reviews = scrape_reviews_from_url(link, max_reviews=10000)
        
        if not reviews:
            return jsonify({
                "error": f"Could not extract reviews from: {link}. "
                        f"Possible solutions: "
                        f"1) Ensure the URL is a product page with visible customer reviews "
                        f"2) Try a different product URL from the same website "
                        f"3) Check if reviews require login/registration "
                        f"4) Install Selenium for JavaScript-heavy sites: pip install selenium "
                        f"5) Use the /test-scraping endpoint to debug the URL first. "
                        f"Note: Some sites may block automated access or require special handling."
            }), 400
        
        print(f"Successfully extracted {len(reviews)} reviews from URL")
    else:
        return jsonify({"error": "Please provide either a CSV file or a valid product URL"}), 400

    # Validate reviews
    if not reviews or len(reviews) == 0:
        return jsonify({"error": "No reviews found to analyze. Please check your input."}), 400

    # NO filtering or duplicate removal - process ALL reviews as-is
    print(f"Processing {len(reviews)} reviews through ML model (NO filtering applied)...")

    # Process reviews through ML model
    try:
        results_df = check_reviews(reviews)
        
        if results_df.empty:
            return jsonify({"error": "No valid reviews to process after ML analysis"}), 400
            
    except Exception as e:
        print(f"ML model error: {e}")
        return jsonify({"error": f"Error processing reviews through ML model: {str(e)}"}), 400

    # Save results to CSV
    uid = str(uuid.uuid4())[:8]
    result_file = os.path.join(RESULT_FOLDER, f"result_{uid}.csv")
    
    try:
        results_df.to_csv(result_file, index=False, encoding='utf-8')
        print(f"Results saved to: {result_file}")
    except Exception as e:
        print(f"Error saving results: {e}")
        return jsonify({"error": "Error saving results"}), 400

    # Convert DataFrame to dict for frontend
    try:
        results = results_df.to_dict(orient="records")
        counts = results_df["prediction"].value_counts().to_dict()
        
        response_data = {
            "results": results,
            "counts": counts,
            "download_url": url_for("download_file", filename=os.path.basename(result_file)),
            "total_reviews_scraped": len(reviews),
            "total_reviews": len(reviews),
            "processed_reviews": len(results_df),
            "statistics": {
                "average_review_length": sum(len(str(r)) for r in reviews) / len(reviews) if reviews else 0,
                "longest_review": max(len(str(r)) for r in reviews) if reviews else 0,
                "shortest_review": min(len(str(r)) for r in reviews) if reviews else 0
            }
        }
        
        print(f"Returning results: {len(results)} processed reviews")
        return jsonify(response_data)
        
    except Exception as e:
        print(f"Error preparing response: {e}")
        return jsonify({"error": "Error preparing results for display"}), 400


@app.route("/download/<filename>")
def download_file(filename):
    """Download result CSV file"""
    try:
        file_path = os.path.join(RESULT_FOLDER, filename)
        if not os.path.exists(file_path):
            return jsonify({"error": "File not found"}), 404
        return send_file(file_path, as_attachment=True)
    except Exception as e:
        return jsonify({"error": f"Error downloading file: {str(e)}"}), 500


@app.route("/get-review-count", methods=["POST"])
def get_review_count():
    """Get estimated review count from URL without full processing"""
    url = request.form.get("url", "").strip()
    
    if not url:
        return jsonify({"error": "No URL provided"}), 400
    
    if not (url.startswith('http://') or url.startswith('https://')):
        url = 'https://' + url
    
    try:
        session = get_session_with_headers()
        response = session.get(url, timeout=10)
        soup = BeautifulSoup(response.content, 'html.parser')
        
        review_count_patterns = [
            r'(\d+,?\d*)\s*(?:customer\s*)?reviews?',
            r'(\d+,?\d*)\s*(?:total\s*)?ratings?',
            r'See\s*all\s*(\d+,?\d*)\s*reviews?'
        ]
        
        page_text = soup.get_text()
        estimated_count = 0
        
        for pattern in review_count_patterns:
            matches = re.findall(pattern, page_text, re.IGNORECASE)
            if matches:
                try:
                    count = int(matches[0].replace(',', ''))
                    estimated_count = max(estimated_count, count)
                except:
                    continue
        
        return jsonify({
            "url": url,
            "estimated_total_reviews": estimated_count,
            "message": f"Estimated {estimated_count} total reviews available" if estimated_count else "Could not estimate review count"
        })
        
    except Exception as e:
        return jsonify({"error": f"Error checking review count: {str(e)}"}), 500


@app.route("/scrape-maximum", methods=["POST"])
def scrape_maximum():
    """Scrape maximum possible reviews (use with caution)"""
    url = request.form.get("url", "").strip()
    max_reviews = int(request.form.get("max_reviews", 1000))
    
    if not url:
        return jsonify({"error": "No URL provided"}), 400
    
    if not (url.startswith('http://') or url.startswith('https://')):
        url = 'https://' + url
    
    if max_reviews > 2000:
        return jsonify({"error": "Maximum limit is 2000 reviews to prevent server overload"}), 400
    
    print(f"Starting maximum scraping for: {url} (limit: {max_reviews})")
    
    reviews = scrape_reviews_from_url(url, max_reviews=max_reviews)
    
    return jsonify({
        "url": url,
        "reviews_found": len(reviews),
        "sample_reviews": reviews[:5] if reviews else [],
        "all_reviews": reviews,
        "message": f"Found {len(reviews)} reviews (requested max: {max_reviews})"
    })


@app.errorhandler(404)
def not_found(error):
    return jsonify({"error": "Endpoint not found"}), 404


@app.errorhandler(500)
def internal_error(error):
    return jsonify({"error": "Internal server error"}), 500


@app.errorhandler(413)
def payload_too_large(error):
    return jsonify({"error": "File too large. Please upload a smaller CSV file."}), 413


if __name__ == "__main__":
    print("Starting Enhanced Flask Review Analyzer...")
    print(f"Upload folder: {UPLOAD_FOLDER}")
    print(f"Results folder: {RESULT_FOLDER}")
    print("Features enabled:")
    print("- Multi-page review scraping (Amazon: 50 pages, Flipkart: 50 pages, Meesho: 30 pages)")
    print("- Takes ALL reviews including duplicates (NO filtering)")
    print("- NO review limit - scrapes everything available")
    print("- Enhanced fake review detection (lowered threshold)")
    print("- Selenium fallback support")
    print("- Platform-specific optimizations")
    print("- Proper try-except-finally blocks")
    print("Available endpoints:")
    print("- /process (main processing)")
    print("- /test-scraping (test URL without ML)")
    print("- /get-review-count (estimate total reviews)")
    print("- /scrape-maximum (scrape up to specified limit)")
    app.run()