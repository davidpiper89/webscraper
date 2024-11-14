from playwright.async_api import async_playwright
import asyncio
import pandas as pd
from datetime import datetime
import os

# File to store price history
PRICE_FILE = 'prices_comparison.csv'

# List of product page URLs to scrape
PRODUCT_PAGES = [
    # "https://www.apply3d.com/asiga",
    # "https://www.apply3d.com/asiga?page=2",
    # "https://www.apply3d.com/bluecast",
    "https://www.apply3d.com/detax",
    # "https://www.apply3d.com/keyprint",
    # "https://www.apply3d.com/loctite",
    # "https://www.apply3d.com/nk-optik",
    # "https://www.apply3d.com/phrozen",
    # "https://www.apply3d.com/phrozen?page=2",
    # "https://www.apply3d.com/saremco"
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
    """Processes individual product pages that have one or two dropdowns for price ranges."""
    for product_page in product_pages:
        print("Navigating to", product_page)
        await page.goto(product_page)
        await close_banner_if_present(page)
        await page.wait_for_load_state("domcontentloaded")

        name_element = await page.query_selector('h1[data-hook="product-title"]')
        product_name = await name_element.text_content() if name_element else "No Name"
        
        dropdown_buttons = await page.query_selector_all('button[data-hook="dropdown-base"]')
        if dropdown_buttons:
            if len(dropdown_buttons) == 1:
                await handle_single_dropdown(page, dropdown_buttons[0], names, product_name, prices, retries=10)
            elif len(dropdown_buttons) >= 2:
                await handle_two_dropdowns(page, dropdown_buttons, names, product_name, prices, retries=10)
                
async def close_banner_if_present(page):
    """Closes a consent banner if present on the page."""
    try:
        await page.wait_for_selector('button[data-hook="consent-banner-apply-button"]', timeout=5000)
        print("button found")
        await page.click('button[data-hook="consent-banner-apply-button"]')
        print("button clicked")
    except:
        print("Banner not found")

async def find_container_id(page, dropdown_button):
    """Find the appropriate container ID on the page by checking a range of IDs."""
    used_ids = set()
    
    # Open the dropdown menu to reveal the container options
    await page.evaluate('(element) => element.click()', dropdown_button)
    await page.wait_for_load_state('load')
    await page.wait_for_timeout(1000)
    
    # Define a range of possible container IDs and check each one
    for i in range(1, 21):
        if i in used_ids:
            continue
        container_id = f"#dropdown-options-container_-{i}"
        # Skip if this container ID was already used
        
        container = await page.query_selector(container_id)
        
        if container:
            print(f"Container found with ID: {container_id}")
            used_ids.add(i) 
            await page.evaluate('(element) => element.click()', dropdown_button)
            await page.wait_for_load_state('load')
            await page.wait_for_timeout(1000)
            return container_id  
    await page.evaluate('(element) => element.click()', dropdown_button)
    await page.wait_for_load_state('load')
    await page.wait_for_timeout(1000)
    print("No appropriate container ID found.")
    return None

async def handle_single_dropdown(page, dropdown_button, names, product_name, prices, retries):
    """Handles interaction with a single dropdown by selecting options based on title."""
    print("Handling single dropdown")

    try:
        # Find the correct container ID
        container_id = await find_container_id(page, dropdown_button)
        await page.evaluate('(element) => element.click()', dropdown_button)
        await page.wait_for_load_state('load')
        await page.wait_for_timeout(1000)
        if container_id:
            container = await page.query_selector(container_id)
            options = await container.query_selector_all('div[data-hook="option"][role="menuitem"]')
            
            for option in options:
                name_element = await option.query_selector('span.sMgpOzd')
                name = await name_element.text_content() if name_element else "Unnamed Option"
                
                # Click on the option by its title
                title = await page.query_selector(f'div[title="{name}"]')
                if title:
                    await page.evaluate('(element) => element.click()', title)
                    await page.wait_for_timeout(1500)
                    await page.wait_for_load_state('load')

                    # Retrieve price for the selected option
                    price_element = await page.query_selector('span[data-hook="formatted-primary-price"]')
                    await page.wait_for_timeout(500)
                    price = await price_element.text_content() if price_element else "No Price"

                    # Append the name and price with product name to lists
                    combined_name = f"{product_name} - Option: {name.strip()}"
                    names.append(combined_name)
                    prices.append(price.strip())
                    print(f"Option: {combined_name} - Price: {price}")
                    
                    # Reopen dropdown for the next option
                    await page.evaluate('(element) => element.click()', dropdown_button)
                    await page.wait_for_timeout(1000)

        else:
            print("Dropdown options container not found for single dropdown.")
            if retries > 0:
                print("Retrying single dropdown...")
                await page.reload()
                await page.wait_for_load_state('load')
                await page.wait_for_timeout(3000)
                dropdown_button = await page.query_selector('button[data-hook="dropdown-base"]')
                if dropdown_button:
                    await handle_single_dropdown(page, dropdown_button, names, product_name, prices, retries - 1)
            else:
                print("Failed to handle single dropdown after retries.")

    except Exception as e:
        print(f"Error handling single dropdown: {e}")

async def scrape_prices_for_dropdown_options(page, dropdown_buttons, first_dropdown_titles, second_dropdown_titles, product_name, names, prices, retries):
    """Handles going through each drop down option and scrape the prices"""
    for first_title in first_dropdown_titles:
        try:

            # Open and select first dropdown option
            await page.evaluate('(element) => element.click()', dropdown_buttons[0])
            await page.wait_for_timeout(1000)
            first_option = await page.query_selector(f'span:text("{first_title}")')
            if not first_option:
                print(f"First option '{first_title}' not found, retrying...")
                await scrape_prices_for_dropdown_options(
                    page, dropdown_buttons, first_dropdown_titles,
                    second_dropdown_titles, product_name, names, prices, retries-1
                )
                return

            await page.evaluate('(element) => element.click()', first_option)
            await page.wait_for_timeout(1000)

            # Loop through second dropdown options
            for second_title in second_dropdown_titles:
                await page.evaluate('(element) => element.click()', dropdown_buttons[1])
                await page.wait_for_timeout(1000)

                second_option = await page.query_selector(f'span:text("{second_title}")')
                if not second_option:
                    print(f"Second option '{second_title}' not found, retrying second dropdown...")
                    continue  # Skip this iteration but don't retry whole function

                await page.evaluate('(element) => element.click()', second_option)
                await page.wait_for_timeout(1000)

                # Extract and store price
                price_element = await page.wait_for_selector('span[data-hook="formatted-primary-price"]', timeout=5000)
                price = await price_element.text_content() if price_element else "No Price"

                combined_name = f"{product_name} - {first_title.strip()} - {second_title.strip()}"
                names.append(combined_name)
                prices.append(price.strip())
                print(f"Combination: {combined_name} - Price: {price}")

        except Exception as e:
            print(f"Error handling dropdowns: {e}")
            await scrape_prices_for_dropdown_options(
                page, dropdown_buttons, first_dropdown_titles,
                second_dropdown_titles, product_name, names, prices, retries-1
            )
            return


async def handle_two_dropdowns(page, dropdown_buttons, names, product_name, prices, retries):
    """Handles interaction with two dropdowns, retrieving names and prices for each combination using titles for selection."""

    # Find the container ID for the first dropdown
    first_dropdown_container_id = await find_container_id(page, dropdown_buttons[0])
    if not first_dropdown_container_id:
        print("First dropdown container not found.")
        return

    # Find the container ID for the second dropdown
    second_dropdown_container_id = await find_container_id(page, dropdown_buttons[1])
    if not second_dropdown_container_id:
        print("Second dropdown container not found.")
        return

    # Gather options titles for first dropdown
    first_dropdown_titles = await get_dropdown_titles(page, dropdown_buttons[0], first_dropdown_container_id)

    # Gather options titles for the second dropdown
    second_dropdown_titles = await get_dropdown_titles(page, dropdown_buttons[1], second_dropdown_container_id)

    # Pass the dynamically obtained dropdown buttons to the scrape function
    await scrape_prices_for_dropdown_options(page, dropdown_buttons, first_dropdown_titles, second_dropdown_titles, product_name, names, prices, retries)

async def get_dropdown_titles(page, dropdown_button, container_id):
    """Returns a list of titles for each option in a dropdown specified by the container ID."""
    # Open the dropdown to retrieve titles
    await page.evaluate('(element) => element.click()', dropdown_button)
    await page.wait_for_timeout(1000)
    container = await page.query_selector(container_id)

    # Extract titles or return an empty list if container not found
    options_elements = await container.query_selector_all('div[data-hook="option"][role="menuitem"]') if container else []
    titles = []

    for element in options_elements:
        title_element = await element.query_selector('span.sMgpOzd')
        title = await title_element.text_content() if title_element else "Unnamed Option"
        titles.append(title)
        print(f"Option title added: {title}")

    # Close the dropdown after gathering titles
    await page.evaluate('(element) => element.click()', dropdown_button)
    return titles

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
