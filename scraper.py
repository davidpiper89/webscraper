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

        # Navigate to the Asiga page
        await page.wait_for_load_state("networkidle")
        print("Navigating to the Asiga page...")
        await page.goto("https://www.apply3d.com/asiga")
        print("Navigated to the Asiga page.")

        # Extract product names and prices from the Asiga page
        new_product_names = []
        new_prices = []
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")  # Current timestamp

        # Scrape Asiga products
        asiga_product_names = await page.query_selector_all('p.sNPC28E')
        asiga_price_elements = await page.query_selector_all('span.cfpn1d')

        for name, price in zip(asiga_product_names, asiga_price_elements):
            product_name = await name.text_content() 
            price_value = await price.get_attribute('data-wix-price') 

            if price_value:
                new_product_names.append(product_name.strip())  # Collect names
                new_prices.append(price_value.strip())  # Collect prices

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
                new_product_names.append(product_name.strip())  # Collect names
                new_prices.append(price_value.strip())  # Collect prices

        # Check if the price file exists, if not, create it with a header
        if not os.path.exists(PRICE_FILE):
            df = pd.DataFrame({
                "Product Names": new_product_names,
                "Previous Prices": new_prices,
                "Previous Timestamp": [timestamp] * len(new_prices),  
                "Current Prices": new_prices,
                "Current Timestamp": [timestamp] * len(new_prices)  
            })
            df.to_csv(PRICE_FILE, index=False)
            print(f"Prices and product names saved to '{PRICE_FILE}'")
        else:
            # Load existing prices and compare
            df = pd.read_csv(PRICE_FILE)

            # Update existing rows based on the number of new products
            num_existing = min(len(df), len(new_product_names))
            df.loc[:num_existing - 1, 'Product Names'] = new_product_names[:num_existing]
            df.loc[:num_existing - 1, 'Previous Prices'] = df['Current Prices'][:num_existing]
            df.loc[:num_existing - 1, 'Previous Timestamp'] = df['Current Timestamp'][:num_existing]
            df.loc[:num_existing - 1, 'Current Prices'] = new_prices[:num_existing]
            df.loc[:num_existing - 1, 'Current Timestamp'] = [timestamp] * num_existing

            # Handle any new products if length changes
            if len(new_product_names) > len(df):
                extra_rows = pd.DataFrame({
                    "Product Names": new_product_names[len(df):],
                    "Previous Prices": [""] * (len(new_product_names) - len(df)),
                    "Previous Timestamp": ["" for _ in range(len(new_product_names) - len(df))],
                    "Current Prices": new_prices[len(df):],
                    "Current Timestamp": [timestamp] * (len(new_product_names) - len(df))  
                })
                df = pd.concat([df, extra_rows], ignore_index=True)

            # Save the updated CSV
            df.to_csv(PRICE_FILE, index=False)
            print(f"Updated prices and product names saved to '{PRICE_FILE}'")

        await browser.close()

if __name__ == "__main__":
    asyncio.run(scrape_prices())
