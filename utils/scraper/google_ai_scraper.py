"""
Google AI Scraper Adapter
=========================
Módulo de scraping con IA usando ScrapeGraphAI + Ollama (LLM local).
Se integra como un motor de búsqueda adicional en el sistema Europa Scraper.

Requisitos:
- Ollama instalado y corriendo (https://ollama.ai)
- Modelo descargado: ollama pull llama3.1
- pip install scrapegraphai langchain langchain-community
"""

import asyncio
import logging
import os
import json
import re
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)


class GoogleAIScraper:
    """
    Scraper de Google basado en IA (ScrapeGraphAI + Ollama).
    Usa un LLM local para extraer URLs de resultados de Google
    de manera inteligente y adaptativa.
    """

    def __init__(
        self,
        ollama_url: str = "http://localhost:11434",
        model_name: str = "llama3.1",
        temperature: float = 0.1,
    ):
        self.ollama_url = ollama_url
        self.model_name = model_name
        self.temperature = temperature
        self._scraper = None
        self._initialized = False

    def _ensure_initialized(self):
        """Inicializa ScrapeGraphAI de forma lazy (solo cuando se necesita)."""
        if self._initialized:
            return True

        try:
            from scrapegraphai.graphs import SmartScraperGraph

            # Verificar que Ollama esté corriendo
            import requests

            try:
                resp = requests.get(f"{self.ollama_url}/api/tags", timeout=5)
                if resp.status_code != 200:
                    logger.error(
                        f"Ollama no responde en {self.ollama_url}. "
                        f"¿Está corriendo? ¿Descargaste el modelo '{self.model_name}'?"
                    )
                    return False

                # Verificar que el modelo esté disponible
                models = resp.json().get("models", [])
                model_names = [m.get("name", "") for m in models]
                model_found = any(self.model_name in mn for mn in model_names)

                if not model_found:
                    logger.warning(
                        f"Modelo '{self.model_name}' no encontrado en Ollama. "
                        f"Modelos disponibles: {model_names}. "
                        f"Ejecuta: ollama pull {self.model_name}"
                    )
                    # Intentar usar el primer modelo disponible
                    if model_names:
                        self.model_name = model_names[0].split(":")[0]
                        logger.info(f"Usando modelo alternativo: {self.model_name}")
                    else:
                        return False

            except requests.exceptions.ConnectionError:
                logger.error(
                    f"No se puede conectar a Ollama en {self.ollama_url}. "
                    f"Asegúrate de que Ollama esté corriendo."
                )
                return False

            self._initialized = True
            logger.info(
                f"GoogleAIScraper inicializado. Ollama={self.ollama_url}, "
                f"Modelo={self.model_name}"
            )
            return True

        except ImportError as e:
            logger.error(
                f"ScrapeGraphAI no está instalado. "
                f"Ejecuta: pip install scrapegraphai langchain langchain-community. "
                f"Error: {e}"
            )
            return False
        except Exception as e:
            logger.error(f"Error inicializando GoogleAIScraper: {e}")
            return False

    async def search_google_ai(
        self,
        query: str,
        site_domain: Optional[str] = None,
        max_results: int = 50,
    ) -> List[Dict[str, Any]]:
        """
        Realiza búsqueda en Google usando ScrapeGraphAI + LLM local.

        Args:
            query: Término de búsqueda (nombre del curso)
            site_domain: Dominio para filtrar (ej: europa.eu)
            max_results: Máximo de resultados a retornar

        Returns:
            Lista de dicts con keys: url, title, description, mediatype, format
        """
        # Construir query de búsqueda
        search_query = f"{query} site:{site_domain}" if site_domain else query
        logger.info(f"[Google AI] Iniciando búsqueda: '{search_query}'")

        # Inicializar de forma lazy
        if not self._ensure_initialized():
            logger.error(
                "[Google AI] No se pudo inicializar. "
                "Verifica que Ollama esté corriendo y el modelo esté descargado."
            )
            return []

        try:
            results = await self._scrape_with_scrapegraph(
                search_query, max_results
            )

            if not results:
                logger.info(
                    "[Google AI] ScrapeGraph no retornó resultados. "
                    "Intentando fallback con requests..."
                )
                results = await self._fallback_scrape(search_query, max_results)

            logger.info(
                f"[Google AI] Búsqueda completada. {len(results)} resultados."
            )
            return results

        except Exception as e:
            logger.error(f"[Google AI] Error en búsqueda: {e}")
            # Fallback a método manual
            return await self._fallback_scrape(search_query, max_results)

    async def _scrape_with_scrapegraph(
        self, search_query: str, max_results: int
    ) -> List[Dict[str, Any]]:
        """
        Usa ScrapeGraphAI para extraer resultados de Google.
        Se ejecuta en thread separado para no bloquear el event loop.
        """
        from scrapegraphai.graphs import SmartScraperGraph

        # Codificar query para URL
        import urllib.parse

        encoded_query = urllib.parse.quote_plus(search_query)
        google_url = f"https://www.google.com/search?q={encoded_query}&num={min(max_results, 100)}"

        # Configuración del graph de ScrapeGraphAI
        graph_config = {
            "llm": {
                "model": f"ollama/{self.model_name}",
                "base_url": self.ollama_url,
                "temperature": self.temperature,
            },
            "verbose": False,
            "headless": True,
        }

        # Prompt para extraer resultados de búsqueda
        prompt = (
            f"Extract all search result URLs from this Google search page. "
            f"For each result, extract: the URL (href), the title, and the description/snippet. "
            f"Return as a JSON list. Maximum {max_results} results. "
            f"Only include actual search result links, not Google navigation links."
        )

        # Ejecutar en thread para no bloquear async
        def _run_scraper():
            try:
                smart_scraper = SmartScraperGraph(
                    prompt=prompt,
                    source=google_url,
                    config=graph_config,
                )
                result = smart_scraper.run()
                return result
            except Exception as e:
                logger.error(f"[Google AI] ScrapeGraph error: {e}")
                return None

        result = await asyncio.to_thread(_run_scraper)

        if not result:
            return []

        # Parsear resultado de ScrapeGraphAI
        return self._parse_scrapegraph_result(result)

    def _parse_scrapegraph_result(self, result) -> List[Dict[str, Any]]:
        """
        Parsea la salida de ScrapeGraphAI al formato estándar del scraper.
        ScrapeGraphAI puede retornar dict con listas o lista directa.
        """
        parsed = []

        try:
            # ScrapeGraphAI puede retornar diversos formatos
            items = []

            if isinstance(result, dict):
                # Buscar la lista de resultados en el dict
                for key, value in result.items():
                    if isinstance(value, list):
                        items = value
                        break
                if not items:
                    # Si no hay lista, el dict mismo puede ser un resultado
                    items = [result]

            elif isinstance(result, list):
                items = result

            elif isinstance(result, str):
                # Intentar parsear como JSON
                try:
                    items = json.loads(result)
                except json.JSONDecodeError:
                    # Intentar extraer URLs directamente del texto
                    urls = re.findall(
                        r'https?://[^\s<>"\']+', result
                    )
                    for url in urls:
                        if "google.com" not in url and "gstatic.com" not in url:
                            items.append({"url": url})

            for item in items:
                if isinstance(item, dict):
                    url = item.get("url") or item.get("link") or item.get("href", "")
                    title = item.get("title") or item.get("name", "")
                    description = item.get("description") or item.get("snippet") or item.get("text", "")

                    if url and "google.com/search" not in url:
                        parsed.append(
                            {
                                "url": url,
                                "title": title,
                                "description": description,
                                "mediatype": "web",
                                "format": None,
                            }
                        )

                elif isinstance(item, str):
                    # Si es un string, intentar como URL
                    if item.startswith("http") and "google.com" not in item:
                        parsed.append(
                            {
                                "url": item,
                                "title": "",
                                "description": "",
                                "mediatype": "web",
                                "format": None,
                            }
                        )

        except Exception as e:
            logger.error(f"[Google AI] Error parseando resultado: {e}")

        return parsed

    async def _fallback_scrape(
        self, search_query: str, max_results: int
    ) -> List[Dict[str, Any]]:
        """
        Fallback: Usa requests + BeautifulSoup para extraer resultados de Google
        cuando ScrapeGraphAI no está disponible o falla.
        No requiere navegador ni LLM.
        """
        import urllib.parse

        encoded_query = urllib.parse.quote_plus(search_query)
        url = f"https://www.google.com/search?q={encoded_query}&num={min(max_results, 100)}"

        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/125.0.0.0 Safari/537.36"
            ),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Accept-Encoding": "gzip, deflate",
            "DNT": "1",
        }

        results = []

        def _fetch():
            try:
                import requests as req
                from bs4 import BeautifulSoup

                resp = req.get(url, headers=headers, timeout=15)
                if resp.status_code != 200:
                    logger.warning(
                        f"[Google AI Fallback] Google retornó status {resp.status_code}"
                    )
                    return []

                soup = BeautifulSoup(resp.text, "lxml")
                found = []

                # Intentar múltiples selectores de Google
                selectors = [
                    "div.g div.yuRUbf a",  # Resultado clásico
                    "div[data-sokoban-container] a",  # Nuevo layout
                    "div.g a[href]",  # Genérico
                    "a[href^='/url?q=']",  # Redirect links
                ]

                for selector in selectors:
                    links = soup.select(selector)
                    for link in links:
                        href = link.get("href", "")
                        if not href:
                            continue

                        # Limpiar URLs de redirect de Google
                        if "/url?q=" in href:
                            href = href.split("/url?q=")[1].split("&")[0]

                        # Filtrar URLs internas de Google
                        if any(
                            skip in href
                            for skip in [
                                "google.com",
                                "gstatic.com",
                                "googleapis.com",
                                "schemas.microsoft.com",
                                "/search?",
                            ]
                        ):
                            continue

                        if not href.startswith("http"):
                            continue

                        # Extraer título
                        title_el = link.find("h3") or link.find("span")
                        title = title_el.get_text(strip=True) if title_el else ""

                        # Extraer descripción
                        desc = ""
                        parent = link.find_parent("div", class_="g")
                        if parent:
                            desc_el = parent.select_one(
                                "div[data-sncf], div.VwiC3b, span.aCOpRe"
                            )
                            if desc_el:
                                desc = desc_el.get_text(strip=True)

                        found.append(
                            {
                                "url": href,
                                "title": title,
                                "description": desc,
                                "mediatype": "web",
                                "format": None,
                            }
                        )

                # Deduplicar por URL
                seen = set()
                unique = []
                for r in found:
                    if r["url"] not in seen:
                        seen.add(r["url"])
                        unique.append(r)

                return unique[:max_results]

            except Exception as e:
                logger.error(f"[Google AI Fallback] Error: {e}")
                return []

        results = await asyncio.to_thread(_fetch)
        logger.info(
            f"[Google AI Fallback] Extraídos {len(results)} resultados"
        )
        return results

    def check_availability(self) -> Dict[str, Any]:
        """
        Verifica si el scraper AI está disponible (Ollama + modelo).
        Retorna dict con estado y detalles.
        """
        status = {
            "available": False,
            "ollama_running": False,
            "model_available": False,
            "model_name": self.model_name,
            "ollama_url": self.ollama_url,
            "scrapegraph_installed": False,
            "errors": [],
        }

        # Verificar ScrapeGraphAI
        try:
            import scrapegraphai

            status["scrapegraph_installed"] = True
        except ImportError:
            status["errors"].append(
                "ScrapeGraphAI no instalado. pip install scrapegraphai"
            )

        # Verificar Ollama
        try:
            import requests

            resp = requests.get(f"{self.ollama_url}/api/tags", timeout=5)
            if resp.status_code == 200:
                status["ollama_running"] = True
                models = resp.json().get("models", [])
                model_names = [m.get("name", "") for m in models]
                if any(self.model_name in mn for mn in model_names):
                    status["model_available"] = True
                else:
                    status["errors"].append(
                        f"Modelo '{self.model_name}' no encontrado. "
                        f"Disponibles: {model_names}. "
                        f"Ejecuta: ollama pull {self.model_name}"
                    )
            else:
                status["errors"].append(
                    f"Ollama respondió con status {resp.status_code}"
                )
        except requests.exceptions.ConnectionError:
            status["errors"].append(
                f"No se puede conectar a Ollama en {self.ollama_url}. "
                "¿Está corriendo?"
            )
        except Exception as e:
            status["errors"].append(f"Error verificando Ollama: {e}")

        status["available"] = (
            status["scrapegraph_installed"]
            and status["ollama_running"]
            and status["model_available"]
        )

        return status