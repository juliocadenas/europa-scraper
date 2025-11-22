import logging
import os
import asyncio
import aiohttp
from typing import Optional
from urllib.parse import urlparse
from playwright.async_api import async_playwright

logger = logging.getLogger(__name__)

class FileDownloader:
    """
    Downloads files and web pages.
    """
    
    def __init__(self):
        """Initialize the file downloader."""
        self.browser = None
        self.context = None
    
    async def _ensure_browser(self):
        """Ensure the browser is initialized."""
        if not self.browser:
            playwright = await async_playwright().start()
            self.browser = await playwright.chromium.launch(headless=True)
            self.context = await self.browser.new_context()
    
    async def download_as_pdf(self, url: str, output_path: str) -> bool:
        """
        Download a web page as PDF.
        
        Args:
            url: URL to download
            output_path: Path to save the PDF
            
        Returns:
            True if successful, False otherwise
        """
        try:
            await self._ensure_browser()
            
            logger.info(f"Downloading {url} as PDF to {output_path}")
            
            # Create a new page
            page = await self.context.new_page()
            
            # Navigate to the URL
            await page.goto(url, wait_until='networkidle')
            
            # Ensure the output directory exists
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            
            # Save as PDF
            await page.pdf(path=output_path)
            
            await page.close()
            
            logger.info(f"Successfully downloaded {url} as PDF to {output_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error downloading {url} as PDF: {str(e)}")
            return False
    
    async def download_file(self, url: str, output_path: str) -> bool:
        """
        Download a file.
        
        Args:
            url: URL to download
            output_path: Path to save the file
            
        Returns:
            True if successful, False otherwise
        """
        try:
            logger.info(f"Downloading file from {url} to {output_path}")
            
            # Ensure the output directory exists
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            
            # Download the file
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    if response.status == 200:
                        with open(output_path, 'wb') as f:
                            while True:
                                chunk = await response.content.read(8192)
                                if not chunk:
                                    break
                                f.write(chunk)
                        
                        logger.info(f"Successfully downloaded file from {url} to {output_path}")
                        return True
                    else:
                        logger.error(f"Error downloading file from {url}: HTTP {response.status}")
                        return False
                        
        except Exception as e:
            logger.error(f"Error downloading file from {url}: {str(e)}")
            return False
    
    async def close(self):
        """Close the browser and clean up resources."""
        try:
            if self.browser:
                await self.browser.close()
                self.browser = None
                self.context = None
                logger.info("Navegador del descargador de archivos cerrado correctamente")
        except Exception as e:
            logger.error(f"Error cerrando navegador del descargador de archivos: {str(e)}")
