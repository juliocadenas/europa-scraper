
import asyncio
from controllers.scraper_controller import ScraperController
from utils.config import Config

async def main():
    config = Config()
    controller = ScraperController(config_manager=config)

    params = {
        'from_sic': '13199.0',
        'to_sic': '13199.0',
        'from_course': 'Cotton',
        'to_course': 'Cotton',
        'min_words': 30
    }

    await controller.run_scraping(params)

if __name__ == "__main__":
    asyncio.run(main())
