from playwright.async_api import async_playwright
import asyncio

async def scrape_titles():
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

        #Await login modal and login
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

        # Assure login complete and navigate to product page
        await page.wait_for_load_state("networkidle")
        print("Navigating to the Asiga page...")
        await page.goto("https://www.apply3d.com/asiga")
        print("Navigated to the Asiga page.")

        
        # Extract the price spans and print to terminal
        price_elements = await page.query_selector_all('span.cfpn1d')

        for price in price_elements:
            price_value = await price.get_attribute('data-wix-price')  
            print(f"Price found: {price_value.strip()}")  

        await browser.close()

if __name__ == "__main__":
    asyncio.run(scrape_titles())  
