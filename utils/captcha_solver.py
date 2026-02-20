import logging
import httpx
import time
import asyncio
import uuid
import base64

logger = logging.getLogger(__name__)

class CaptchaSolver:
    """
    Gestor para resolver CAPTCHAs, soportando múltiples servicios y modo manual.
    """

    def __init__(self, config_manager, captcha_challenge_callback=None, captcha_solution_queue=None):
        """
        Inicializa el solucionador de CAPTCHAs.

        Args:
            config_manager: Instancia del gestor de configuración (Config).
            captcha_challenge_callback: Función de callback para enviar desafíos de CAPTCHA al cliente.
            captcha_solution_queue: Cola para recibir soluciones de CAPTCHA del cliente.
        """
        self.config = config_manager
        self.captcha_challenge_callback = captcha_challenge_callback
        self.captcha_solution_queue = captcha_solution_queue
        self._captcha_detected_count = 0
        self._captcha_solved_count = 0
        self._manual_captcha_pending = False # New flag

    async def solve_captcha(self, page: 'Page' = None, image_url: str = None, page_url: str = None, site_key: str = None) -> str | None:
        logger.info("solve_captcha method called.")
        """
        Punto de entrada principal para resolver un CAPTCHA.

        Lee la configuración y delega al método de resolución apropiado.

        Args:
            page: La instancia de la página de Playwright (necesaria para reCAPTCHA manual).
            image_url: La URL de la imagen del CAPTCHA (para CAPTCHAs de imagen).
            page_url: La URL de la página donde se encuentra el reCAPTCHA (para reCAPTCHAs).
            site_key: La sitekey del reCAPTCHA (para reCAPTCHAs).

        Returns:
            El texto del CAPTCHA resuelto, o None si falla o está deshabilitado.
        """
        if not self.config.get("captcha_solving_enabled", False):
            logger.info("La resolución de CAPTCHA está deshabilitada en la configuración.")
            return None

        service = self.config.get("captcha_service", "Manual")
        logger.info(f"Intentando resolver CAPTCHA usando el servicio: {service}")

        if service == "2Captcha":
            if site_key and page_url:
                return await self._solve_recaptcha_with_2captcha(page_url, site_key)
            elif image_url:
                return await self._solve_with_2captcha(image_url)
            else:
                logger.error("Parámetros insuficientes para resolver CAPTCHA con 2Captcha.")
                return None
        elif service == "Manual":
            if site_key and page_url:
                if not page:
                    logger.error("Se requiere el objeto 'page' para resolver reCAPTCHA manualmente.")
                    return None
                page_content = await page.content()
                return await self._solve_manually(page_content=page_content)
            elif image_url:
                return await self._solve_manually(image_url=image_url)
            else:
                logger.error("Parámetros insuficientes para resolver CAPTCHA manualmente.")
                return None
        else:
            logger.warning(f"Servicio de CAPTCHA desconocido: {service}")
            return None

    async def _solve_with_2captcha(self, image_url: str) -> str | None:
        """
        Resuelve un CAPTCHA usando la API de 2Captcha.

        Args:
            image_url: URL de la imagen del CAPTCHA.

        Returns:
            El texto del CAPTCHA o None si hay un error.
        """
        api_key = self.config.get("captcha_api_key")
        if not api_key:
            logger.error("La API key de 2Captcha no está configurada.")
            return None

        logger.info("Enviando CAPTCHA a 2Captcha.")
        
        # 1. Enviar la imagen
        try:
            async with httpx.AsyncClient() as client:
                image_response = await client.get(image_url)
                image_response.raise_for_status()
                response = await client.post(
                    "http://2captcha.com/in.php",
                    params={"key": api_key, "method": "post"},
                    files={"file": image_response.content}
                )
                response.raise_for_status()

            if "OK|" not in response.text:
                logger.error(f"Error en la API de 2Captcha al enviar: {response.text}")
                return None

            captcha_id = response.text.split('|')[1]
            logger.info(f"CAPTCHA enviado con éxito. ID: {captcha_id}")

        except httpx.RequestError as e:
            logger.error(f"Error de red al enviar CAPTCHA a 2Captcha: {e} - Response: {response.text if 'response' in locals() else 'No response'}")
            return None

        # 2. Sondear el resultado
        time.sleep(10)  # Espera inicial antes de empezar a sondear
        max_attempts = 30
        for attempt in range(max_attempts):
            try:
                async with httpx.AsyncClient() as client:
                    result_response = await client.get(
                        f"http://2captcha.com/res.php?key={api_key}&action=get&id={captcha_id}"
                    )
                    result_response.raise_for_status()

                logger.info(f"Respuesta de 2Captcha (intento {attempt + 1}): {result_response.text}")

                if "OK|" in result_response.text:
                    solution = result_response.text.split('|')[1]
                    logger.info(f"CAPTCHA resuelto por 2Captcha: {solution}")
                    return solution
                elif result_response.text == "CAPCHA_NOT_READY":
                    logger.info("El CAPTCHA aún no está listo, esperando...")
                    time.sleep(5)
                else:
                    logger.error(f"Error en la API de 2Captcha al obtener resultado: {result_response.text}")
                    return None

            except httpx.RequestError as e:
                logger.error(f"Error de red al obtener resultado de 2Captcha: {e} - Response: {result_response.text if 'result_response' in locals() else 'No response'}")
                return None
        
        logger.error("Se superó el número máximo de intentos para resolver el CAPTCHA.")
        return None

    async def _solve_manually(self, image_url: str = None, page_content: str = None) -> str | None:
        """
        Permite al usuario resolver el CAPTCHA manualmente a través de la GUI del cliente.
        Envía el desafío (imagen o contenido HTML) al cliente y espera la solución.

        Args:
            image_url: URL de la imagen del CAPTCHA.
            page_content: Contenido HTML de la página del CAPTCHA.

        Returns:
            El texto introducido por el usuario o None si cancela o falla.
        """
        if not self.captcha_challenge_callback or not self.captcha_solution_queue:
            logger.error("Callbacks o colas de comunicación para CAPTCHA manual no configurados.")
            return None

        captcha_id = str(uuid.uuid4())
        logger.info(f"Generando desafío CAPTCHA manual con ID: {captcha_id}")

        try:
            challenge_data = {
                "id": captcha_id,
                "type": "none",
                "data": ""
            }

            if page_content:
                logger.info("Enviando contenido HTML de reCAPTCHA al cliente.")
                challenge_data["type"] = "recaptcha"
                challenge_data["data"] = page_content
            elif image_url:
                logger.info(f"Descargando imagen de CAPTCHA desde: {image_url}")
                async with httpx.AsyncClient() as client:
                    response = await client.get(image_url)
                response.raise_for_status()
                image_data = response.content
                image_base64 = base64.b64encode(image_data).decode('utf-8')
                challenge_data["type"] = "image"
                challenge_data["data"] = image_base64
            else:
                logger.error("Se requiere image_url o page_content para resolver manualmente.")
                return None

            # Enviar el desafío al cliente a través del callback
            self.captcha_challenge_callback(challenge_data)
            self._captcha_detected_count += 1
            logger.info(f"Desafío CAPTCHA {captcha_id} enviado al cliente. Esperando solución...")

            self._manual_captcha_pending = True # Set flag when waiting starts

            # Esperar la solución del cliente
            solution_data = await asyncio.wait_for(self.captcha_solution_queue.get(), timeout=300) # 5 minutos

            if solution_data and solution_data.get('captcha_id') == captcha_id:
                solution = solution_data.get('solution')
                if solution:
                    self._captcha_solved_count += 1
                    logger.info(f"CAPTCHA {captcha_id} resuelto manualmente por el cliente con token: {solution[:30]}...")
                    return solution
                else:
                    logger.warning(f"El cliente envió una solución vacía para CAPTCHA {captcha_id}.")
                    return None
            else:
                logger.warning(f"Solución de CAPTCHA {captcha_id} no coincide o es inválida.")
                return None

        except asyncio.TimeoutError:
            logger.error(f"Tiempo de espera agotado para la solución del CAPTCHA {captcha_id}.")
            return None
        except requests.RequestException as e:
            logger.error(f"Error al descargar la imagen del CAPTCHA {image_url}: {e}")
            return None
        except Exception as e:
            logger.error(f"Error durante la resolución manual del CAPTCHA {captcha_id}: {e}")
            return None
        finally:
            self._manual_captcha_pending = False # Clear flag when waiting ends

    async def is_captcha_present(self, page) -> bool:
        """
        Verifica si hay un CAPTCHA visible en la página.

        Args:
            page: La página de Playwright a verificar.

        Returns:
            True si se detecta un CAPTCHA, False en caso contrario.
        """
        # Implementación simple: busca un iframe de Cloudflare o una imagen de CAPTCHA
        # Esto puede necesitar ser ajustado para el sitio específico
        captcha_iframe_locator = page.locator("iframe[src*='cloudflare.com/turnstile']")
        if await captcha_iframe_locator.count() > 0:
            logger.info("Detectado iframe de CAPTCHA de Cloudflare.")
            return True

        # Busca campos de entrada de CAPTCHA comunes
        captcha_input = page.locator("input[name='captcha'], input[id='captcha']")
        if await captcha_input.count() > 0:
            logger.info("Detectado campo de entrada de CAPTCHA.")
            return True

        return False

    async def handle_captcha(self, page) -> bool:
        """
        Maneja un CAPTCHA encontrado en la página.

        Args:
            page: La página de Playwright con el CAPTCHA.

        Returns:
            True si el CAPTCHA se manejó correctamente, False en caso contrario.
        """
        # Aquí puedes implementar la lógica para resolver el CAPTCHA
        # Por ejemplo, si es un CAPTCHA de imagen, extraer la URL de la imagen
        # y enviarla a un servicio de resolución.

        # Por ahora, simplemente registraremos que se encontró un CAPTCHA
        logger.warning("Manejo de CAPTCHA aún no implementado.")
        return False

    
        """
        Resuelve un reCAPTCHA usando la API de 2Captcha.

        Args:
            page_url: La URL de la página donde se encuentra el reCAPTCHA.
            site_key: La sitekey del reCAPTCHA.

        Returns:
            El token de reCAPTCHA o None si hay un error.
        """
        api_key = self.config.get("captcha_api_key")
        if not api_key:
            logger.error("La API key de 2Captcha no está configurada para reCAPTCHA.")
            return None

        logger.info(f"Enviando reCAPTCHA a 2Captcha para URL: {page_url}, Sitekey: {site_key}")
        
        # 1. Enviar la solicitud de reCAPTCHA
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "http://2captcha.com/in.php",
                    data={
                        "key": api_key,
                        "method": "recaptcha",
                        "googlekey": site_key,
                        "pageurl": page_url
                    }
                )
                response.raise_for_status()

            if "OK|" not in response.text:
                logger.error(f"Error en la API de 2Captcha al enviar reCAPTCHA: {response.text}")
                return None

            captcha_id = response.text.split('|')[1]
            logger.info(f"reCAPTCHA enviado con éxito. ID: {captcha_id}")

        except httpx.RequestError as e:
            logger.error(f"Error de red al enviar reCAPTCHA a 2Captcha: {e} - Response: {response.text if 'response' in locals() else 'No response'}")
            return None

        # 2. Sondear el resultado
        time.sleep(10)  # Espera inicial antes de empezar a sondear
        max_attempts = 30
        for attempt in range(max_attempts):
            try:
                async with httpx.AsyncClient() as client:
                    result_response = await client.get(
                        f"http://2captcha.com/res.php?key={api_key}&action=get&id={captcha_id}"
                    )
                    result_response.raise_for_status()

                logger.info(f"Respuesta de 2Captcha (intento {attempt + 1}): {result_response.text}")

                if "OK|" in result_response.text:
                    solution = result_response.text.split('|')[1]
                    logger.info(f"reCAPTCHA resuelto por 2Captcha: {solution}")
                    return solution
                elif result_response.text == "CAPCHA_NOT_READY":
                    logger.info("El reCAPTCHA aún no está listo, esperando...")
                    time.sleep(5)
                else:
                    logger.error(f"Error en la API de 2Captcha al obtener resultado de reCAPTCHA: {result_response.text}")
                    return None

            except httpx.RequestError as e:
                logger.error(f"Error de red al obtener resultado de reCAPTCHA de 2Captcha: {e} - Response: {result_response.text if 'result_response' in locals() else 'No response'}")
                return None
        
        logger.error("Se superó el número máximo de intentos para resolver el reCAPTCHA.")
        return None

    async def is_captcha_present(self, page) -> bool:
        """
        Verifica si hay un CAPTCHA visible en la página.

        Args:
            page: La página de Playwright a verificar.

        Returns:
            True si se detecta un CAPTCHA, False en caso contrario.
        """
        # Implementación simple: busca un iframe de Cloudflare o una imagen de CAPTCHA
        # Esto puede necesitar ser ajustado para el sitio específico
        captcha_iframe_locator = page.locator("iframe[src*='cloudflare.com/turnstile']")
        if await captcha_iframe_locator.count() > 0:
            logger.info("Detectado iframe de CAPTCHA de Cloudflare.")
            return True

        # Busca campos de entrada de CAPTCHA comunes
        captcha_input = page.locator("input[name='captcha'], input[id='captcha']")
        if await captcha_input.count() > 0:
            logger.info("Detectado campo de entrada de CAPTCHA.")
            return True

        return False

    async def handle_captcha(self, page) -> bool:
        """
        Maneja un CAPTCHA encontrado en la página.

        Args:
            page: La página de Playwright con el CAPTCHA.

        Returns:
            True si el CAPTCHA se manejó correctamente, False en caso contrario.
        """
        # La lógica de manejo de CAPTCHA ahora se encuentra en BrowserManager.handle_captcha
        # Este método en CaptchaSolver ya no es necesario para la detección y resolución directa.
        # Solo se mantiene para compatibilidad si otras partes del código lo llaman.
        return False

    def get_stats(self) -> dict:
        """
        Retorna las estadísticas de resolución de CAPTCHAs.

        Returns:
            Un diccionario con las estadísticas.
        """
        return {
            "captcha_detected_count": self._captcha_detected_count,
            "captcha_solved_count": self._captcha_solved_count,
        }

    def is_manual_captcha_pending(self) -> bool:
        """
        Verifica si hay un CAPTCHA manual pendiente de resolución por parte del usuario.
        """
        return self._manual_captcha_pending