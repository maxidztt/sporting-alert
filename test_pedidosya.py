from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)

    page = browser.new_page()

    page.goto(
        "https://www.pedidosya.com.ar/groceries/web/v1/vendors/183015/categories",
        wait_until="networkidle"
    )

    print("TITULO:", page.title())
    print(page.content()[:2000])

    browser.close()
