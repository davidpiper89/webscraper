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

        # Product pages with from prices
        product_from_price_pages = []

        # Extract product names and prices from all pages
        product_names = []
        prices = []
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Navigate to the Asiga page
        await page.wait_for_load_state("networkidle")
        print("Navigating to the Asiga page...")
        await page.goto("https://www.apply3d.com/asiga")
        print("Navigated to the Asiga page.")
        await page.wait_for_load_state("domcontentloaded")

        # Scrape Asiga products with no from price
        asiga_products = await page.query_selector_all('li[data-hook="product-list-grid-item"]')

        for product in asiga_products:
            # Extract product name
            name_element = await product.query_selector('p[data-hook="product-item-name"]')
            product_name = await name_element.text_content() if name_element else "No Name"

            # Initialize price variables
            price_value = None

            # Check if the product is out of stock
            out_of_stock_element = await product.query_selector('span[data-hook="product-item-out-of-stock"]')
            if out_of_stock_element:
                # Out of stock: add "Out of stock" as price
                price_value = await out_of_stock_element.text_content()
                product_name += " - Out of stock"
            else:
                # Try to get the standard price if in stock
                price_element = await product.query_selector('span[data-hook="product-item-price-to-pay"]')
                
                if price_element:
                    # Found standard price
                    price_value = await price_element.text_content()
                else:
                    # No standard price found, check for "From" price
                    from_price_element = await product.query_selector('span[data-hook="price-range-from"]')
                    
                    if from_price_element:
                        # From price found, add product link to `product_from_price_pages`
                        anchor = await product.query_selector('a[data-hook="product-item-product-details-link"]')
                        product_link = await anchor.get_attribute('href') if anchor else None
                        if product_link:
                            product_from_price_pages.append(product_link.strip())

            # Append product name and price if we have a price value
            if price_value:
                product_names.append(product_name.strip())
                prices.append(price_value.strip())


        # # Repeat the process for Asiga page 2
        # print("Navigating to Asiga page 2...")
        # await page.goto("https://www.apply3d.com/asiga?page=2")
        # print("Navigated to Asiga page 2.")
        # await page.wait_for_load_state("domcontentloaded") 

        # # Scrape Asiga products on page 2
        # asiga_page2_products = await page.query_selector_all('li[data-hook="product-list-grid-item"]')

        # for product in asiga_page2_products:
        #     # Extract product name
        #     name_element = await product.query_selector('p[data-hook="product-item-name"]')
        #     product_name = await name_element.text_content() if name_element else "No Name"

        #     # Initialize price variables
        #     price_value = None

        #     # Check if the product is out of stock
        #     out_of_stock_element = await product.query_selector('span[data-hook="product-item-out-of-stock"]')
        #     if out_of_stock_element:
        #         # Out of stock: add "Out of stock" as price
        #         price_value = await out_of_stock_element.text_content()
        #         product_name += " - Out of stock"
        #     else:
        #         # Try to get the standard price if in stock
        #         price_element = await product.query_selector('span[data-hook="product-item-price-to-pay"]')
                
        #         if price_element:
        #             # Found standard price
        #             price_value = await price_element.text_content()
        #         else:
        #             # No standard price found, check for "From" price
        #             from_price_element = await product.query_selector('span[data-hook="price-range-from"]')
                    
        #             if from_price_element:
        #                 # From price found, add product link to `product_from_price_pages`
        #                 price_value = await from_price_element.text_content()
        #                 anchor = await product.query_selector('a[data-hook="product-item-container"]')
        #                 product_link = await anchor.get_attribute('href') if anchor else None
                        
        #                 if product_link:
        #                     product_from_price_pages.append(product_link.strip())

        #     # Append product name and price if we have a price value
        #     if price_value:
        #         product_names.append(product_name.strip())
        #         prices.append(price_value.strip())


        # # Navigate to the BlueCast page
        # print("Navigating to the BlueCast page...")
        # await page.goto("https://www.apply3d.com/bluecast")
        # print("Navigated to the BlueCast page.")
        # await page.wait_for_load_state("domcontentloaded")  

        # # Scrape BlueCast products
        # bluecast_products = await page.query_selector_all('li[data-hook="product-list-grid-item"]')

        # for product in bluecast_products:
        #     # Extract product name
        #     name_element = await product.query_selector('p[data-hook="product-item-name"]')
        #     product_name = await name_element.text_content() if name_element else "No Name"

        #     # Check if the product is out of stock
        #     out_of_stock_element = await product.query_selector('span[data-hook="product-item-out-of-stock"]')
        #     if out_of_stock_element:
        #         # If the product is out of stock, use the text "Out of stock" instead of a price
        #         price_value = await out_of_stock_element.text_content()
        #     else:
        #         # If in stock, try to get the standard price
        #         price_element = await product.query_selector('span[data-hook="product-item-price-to-pay"]')
                
        #         # If standard price not found, check for the "From" price range
        #         if not price_element:
        #             price_element = await product.query_selector('span[data-hook="price-range-from"]')
                
        #         # Extract price if found
        #         price_value = await price_element.text_content() if price_element else None

        #     # Append product name and price (or "Out of stock" text) to the lists
        #     if price_value:
        #         product_names.append(product_name.strip())
        #         prices.append(price_value.strip())

        # # Navigate to the Detax page
        # print("Navigating to the Detax page...")
        # await page.goto("https://www.apply3d.com/detax")
        # print("Navigated to the Detax page.")
        # await page.wait_for_load_state("domcontentloaded")

        # # Scrape Detax products
        # detax_products = await page.query_selector_all('li[data-hook="product-list-grid-item"]')

        # for product in detax_products:
        #     # Extract product name
        #     name_element = await product.query_selector('p[data-hook="product-item-name"]')
        #     product_name = await name_element.text_content() if name_element else "No Name"

        #     # Check if the product is out of stock
        #     out_of_stock_element = await product.query_selector('span[data-hook="product-item-out-of-stock"]')
        #     if out_of_stock_element:
        #         # If the product is out of stock, use the text "Out of stock" instead of a price
        #         price_value = await out_of_stock_element.text_content()
        #     else:
        #         # If in stock, try to get the standard price
        #         price_element = await product.query_selector('span[data-hook="product-item-price-to-pay"]')
                
        #         # If standard price not found, check for the "From" price range
        #         if not price_element:
        #             price_element = await product.query_selector('span[data-hook="price-range-from"]')
                
        #         # Extract price if found
        #         price_value = await price_element.text_content() if price_element else None

        #     # Append product name and price (or "Out of stock" text) to the lists
        #     if price_value:
        #         product_names.append(product_name.strip())
        #         prices.append(price_value.strip())

        # # Navigate to the Keyprint page
        # print("Navigating to the Keyprint page...")
        # await page.goto("https://www.apply3d.com/keyprint")
        # print("Navigated to the Keyprint page.")
        # await page.wait_for_load_state("domcontentloaded")   
        
        # # Scrape Keyprint products
        # keyprint_products = await page.query_selector_all('li[data-hook="product-list-grid-item"]')

        # for product in keyprint_products:
        #     # Extract product name
        #     name_element = await product.query_selector('p[data-hook="product-item-name"]')
        #     product_name = await name_element.text_content() if name_element else "No Name"

        #     # Check if the product is out of stock
        #     out_of_stock_element = await product.query_selector('span[data-hook="product-item-out-of-stock"]')
        #     if out_of_stock_element:
        #         # If the product is out of stock, use the text "Out of stock" instead of a price
        #         price_value = await out_of_stock_element.text_content()
        #     else:
        #         # If in stock, try to get the standard price
        #         price_element = await product.query_selector('span[data-hook="product-item-price-to-pay"]')
                
        #         # If standard price not found, check for the "From" price range
        #         if not price_element:
        #             price_element = await product.query_selector('span[data-hook="price-range-from"]')
                
        #         # Extract price if found
        #         price_value = await price_element.text_content() if price_element else None

        #     # Append product name and price (or "Out of stock" text) to the lists
        #     if price_value:
        #         product_names.append(product_name.strip())
        #         prices.append(price_value.strip())

        # # Navigate to the Loctite page
        # print("Navigating to the Loctite page...")
        # await page.goto("https://www.apply3d.com/loctite")
        # print("Navigated to the Loctite page.")
        # await page.wait_for_load_state("domcontentloaded") 
        
        # # Scrape Loctite products
        # loctite_products = await page.query_selector_all('li[data-hook="product-list-grid-item"]')

        # for product in loctite_products:
        #     # Extract product name
        #     name_element = await product.query_selector('p[data-hook="product-item-name"]')
        #     product_name = await name_element.text_content() if name_element else "No Name"

        #     price_element = await product.query_selector('span[data-hook="product-item-price-to-pay"]')

        #     # If standard price not found, check for the "From" price range
        #     if not price_element:
        #         price_element = await product.query_selector('span[data-hook="price-range-from"]')

        #      # Extract price if found
        #     if price_element:
        #         price_value = await price_element.text_content()
        #         if price_value :
        #             # Append product name and price to the lists
        #             product_names.append(product_name.strip())
        #             prices.append(price_value.strip())
 
        # # Navigate to the NKOptik page
        # print("Navigating to the NKOptik page...")
        # await page.goto("https://www.apply3d.com/nk-optik")
        # print("Navigated to the NKOptik page.")
        # await page.wait_for_load_state("domcontentloaded")  
        
        # # Scrape NKOptik products
        # nkoptik_products = await page.query_selector_all('li[data-hook="product-list-grid-item"]')

        # for product in nkoptik_products:
        #     # Extract product name
        #     name_element = await product.query_selector('p[data-hook="product-item-name"]')
        #     product_name = await name_element.text_content() if name_element else "No Name"

        #     # Check if the product is out of stock
        #     out_of_stock_element = await product.query_selector('span[data-hook="product-item-out-of-stock"]')
        #     if out_of_stock_element:
        #         # If the product is out of stock, use the text "Out of stock" instead of a price
        #         price_value = await out_of_stock_element.text_content()
        #     else:
        #         # If in stock, try to get the standard price
        #         price_element = await product.query_selector('span[data-hook="product-item-price-to-pay"]')
                
        #         # If standard price not found, check for the "From" price range
        #         if not price_element:
        #             price_element = await product.query_selector('span[data-hook="price-range-from"]')
                
        #         # Extract price if found
        #         price_value = await price_element.text_content() if price_element else None

        #     # Append product name and price (or "Out of stock" text) to the lists
        #     if price_value:
        #         product_names.append(product_name.strip())
        #         prices.append(price_value.strip())

        # # Navigate to the Phrozen page
        # print("Navigating to the Phrozen page...")
        # await page.goto("https://www.apply3d.com/phrozen")
        # print("Navigated to the Phrozen page.")
        # await page.wait_for_load_state("networkidle")    
        
        # # Scrape Phrozen products
        # phrozen_products = await page.query_selector_all('li[data-hook="product-list-grid-item"]')

        # for product in phrozen_products:
        #     # Extract product name
        #     name_element = await product.query_selector('p[data-hook="product-item-name"]')
        #     product_name = await name_element.text_content() if name_element else "No Name"

        #     # Check if the product is out of stock
        #     out_of_stock_element = await product.query_selector('span[data-hook="product-item-out-of-stock"]')
        #     if out_of_stock_element:
        #         # If the product is out of stock, use the text "Out of stock" instead of a price
        #         price_value = await out_of_stock_element.text_content()
        #     else:
        #         # If in stock, try to get the standard price
        #         price_element = await product.query_selector('span[data-hook="product-item-price-to-pay"]')
                
        #         # If standard price not found, check for the "From" price range
        #         if not price_element:
        #             price_element = await product.query_selector('span[data-hook="price-range-from"]')
                
        #         # Extract price if found
        #         price_value = await price_element.text_content() if price_element else None

        #     # Append product name and price (or "Out of stock" text) to the lists
        #     if price_value:
        #         product_names.append(product_name.strip())
        #         prices.append(price_value.strip())

        # # Navigate to the Phrozen page 2
        # print("Navigating to the Phrozen page 2...")
        # await page.goto("https://www.apply3d.com/phrozen?page=2")
        # print("Navigated to the Phrozen page 2.")
        # await page.wait_for_load_state("domcontentloaded")
        
        # # Scrape Phrozen page 2 products
        # phrozen_page2_products = await page.query_selector_all('li[data-hook="product-list-grid-item"]')

        # for product in phrozen_page2_products:
        #     # Extract product name
        #     name_element = await product.query_selector('p[data-hook="product-item-name"]')
        #     product_name = await name_element.text_content() if name_element else "No Name"

        #     # Check if the product is out of stock
        #     out_of_stock_element = await product.query_selector('span[data-hook="product-item-out-of-stock"]')
        #     if out_of_stock_element:
        #         # If the product is out of stock, use the text "Out of stock" instead of a price
        #         price_value = await out_of_stock_element.text_content()
        #     else:
        #         # If in stock, try to get the standard price
        #         price_element = await product.query_selector('span[data-hook="product-item-price-to-pay"]')
                
        #         # If standard price not found, check for the "From" price range
        #         if not price_element:
        #             price_element = await product.query_selector('span[data-hook="price-range-from"]')
                
        #         # Extract price if found
        #         price_value = await price_element.text_content() if price_element else None

        #     # Append product name and price (or "Out of stock" text) to the lists
        #     if price_value:
        #         product_names.append(product_name.strip())
        #         prices.append(price_value.strip())
 
        # # Navigate to the Saremco page
        # print("Navigating to the Saremco...")
        # await page.goto("https://www.apply3d.com/saremco")
        # print("Navigated to the Saremco.")
        # await page.wait_for_load_state("domcontentloaded") 
        
        # # Scrape Saremco products
        # saremco_products = await page.query_selector_all('li[data-hook="product-list-grid-item"]')

        # for product in saremco_products:
        #     # Extract product name
        #     name_element = await product.query_selector('p[data-hook="product-item-name"]')
        #     product_name = await name_element.text_content() if name_element else "No Name"

        #     # Check if the product is out of stock
        #     out_of_stock_element = await product.query_selector('span[data-hook="product-item-out-of-stock"]')
        #     if out_of_stock_element:
        #         # If the product is out of stock, use the text "Out of stock" instead of a price
        #         price_value = await out_of_stock_element.text_content()
        #     else:
        #         # If in stock, try to get the standard price
        #         price_element = await product.query_selector('span[data-hook="product-item-price-to-pay"]')
                
        #         # If standard price not found, check for the "From" price range
        #         if not price_element:
        #             price_element = await product.query_selector('span[data-hook="price-range-from"]')
                
        #         # Extract price if found
        #         price_value = await price_element.text_content() if price_element else None

        #     # Append product name and price (or "Out of stock" text) to the lists
        #     if price_value:
        #         product_names.append(product_name.strip())
        #         prices.append(price_value.strip())
        
        # Navigate through from pages and get product range and price
        for product_page in product_from_price_pages:
            # Navigate to individual page
            print("Navigating to", product_page)
            await page.goto(product_page)
            await page.wait_for_load_state("networkidle") 
            await page.wait_for_load_state("domcontentloaded") 
            print("DOM loaded")

            # Handle banner if present
            try:
                await page.wait_for_selector('button[data-hook="consent-banner-apply-button"]', timeout=5000)
                print("Banner found")
                await page.click('button[data-hook="consent-banner-apply-button"]')
                print("Banner clicked")
            except:
                print("Banner not found")

            # Get product name
            name_element = await page.query_selector('h1[data-hook="product-title"]')
            product_name = await name_element.text_content() if name_element else "No Name"

            # Set to control the dropdown state
            open_drop_down = False

            # Navigate the dropdown button
            dropdown_button = await page.query_selector('button[data-hook="dropdown-base"]')
            if dropdown_button:
                print("Dropdown button found.")

                # Open the dropdown the first time
                await page.evaluate('(element) => element.click()', dropdown_button)
                print("Dropdown button clicked via JavaScript.")
                open_drop_down = True  
                

                # Get all dropdown options within the container
                container = await page.query_selector('div#dropdown-options-container_-1')

                if container:
                    options = await container.query_selector_all('div[data-hook="option"]')
                    print("Dropdown options found:", len(options))

                    for option in options:
                        # Open the dropdown if it is closed
                        if not open_drop_down:
                            await page.evaluate('(element) => element.click()', dropdown_button)
                            print("Dropdown button clicked again via JavaScript.")
                            await page.wait_for_load_state("networkidle")
                            await page.wait_for_load_state("domcontentloaded")

                        
                        await page.evaluate('(element) => element.click()', option)
                        print("Clicked option via JavaScript:", option)

                        await page.wait_for_load_state("networkidle")
                        await page.wait_for_load_state("domcontentloaded")

                        # Extract sub-name and price from the current option
                        sub_name_element = await option.query_selector('span.sNipX2_') 
                        sub_name = await sub_name_element.text_content() if sub_name_element else "No Sub Name"
                        print("Sub name found:", sub_name)

                        price_element = await page.query_selector('span[data-hook="formatted-primary-price"]')
                        price_value = await price_element.text_content() if price_element else "No Price"
                        print("Price found:", price_value)

                        # Append the product name, sub-name, and price
                        product_names.append(f"{product_name.strip()} {sub_name.strip()}")
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
                df.loc[missing_index, "Current Prices"] = "(NOT ON SITE)"
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