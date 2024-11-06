from playwright.async_api import async_playwright
import asyncio
import pandas as pd
from datetime import datetime
import os

# File to store price history
PRICE_FILE = 'prices_comparison.csv'

# List of product page URLs to scrape
PRODUCT_PAGES = [
    "https://www.apply3d.com/asiga",
    # "https://www.apply3d.com/asiga?page=2",
    # "https://www.apply3d.com/bluecast",
    # "https://www.apply3d.com/detax",
    # "https://www.apply3d.com/keyprint",
    # "https://www.apply3d.com/loctite",
    # "https://www.apply3d.com/nk-optik",
    # "https://www.apply3d.com/phrozen",
    # "https://www.apply3d.com/phrozen?page=2",
]

async def login(page, email, password):
    """Log into the site."""
    await page.goto("https://www.apply3d.com/")
    await page.wait_for_load_state("networkidle")
    await page.click('button:has(span:text("Login"))')
    await page.fill('input[type="email"]', email)
    await page.fill('input[type="password"]', password)
    await page.click('button:has(span.l7_2fn:text("Log In"))')
    print("Logged in successfully.")

async def extract_product_info(product):
    """Extracts the name and price or status for an individual product."""
    name_element = await product.query_selector('p[data-hook="product-item-name"]')
    product_name = await name_element.text_content() if name_element else "No Name"

    out_of_stock_element = await product.query_selector('span[data-hook="product-item-out-of-stock"]')
    if out_of_stock_element:
        return f"{product_name} - Out of stock", await out_of_stock_element.text_content(), None 

    price_element = await product.query_selector('span[data-hook="product-item-price-to-pay"]')
    if price_element:
        return product_name, await price_element.text_content(), None  

    from_price_element = await product.query_selector('span[data-hook="price-range-from"]')
    if from_price_element:
        product_link = await product.query_selector('a[data-hook="product-item-product-details-link"]')
        link = await product_link.get_attribute('href') if product_link else None
        return product_name, None, link 

    return product_name, None, None 

async def scrape_page(page, url):
    """Navigate to the page and retrieve product elements."""
    await page.goto(url)
    await page.wait_for_load_state("domcontentloaded")
    return await page.query_selector_all('li[data-hook="product-list-grid-item"]')

async def scrape_prices():
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()

        await login(page, 'testy888777@hotmail.com', 'Breadboard99')

        # Data collection lists
        all_product_names, all_prices, all_product_from_price_pages = [], [], []

        # Scrape each product page
        for url in PRODUCT_PAGES:
            print(f"Scraping page: {url}")
            product_list = await scrape_page(page, url)
            for product in product_list:
                name, price, link = await extract_product_info(product)
                if price:
                    all_product_names.append(name.strip())
                    all_prices.append(price.strip())
                elif link:
                    all_product_from_price_pages.append(link.strip())
        
        print("Number of products with price ranges:", len(all_product_from_price_pages))   

        # Process individual product pages for "from" price ranges
        await process_price_ranges(page, all_product_from_price_pages, all_product_names, all_prices)

        await save_price_data(all_product_names, all_prices)

        await browser.close()

async def process_price_ranges(page, product_pages, names, prices):
    """Processes individual product pages that have a price range."""
    for product_page in product_pages:
        print("Navigating to", product_page)
        await page.goto(product_page)
        await close_banner_if_present(page)
        await page.wait_for_load_state("domcontentloaded")

        name_element = await page.query_selector('h1[data-hook="product-title"]')
        product_name = await name_element.text_content() if name_element else "No Name"
        
        dropdown_button = await page.query_selector('button[data-hook="dropdown-base"]')
        if dropdown_button:
            await handle_dropdown(page, dropdown_button, names, prices, retries=3) 


async def close_banner_if_present(page):
    """Closes a consent banner if present on the page."""
    try:
        await page.wait_for_selector('button[data-hook="consent-banner-apply-button"]', timeout=5000)
        print("button found")
        await page.click('button[data-hook="consent-banner-apply-button"]')
        print("button clicked")
    except:
        print("Banner not found")

async def handle_dropdown(page, dropdown_button, names, prices, retries):
    """Handles dropdown interaction and retrieves prices for each option, with retry on failure."""
    print("Handling dropdown")

    try:
        # Open the dropdown menu
        await page.evaluate('(element) => element.click()', dropdown_button)
        await page.wait_for_timeout(1000)

        # Look for the dropdown options container
        container = await page.query_selector('div#dropdown-options-container_-1')
        if container:
            print("Container found")
            options = await container.query_selector_all('div[data-hook="option"][role="menuitem"]')
            print("Options found:", len(options))

            for option in options:
                # Adjust option selector dynamically
                name_element = await option.query_selector('span.sNipX2_')
                name = await name_element.text_content() if name_element else "Unnamed Option"
                
                print(f"Looking for title with name: {name}")
                title = await page.query_selector(f'div[title="{name}"]')

                if title:
                    # Click to select the option directly
                    await page.evaluate('(element) => element.click()', title)
                    await page.wait_for_timeout(2000)
                    # Retrieve name and price for the selected option
                    try:
                        price_element = await page.query_selector('span[data-hook="formatted-primary-price"]')
                        await page.wait_for_timeout(1000)  
                        price = await price_element.text_content() if price_element else "No Price"
                    except Exception as e:
                        print(f"Error retrieving price: {e}")
                        name, price = "Error Option", "Error Price"

                    print(f"Option: {name} - Price: {price}")
                    names.append(name.strip())
                    prices.append(price.strip())
                else:
                    print(f"Title element not found for {name}")
                    
                # Close and reopen dropdown if necessary
                await page.evaluate('(element) => element.click()', dropdown_button)
                await page.wait_for_timeout(1500)


        else:
            print("Dropdown options container not found.")
            if retries > 0:
                print("Retrying...")
                await page.reload()
                await page.wait_for_timeout(3000)
                dropdown_button = await page.query_selector('button[data-hook="dropdown-base"]')
                if dropdown_button:
                    await handle_dropdown(page, dropdown_button, names, prices, retries=3)
            else:
                print("Failed to find dropdown options container after retries.")

    except Exception as e:
        print(f"Error handling dropdown: {e}")



async def save_price_data(names, prices):
    """Saves or updates price data in a CSV file."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    if not os.path.exists(PRICE_FILE):
        create_new_price_file(names, prices, timestamp)
    else:
        update_existing_price_file(names, prices, timestamp)

def create_new_price_file(names, prices, timestamp):
    """Creates a new price file with the initial data."""
    df = pd.DataFrame({
        "Product Names": names,
        "New to site?": ["YES"] * len(names),
        "Previous Prices": ["" for _ in names],
        "Previous Timestamp": ["" for _ in names],
        "Current Prices": prices,
        "Current Timestamp": [timestamp] * len(names),
        "Price Difference": ["N/A"] * len(names)
    })
    df.to_csv(PRICE_FILE, index=False)
    print(f"Prices and product names saved to '{PRICE_FILE}'")

def update_existing_price_file(names, prices, timestamp):
    """Updates the existing price file by comparing and adding new data."""
    df = pd.read_csv(PRICE_FILE)
    df['Previous Prices'], df['Previous Timestamp'] = df['Current Prices'], df['Current Timestamp']
    prev_product_names = set(df["Product Names"])

    for product_name, price in zip(names, prices):
        if product_name in prev_product_names:
            df.loc[df['Product Names'] == product_name, 'Current Prices'] = price
            df.loc[df['Product Names'] == product_name, 'New to site?'] = "NO"
        else:
            df = pd.concat([df, pd.DataFrame({
                "Product Names": [product_name],
                "New to site?": ["YES"], 
                "Previous Prices": [""],
                "Previous Timestamp": [""],
                "Current Prices": [price],
                "Current Timestamp": [timestamp],
                "Price Difference": ["N/A"]
            })], ignore_index=True)

    df['Price Difference'] = df.apply(calculate_price_difference, axis=1)
    df['Current Timestamp'] = timestamp
    df.to_csv(PRICE_FILE, index=False)
    print(f"Updated prices and product names saved to '{PRICE_FILE}'")

def calculate_price_difference(row):
    """Calculates the difference between previous and current prices."""
    def parse_price(price_str):
        if pd.isna(price_str) or price_str == "":
            return None
        cleaned_price = price_str.replace("From ", "").replace("£", "").replace(",", "").strip()
        try:
            return float(cleaned_price)
        except ValueError:
            return None

    prev_price = parse_price(row["Previous Prices"])
    curr_price = parse_price(row["Current Prices"])
    return curr_price - prev_price if prev_price and curr_price else "N/A"

# Run the scraping script
asyncio.run(scrape_prices())
