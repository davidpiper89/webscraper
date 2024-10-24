from playwright.async_api import async_playwright
import asyncio
import pandas as pd
import os
from datetime import datetime

# File to store price history
PRICE_FILE = 'prices_comparison.csv'

async def scrape_prices():
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()
        await page.goto("https://www.apply3d.com/")

        # Wait for the page to load
        await page.wait_for_load_state("networkidle")
        print("Waiting for login button...")

        # Click the login button
        await page.click('button:has(span:text("Login"))')
        print("login clicked...")

        # Await login modal and login
        await page.wait_for_selector('input[type="email"]')
        print("email input found")
        await page.fill('input[type="email"]', 'testy888777@hotmail.com')
        print("Email filled in successfully.")
        print("Waiting for password input...")
        await page.wait_for_selector('input[type="password"]')
        print("Filling in password...")
        await page.fill('input[type="password"]', 'Breadboard99')
        print("Password filled in successfully.")
        await page.click('button:has(span.l7_2fn:text("Log In"))')
        print("logged in")

        # Extract product names and prices from all pages
        product_names = []
        prices = []
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Navigate to the Asiga page
        await page.wait_for_load_state("networkidle")
        print("Navigating to the Asiga page...")
        await page.goto("https://www.apply3d.com/asiga")
        print("Navigated to the Asiga page.")
        await page.wait_for_load_state("networkidle")
        await page.wait_for_timeout(5000)

        # Scrape Asiga products
        asiga_products = await page.query_selector_all('li[data-hook="product-list-grid-item"]')

        for product in asiga_products:
            # Extract product name
            name_element = await product.query_selector('p[data-hook="product-item-name"]')
            product_name = await name_element.text_content() if name_element else "No Name"
            
            # Try to find the standard price
            price_element = await product.query_selector('span[data-hook="product-item-price-to-pay"]')
            
            # If standard price not found, check for the "From" price range
            if not price_element:
                price_element = await product.query_selector('span[data-hook="price-range-from"]')

            # Extract price if found
            if price_element:
                price_value = await price_element.text_content()
                if price_value :
                    # Append product name and price to the lists
                    product_names.append(product_name.strip())
                    prices.append(price_value.strip())
              

        await page.goto("https://www.apply3d.com/asiga?page=2")
        print("Navigated to the Asiga page 2.")   
        await page.wait_for_load_state("networkidle")    

        # Scrape Asiga products page 2
        asiga_product_names = await page.query_selector_all('p.sNPC28E')
        asiga_price_elements = await page.query_selector_all('span.cfpn1d')

        for name, price in zip(asiga_product_names, asiga_price_elements):
            product_name = await name.text_content()
            price_value = await price.get_attribute('data-wix-price')

            if price_value:
                product_names.append(product_name.strip())  
                prices.append(price_value.strip())   
        

        # Navigate to the BlueCast page
        print("Navigating to the BlueCast page...")
        await page.goto("https://www.apply3d.com/bluecast")
        print("Navigated to the BlueCast page.")

        # Scrape BlueCast products
        bluecast_product_names = await page.query_selector_all('p.sNPC28E')
        bluecast_price_elements = await page.query_selector_all('span.cfpn1d')

        for name, price in zip(bluecast_product_names, bluecast_price_elements):
            product_name = await name.text_content()
            price_value = await price.get_attribute('data-wix-price')

            if price_value:
                product_names.append(product_name.strip())  
                prices.append(price_value.strip())  

        # Check if the price file exists, if not, create it with a header
        if not os.path.exists(PRICE_FILE):
            df = pd.DataFrame({
                "Product Names": product_names,
                "New to site?": "YES",
                "Previous Prices": "",
                "Previous Timestamp": "",
                "Current Prices": prices,
                "Current Timestamp": [timestamp] * len(prices),
                "Price Difference": "N/A"  
            })
            df.to_csv(PRICE_FILE, index=False)
            print(f"Prices and product names saved to '{PRICE_FILE}'")
        else:
            # Load existing prices and compare
            df = pd.read_csv(PRICE_FILE)

            # Move current prices to previous prices
            df['Previous Prices'] = df['Current Prices']
            df['Previous Timestamp'] = df['Current Timestamp']

            # Create a set of current and previous products
            prev_product_names = set(df["Product Names"])

            # Identify missing products
            missing_products = prev_product_names - set(product_names)

            for missing_product in missing_products:
                missing_index = df[df["Product Names"] == missing_product].index[0]
                # Update the current price to "(not on site)"
                df.loc[missing_index, "Current Prices"] = "(not on site)"
                df.loc[missing_index, "Current Timestamp"] = timestamp

            # Update current prices with the new scrape for existing products
            for i, product in enumerate(product_names):
                if product in prev_product_names:
                    df.loc[df['Product Names'] == product, 'Current Prices'] = prices[i]
                    df.loc[df['Product Names'] == product, 'New to site?'] = "NO"  
                else:
                    # If the product is new, append it to the DataFrame
                    new_row = pd.DataFrame({
                        "Product Names": [product],
                        "New to site?": ["YES"], 
                        "Previous Prices": [""],
                        "Previous Timestamp": [""],
                        "Current Prices": [prices[i]],
                        "Current Timestamp": [timestamp],
                        "Price Difference": ["N/A"] 
                    })
                    df = pd.concat([df, new_row], ignore_index=True)

            # Calculate price difference for each product
            def calculate_price_difference(row):
                def extract_price(price_string):
                    if pd.isna(price_string) or price_string == "":
                        return None
                    # Remove "From" and currency symbols, and convert to float
                    cleaned_price = price_string.replace("From ", "").replace("£", "").replace(",", "").strip()
                    try:
                        return float(cleaned_price)
                    except ValueError:
                        return None

                prev_price = extract_price(row["Previous Prices"])
                curr_price = extract_price(row["Current Prices"])

                if prev_price is not None and curr_price is not None:
                    return curr_price - prev_price
                else:
                    return "N/A"

            df['Price Difference'] = df.apply(calculate_price_difference, axis=1)

            # Update timestamps for all products
            df['Current Timestamp'] = [timestamp] * len(df)

            # Save the updated CSV
            df.to_csv(PRICE_FILE, index=False)
            print(f"Updated prices and product names saved to '{PRICE_FILE}'")
            await browser.close()

if __name__ == "__main__":
    asyncio.run(scrape_prices())