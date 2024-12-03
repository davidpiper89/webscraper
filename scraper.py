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
    "https://www.apply3d.com/asiga?page=2",
    "https://www.apply3d.com/bluecast",
    "https://www.apply3d.com/detax",
    "https://www.apply3d.com/keyprint",
    "https://www.apply3d.com/loctite",
    "https://www.apply3d.com/nk-optik",
    "https://www.apply3d.com/phrozen",
    "https://www.apply3d.com/phrozen?page=2",
    "https://www.apply3d.com/saremco"
]

async def login(page, email, password, max_retries=5):
    """Log into the site with retries if the login button is not found."""
    for attempt in range(1, max_retries + 1):
        try:
            print(f"Attempt {attempt} to log in...")

            # Navigate to the login page
            await page.goto("https://www.apply3d.com/")
            await close_banner_if_present(page)
            await page.wait_for_load_state("domcontentloaded")

            # Wait for the login button
            await page.wait_for_selector('button:has(span:text("Login"))', timeout=2500)
            await page.click('button:has(span:text("Login"))')

            # Fill in the login form
            await page.fill('input[type="email"]', email)
            await page.fill('input[type="password"]', password)

            # Click the log-in button
            await page.click('button:has(span.l7_2fn:text("Log In"))')

            print("Logged in successfully.")
            return

        except Exception as e:
            print(f"Login attempt {attempt} failed: {e}")
            if attempt < max_retries:
                print("Retrying...")
                await page.reload()
                await page.wait_for_load_state("domcontentloaded")
            else:
                print("Max login attempts reached. Unable to log in.")
                raise

async def extract_product_info(product):
    """Extracts the name, price or status, and ribbon information for an individual product."""
    # Extract product name
    name_element = await product.query_selector('p[data-hook="product-item-name"]')
    product_name = await name_element.text_content() if name_element else "No Name"

    # Check if the product is out of stock
    out_of_stock_element = await product.query_selector('span[data-hook="product-item-out-of-stock"]')

    # Extract ribbon information
    ribbon = await product.query_selector('div[data-hook="RibbonDataHook.RibbonOnImage"]')
    ribbon_text = await ribbon.text_content() if ribbon else "No Ribbon"

    if out_of_stock_element:
        return f"{product_name} - Out of stock", await out_of_stock_element.text_content(), None, ribbon_text

    # Extract price information
    price_element = await product.query_selector('span[data-hook="product-item-price-to-pay"]')
    if price_element:
        return product_name, await price_element.text_content(), None, ribbon_text

    # Extract "from price" and link if available
    from_price_element = await product.query_selector('span[data-hook="price-range-from"]')
    if from_price_element:
        product_link = await product.query_selector('a[data-hook="product-item-product-details-link"]')
        link = await product_link.get_attribute('href') if product_link else None
        return product_name, None, link, ribbon_text

    # Default return for cases with no price or "from price"
    return product_name, None, None, ribbon_text

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
        all_product_names, all_prices, all_ribbons, all_product_from_price_pages = [], [], [], []

        # Scrape each product page
        for url in PRODUCT_PAGES:
            print(f"Scraping page: {url}")
            product_list = await scrape_page(page, url)
            for product in product_list:
                name, price, link, ribbon = await extract_product_info(product)
                if price:
                    all_product_names.append(name.strip())
                    all_prices.append(price.strip())
                    all_ribbons.append(ribbon.strip())
                elif link:
                    all_product_from_price_pages.append(link.strip())

        
        print("Number of products with price ranges:", len(all_product_from_price_pages))   

        # Process individual product pages for "from" price ranges
        await process_price_ranges(page, all_product_from_price_pages, all_product_names, all_prices, all_ribbons)

        # Save the data, including ribbons
        await save_price_data(all_product_names, all_prices, all_ribbons)


        await browser.close()

async def process_price_ranges(page, product_pages, names, prices, ribbons):
    """Processes individual product pages that have one or two dropdowns for price ranges."""
    for product_page in product_pages:
        print("Navigating to", product_page)
        await page.goto(product_page)
        await close_banner_if_present(page)
        await page.wait_for_load_state("domcontentloaded")

        name_element = await page.query_selector('h1[data-hook="product-title"]')
        product_name = await name_element.text_content() if name_element else "No Name"
        dropdown_buttons = await page.query_selector_all('button[data-hook="dropdown-base"]')
        radio_buttons = await page.query_selector_all('div[data-hook="color-picker-item"]')

        if radio_buttons and not dropdown_buttons:
            if len(radio_buttons) > 1:
                await handle_radio_buttons(page, names, radio_buttons, product_name, prices, ribbons, retries=10)
            if len(radio_buttons) == 1:
                await handle_radio_button(page, names, radio_buttons, product_name, prices, ribbons, retries=10)
        if dropdown_buttons and not radio_buttons:
            if len(dropdown_buttons) == 1:
                await handle_single_dropdown(page, dropdown_buttons[0], names, product_name, prices, ribbons, retries=10)
            elif len(dropdown_buttons) >= 2:
                await handle_two_dropdowns(page, dropdown_buttons, names, product_name, prices, ribbons, retries=10)
        if dropdown_buttons and radio_buttons:
            if len(dropdown_buttons) == 1 and len(radio_buttons) == 2:
                await handle_two_radios_and_dropdown(page, dropdown_buttons, radio_buttons, names, product_name, prices, ribbons, retries=10)
            if len(dropdown_buttons) == 1 and len(radio_buttons) == 1:
                await handle_one_radios_and_dropdown(page, dropdown_buttons, radio_buttons, names, product_name, prices, ribbons, retries=10)
            
async def close_banner_if_present(page):
    """Closes a consent banner if present on the page."""
    try:
        await page.wait_for_selector('button[data-hook="consent-banner-apply-button"]', timeout=5000)
        print("button found")
        await page.click('button[data-hook="consent-banner-apply-button"]')
        print("button clicked")
    except:
        print("Banner not found")

async def handle_radio_buttons(page, names, radio_buttons, product_name, prices, ribbons, retries):
    """Handles interaction with radio buttons on a product page."""
    print("Handling radio buttons")

    # Retry limit check
    if retries <= 0:
        print("Max retries reached for handling radio buttons.")
        return

    try:
        for radio_button in radio_buttons:
            # Locate the radio input element within the radio button container
            selector = await radio_button.query_selector('input[type="radio"]')

            # Click the radio input
            await page.evaluate('(element) => element.click()', selector)
            await page.wait_for_timeout(1500)

            # Extract and store price
            price_element = await page.query_selector('span[data-hook="formatted-primary-price"]')
            price = await price_element.text_content() if price_element else "No Price"

            # Retrieve option name from aria-label
            name = await selector.get_attribute('aria-label') if selector else "No Label"
            combined_name = f"{product_name} - Option: {name.strip()}"
            
            # Append combined name and price to lists
            names.append(combined_name)
            prices.append(price.strip())
            ribbons.append("No Ribbon")
            print(f"Option: {combined_name} - Price: {price}")

    except Exception as e:
        print(f"Error handling radio buttons: {e}")
        await handle_radio_buttons(page, names, radio_buttons, product_name, prices, ribbons, retries - 1)

async def handle_radio_button(page, names, radio_buttons, product_name, prices, ribbons, retries):
    """Handles interaction with radio buttons on a product page."""
    print("Handling radio button")

    # Retry limit check
    if retries <= 0:
        print("Max retries reached for handling radio buttons.")
        return

    try:
        # Extract and store price
        price_element = await page.query_selector('span[data-hook="formatted-primary-price"]')
        price = await price_element.text_content() if price_element else "No Price"

        # Retrieve option name from aria-label
        product_colour_element = await page.query_selector('div[data-hook="product-colors-title"]')
        product_color = await product_colour_element.text_content() if product_colour_element else "Unnamed Option"
        print(f"Selected Radio Button: {product_color}")
        combined_name = f"{product_name} - {product_color.strip()}"

        # Append combined name and price to lists
        names.append(combined_name)
        prices.append(price.strip())
        ribbons.append("No Ribbon")
        print(f"Option: {combined_name} - Price: {price}")

    except Exception as e:
        print(f"Error handling radio buttons: {e}")
        await handle_radio_buttons(page, names, radio_buttons, product_name, prices, ribbons, retries - 1)

async def handle_one_radios_and_dropdown(page, dropdown_buttons, radio_buttons, names, product_name, prices, ribbons, retries):
    """Handles interaction with one radio buttons and one dropdown on a product page."""
    print("Handling one radio buttons and one dropdown")

    # Retry limit check
    if retries <= 0:
        print("Max retries reached for handling two radios and dropdown.")
        return
    
    # Open and iterate over dropdown options
    dropdown_button = dropdown_buttons[0]
    container_id = await find_container_id(page, dropdown_button)
    container_open = False

    try:
            product_colour_element = await page.query_selector('div#product-colors-title-1')
            product_color = await product_colour_element.text_content() if product_colour_element else "Unnamed Option"

            print(f"Selected Radio Button: {product_color}")

            if (container_open == False):
                # Open and iterate over dropdown options
                await page.evaluate('(element) => element.click()', dropdown_button)
                container_open = not container_open
                await page.wait_for_timeout(1000)

            if container_id:
                container = await page.query_selector(container_id)
                options = await container.query_selector_all('div[data-hook="option"][role="menuitem"]')

                for option in options:
                    # Extract dropdown option name
                    option_name_element = await option.query_selector('span.sMgpOzd')
                    option_name = await option_name_element.text_content() if option_name_element else "Unnamed Option"

                    #Click on the option by its title
                    title = await page.query_selector(f'div[title="{option_name}"]')

                    # Click dropdown option
                    if title:
                        await page.evaluate('(element) => element.click()', title)
                        container_open = not container_open
                        await page.wait_for_timeout(1500)
                        await page.wait_for_load_state('load')

                        # Extract price for the selected radio and dropdown combination
                        price_element = await page.query_selector('span[data-hook="formatted-primary-price"]')
                        price = await price_element.text_content() if price_element else "No Price"

                        # Combine product name, radio label, and dropdown option name
                        combined_name = f"{product_name} - {product_color} - {option_name.strip()}"
                        names.append(combined_name)
                        prices.append(price.strip())
                        ribbons.append("No Ribbon")

                        print(f"Option: {combined_name} - Price: {price}")

                        # Reopen the dropdown for the next option
                        await page.evaluate('(element) => element.click()', dropdown_button)
                        container_open = not container_open
                        await page.wait_for_timeout(1000)
            else:
                print("Dropdown options container not found, retrying...")
                await handle_two_radios_and_dropdown(page, dropdown_buttons, radio_buttons, names, product_name, prices, ribbons, retries - 1)

    except Exception as e:
        print(f"Error handling two radios and dropdown: {e}")
        await handle_two_radios_and_dropdown(page, dropdown_buttons, radio_buttons, names, product_name, prices, ribbons, retries - 1)

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

async def handle_single_dropdown(page, dropdown_button, names, product_name, prices, ribbons, retries):
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
                    ribbons.append("No Ribbon")
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
                    await handle_single_dropdown(page, dropdown_button, names, product_name, prices, ribbons, retries - 1)
            else:
                print("Failed to handle single dropdown after retries.")

    except Exception as e:
        print(f"Error handling single dropdown: {e}")

async def scrape_prices_for_dropdown_options(page, dropdown_buttons, first_dropdown_titles, second_dropdown_titles, product_name, names, prices, ribbons, retries):
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
                    continue  

                await page.evaluate('(element) => element.click()', second_option)
                await page.wait_for_timeout(1000)

                # Extract and store price
                price_element = await page.wait_for_selector('span[data-hook="formatted-primary-price"]', timeout=5000)
                price = await price_element.text_content() if price_element else "No Price"

                combined_name = f"{product_name} - {first_title.strip()} - {second_title.strip()}"
                names.append(combined_name)
                prices.append(price.strip())
                ribbons.append("No Ribbon")
                print(f"Combination: {combined_name} - Price: {price}")

        except Exception as e:
            print(f"Error handling dropdowns: {e}")
            await scrape_prices_for_dropdown_options(
                page, dropdown_buttons, first_dropdown_titles, second_dropdown_titles, product_name, names, prices, ribbons, retries-1
            )
            return

async def handle_two_dropdowns(page, dropdown_buttons, names, product_name, prices, ribbons, retries):
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
    await scrape_prices_for_dropdown_options(page, dropdown_buttons, first_dropdown_titles, second_dropdown_titles, product_name, names, prices, ribbons, retries)

async def handle_two_radios_and_dropdown(page, dropdown_buttons, radio_buttons, names, product_name, prices, ribbons, retries):
    """Handles interaction with two radio buttons and one dropdown on a product page."""
    print("Handling two radio buttons and one dropdown")

    # Retry limit check
    if retries <= 0:
        print("Max retries reached for handling two radios and dropdown.")
        return
    
    # Open and iterate over dropdown options
    dropdown_button = dropdown_buttons[0]
    container_id = await find_container_id(page, dropdown_button)
    container_open = False

    try:
        # Iterate over each radio button option
        for radio_button in radio_buttons:
            # Click the radio button
            selector = await radio_button.query_selector('input[type="radio"]')
            await page.wait_for_load_state("domcontentloaded")

            await page.evaluate('(element) => element.click()', selector)
            await page.wait_for_timeout(1000)

            # Retrieve option name from aria-label
            radio_label = await selector.get_attribute('aria-label') 
            print(f"Selected Radio Button: {radio_label}")

            if (container_open == False):
                # Open and iterate over dropdown options
                await page.evaluate('(element) => element.click()', dropdown_button)
                container_open = not container_open
                await page.wait_for_timeout(1000)

            if container_id:
                container = await page.query_selector(container_id)
                options = await container.query_selector_all('div[data-hook="option"][role="menuitem"]')

                for option in options:
                    # Extract dropdown option name
                    option_name_element = await option.query_selector('span.sMgpOzd')
                    option_name = await option_name_element.text_content() if option_name_element else "Unnamed Option"

                    #Click on the option by its title
                    title = await page.query_selector(f'div[title="{option_name}"]')

                    # Click dropdown option
                    if title:
                        await page.evaluate('(element) => element.click()', title)
                        container_open = not container_open
                        await page.wait_for_timeout(1500)
                        await page.wait_for_load_state('load')

                        # Extract price for the selected radio and dropdown combination
                        price_element = await page.query_selector('span[data-hook="formatted-primary-price"]')
                        price = await price_element.text_content() if price_element else "No Price"

                        # Combine product name, radio label, and dropdown option name
                        combined_name = f"{product_name} - {radio_label} - {option_name.strip()}"
                        names.append(combined_name)
                        prices.append(price.strip())
                        ribbons.append("No Ribbon")

                        print(f"Option: {combined_name} - Price: {price}")

                        # Reopen the dropdown for the next option
                        await page.evaluate('(element) => element.click()', dropdown_button)
                        container_open = not container_open
                        await page.wait_for_timeout(1000)
            else:
                print("Dropdown options container not found, retrying...")
                await handle_two_radios_and_dropdown(page, dropdown_buttons, radio_buttons, names, product_name, prices, ribbons, retries - 1)

    except Exception as e:
        print(f"Error handling two radios and dropdown: {e}")
        await handle_two_radios_and_dropdown(page, dropdown_buttons, radio_buttons, names, product_name, prices, ribbons, retries - 1)

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

    # Close the dropdown after gathering titles
    await page.evaluate('(element) => element.click()', dropdown_button)
    return titles

async def save_price_data(names, prices, ribbons):
    """Saves or updates price data in a CSV file, including ribbon information."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    if not os.path.exists(PRICE_FILE):
        create_new_price_file(names, prices, ribbons, timestamp)
    else:
        update_existing_price_file(names, prices, ribbons, timestamp)

def create_new_price_file(names, prices, ribbons, timestamp):
    """Creates a new price file with the initial data, including ribbons."""
    df = pd.DataFrame({
        "Product Names": names,
        "New to site?": ["YES"] * len(names),
        "Previous Prices": ["" for _ in names],
        "Previous Timestamp": ["" for _ in names],
        "Current Prices": prices,
        "Current Timestamp": [timestamp] * len(names),
        "Price Difference": ["N/A"] * len(names),
        "Ribbon": ribbons
    })
    df.to_csv(PRICE_FILE, index=False)
    print(f"Prices, product names, and ribbons saved to '{PRICE_FILE}'")

def update_existing_price_file(names, prices, ribbons, timestamp):
    """Updates the existing price file by comparing and adding new data, including ribbons."""
    df = pd.read_csv(PRICE_FILE)
    df['Previous Prices'], df['Previous Timestamp'] = df['Current Prices'], df['Current Timestamp']
    prev_product_names = set(df["Product Names"])

    for product_name, price, ribbon in zip(names, prices, ribbons):
        if product_name in prev_product_names:
            df.loc[df['Product Names'] == product_name, 'Current Prices'] = price
            df.loc[df['Product Names'] == product_name, 'Ribbon'] = ribbon
            df.loc[df['Product Names'] == product_name, 'New to site?'] = "NO"
        else:
            df = pd.concat([df, pd.DataFrame({
                "Product Names": [product_name],
                "New to site?": ["YES"], 
                "Previous Prices": [""],
                "Previous Timestamp": [""],
                "Current Prices": [price],
                "Current Timestamp": [timestamp],
                "Price Difference": ["N/A"],
                "Ribbon": [ribbon]
            })], ignore_index=True)

    df['Price Difference'] = df.apply(calculate_price_difference, axis=1)
    df['Current Timestamp'] = timestamp
    df.to_csv(PRICE_FILE, index=False)
    print(f"Updated prices, product names, and ribbons saved to '{PRICE_FILE}'")

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
