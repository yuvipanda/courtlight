import os
from urllib.parse import quote
import asyncio

import aiohttp
import pandas as pd

async def download_file(session, url, target_path):
    async with session.get(url) as response:
        with open(target_path, 'wb') as f:
            while True:
                chunk = await response.content.read(32 * 1024)
                if not chunk:
                    break
                f.write(chunk)

async def main():
    with open('delhi.jsonl') as f:
        cases = pd.read_json(f, lines=True)
    
    async with aiohttp.ClientSession() as session:
        for download_link in cases['download_link']:
            download_path = os.path.join(
                'judgements',
                quote(download_link).replace('/', r'_')
            )

            if not os.path.exists(download_path):
                await download_file(session, download_link, download_path)
                print(f'Downloaded {download_link}')


loop = asyncio.get_event_loop()
loop.run_until_complete(main())