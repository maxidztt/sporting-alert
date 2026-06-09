from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(
        headless=True,
        args=[
            "--disable-blink-features=AutomationControlled"
        ]
    )

    page = browser.new_page(
        user_agent=(
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/137.0.0.0 Safari/537.36"
        )
    )

    try:
        response = page.goto(
            "https://www.pedidosya.com.ar",
            timeout=30000
        )

        print("STATUS:", response.status if response else "NO RESPONSE")
        print("URL:", page.url)
        print(page.content()[:3000])

    except Exception as e:
        print("ERROR:", e)

    browser.close()
