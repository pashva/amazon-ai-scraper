import os
import base64
import logging
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
import sys

from ai import generate_json

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger()

chrome_driver_path = './chromedriver'

def decode_credentials(encoded_username, encoded_password):
    """Decode base64 encoded credentials."""
    username = base64.b64decode(encoded_username).decode('utf-8')
    password = base64.b64decode(encoded_password).decode('utf-8')
    return username, password

def setup_driver():
    """Setup the Selenium WebDriver with options."""
    options = Options()
    options.add_argument('--start-maximized')
    service = Service(chrome_driver_path)
    driver = webdriver.Chrome(service=service, options=options)
    return driver

def handle_alerts(driver):
    """Handle any unexpected popups or alerts."""
    try:
        WebDriverWait(driver, 3).until(EC.alert_is_present())
        alert = driver.switch_to.alert
        alert.dismiss()
        logger.info('Unexpected alert dismissed.')
    except Exception as e:
        # No alert found
        pass

def login_amazon(driver, username, password):
    """Login to Amazon using provided credentials."""
    logger.info('Navigating to Amazon login page.')
    driver.get('https://www.amazon.in/ap/signin?openid.pape.max_auth_age=0&openid.return_to=https%3A%2F%2Fwww.amazon.in%2F%3Fref_%3Dnav_custrec_signin&openid.identity=http%3A%2F%2Fspecs.openid.net%2Fauth%2F2.0%2Fidentifier_select&openid.assoc_handle=inflex&openid.mode=checkid_setup&openid.claimed_id=http%3A%2F%2Fspecs.openid.net%2Fauth%2F2.0%2Fidentifier_select&openid.ns=http%3A%2F%2Fspecs.openid.net%2Fauth%2F2.0')
    WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, 'ap_email')))
    handle_alerts(driver)

    logger.info('Entering username.')
    email_field = driver.find_element(By.ID, 'ap_email')
    email_field.send_keys(username)
    email_field.send_keys(Keys.RETURN)
    
    WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, 'ap_password')))
    handle_alerts(driver)
    logger.info('Entering password.')
    password_field = driver.find_element(By.ID, 'ap_password')
    password_field.send_keys(password)
    password_field.send_keys(Keys.RETURN)

def navigate_to_orders(driver):
    """Navigate to the orders page."""
    logger.info('Navigating to the orders page.')
    WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, 'nav-orders')))
    handle_alerts(driver)
    orders_link = driver.find_element(By.ID, 'nav-orders')
    orders_link.click()

def scrape_order_data(driver, enable_ai):
    """Scrape order data from the orders page."""
    WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CSS_SELECTOR, 'div.a-box-group.a-spacing-base.order')))
    handle_alerts(driver)

    orders = []
    total_orders = driver.find_elements(By.CLASS_NAME, 'order')
    total_elems = len(total_orders)

    if enable_ai:
        ai_scanned_order_details = []
        for i, element in enumerate(total_orders):
            if not os.path.exists('orders'):
                os.makedirs('orders')
            
            with open(f'orders/order_{i}.html', 'w', encoding='utf-8') as file:
                file.write(element.get_attribute('outerHTML') + '\n')
                object = generate_json(element.get_attribute('outerHTML'))
                ai_scanned_order_details.append(object)
        with open('orders_ai.json', 'w') as f:
            f.write(str(ai_scanned_order_details))
    else:
        for i in range(9, 9 + total_elems):
            order = {}
            order['order_date'] = driver.find_element(By.XPATH, f'/html/body/div[1]/section/div[1]/div[{i}]/div/div[1]/div/div/div/div[1]/div/div[1]/div[2]/span').text.strip()
            order['order_price'] = 'Rs ' + driver.find_element(By.XPATH, f'/html/body/div[1]/section/div[1]/div[{i}]/div/div[1]/div/div/div/div[1]/div/div[2]/div[2]/span/span').text.strip()
            order['order_id'] = driver.find_element(By.XPATH, f'/html/body/div[1]/section/div[1]/div[{i}]/div/div[1]/div/div/div/div[2]/div[1]/span[2]/bdi').text.strip()
            order['delivery_status'] = driver.find_element(By.XPATH, f'/html/body/div[1]/section/div[1]/div[{i}]/div/div[2]/div/div[1]/div[1]/div[1]').get_attribute('innerText').strip()
            order['items'] = driver.find_element(By.XPATH, f'/html/body/div[1]/section/div[1]/div[{i}]/div/div[2]/div/div[2]/div/div[1]/div/div/div/div[2]/div[1]/a').text.strip()
            order['ship_to'] = driver.find_element(By.XPATH, f'/html/body/div[1]/section/div[1]/div[{i}]/div/div[1]/div/div/div/div[1]/div/div[3]/div/div[2]/div/span/a').text.strip()
            try:
                elem = driver.find_element(By.XPATH, f'/html/body/div[1]/section/div[1]/div[{i}]/div/div[2]/div/div[2]/div/div[1]/div/div/div/div[2]/div[2]/span/div')
            except:
                elem = None
            if elem:
                order['replace_or_return'] = elem.text.strip()
            orders.append(order)
        with open('orders_non_ai.json', 'w') as f:
            f.write(str(orders))

def main():
    amazon_username = os.environ.get('AMAZON_USERNAME')
    amazon_password = os.environ.get('AMAZON_PASSWORD')

    if not amazon_username or not amazon_password:
        logger.error('Amazon credentials not set in environment variables.')
        return

    amazon_username, amazon_password = decode_credentials(amazon_username, amazon_password)

    enable_ai = '--enable-ai' in sys.argv
    driver = setup_driver()

    try:
        login_amazon(driver, amazon_username, amazon_password)
        navigate_to_orders(driver)
        scrape_order_data(driver, enable_ai)
    except Exception as e:
        logger.exception('An error occurred during the process.')
    finally:
        logger.info('Quitting the driver.')
        driver.quit()

if __name__ == '__main__':
    main()
