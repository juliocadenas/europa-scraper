# Eliminar la importación circular
# No importar desde controller aquí, ya que controller importa otros módulos

# Simplemente exportar los nombres sin importarlos directamente
__all__ = [
    'ScraperController',
    'BrowserManager',
    'SearchEngine',
    'ContentExtractor',
    'TextProcessor',
    'ResultManager',
    'ProgressReporter',
    'URLUtils'
]
