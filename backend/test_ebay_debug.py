"""Debug eBay scraper HTML structure"""
import asyncio
import aiohttp
import re

async def test_raw():
    url = 'https://www.ebay.com/sch/i.html?_nkw=Iron+Man+%232+comic&LH_Sold=1&LH_Complete=1&_sacat=63'
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.9',
    }
    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers) as response:
            html = await response.text()

            # Find all unique classes containing 's-item'
            item_classes = re.findall(r'class="([^"]*s-item[^"]*)"', html)
            unique_classes = set()
            for c in item_classes:
                unique_classes.add(c)
            print('Classes containing s-item:')
            for c in sorted(unique_classes)[:20]:
                print(f'  {c}')

            # Find li elements
            li_count = html.count('<li ')
            print(f'\nTotal <li> elements: {li_count}')

            # Look for price patterns
            price_pattern = r'\$(\d+(?:,\d{3})*\.\d{2})'
            prices = re.findall(price_pattern, html)
            if prices:
                print(f'\nPrices found: {len(prices)}')
                print(f'Sample prices: {prices[:10]}')

            # Look for new eBay item structures
            print('\nLooking for new eBay structures:')
            patterns = [
                ('data-viewport', r'data-viewport'),
                ('data-track', r'data-track'),
                ('str-item-card', r'str-item-card'),
                ('s-item__info', r's-item__info'),
                ('srp-river', r'srp-river'),
            ]
            for name, pattern in patterns:
                matches = re.findall(pattern, html)
                print(f'  {name}: {len(matches)}')

            # Save sample of HTML for inspection
            with open('ebay_debug.html', 'w', encoding='utf-8') as f:
                f.write(html)
            print('\nFull HTML saved to ebay_debug.html')

if __name__ == '__main__':
    asyncio.run(test_raw())
