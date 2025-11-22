#!/usr/bin/env python3
"""
Prueba rápida del sistema de proxies
Ejecutar: python utils/proxy_tester.py
"""

import asyncio
import sys
from utils.proxy_manager import ProxyManager

async def test_proxy_system():
    """Prueba completa del sistema de proxies"""

    print("🔧 SISTEMA DE PROXIES - PRUEBA COMPLETA")
    print("=" * 50)

    # 1. Inicializar proxy manager
    pm = ProxyManager()
    stats = pm.get_stats()

    print("📊 Estado inicial:")
    print(f"   - Total proxies: {stats['total_proxies']}")
    print(f"   - Habilitado: {stats['enabled']}")
    print(f"   - Rotación: {stats['rotation_enabled']}")

    # 2. Verificar si hay proxies configurados
    if stats['total_proxies'] == 0:
        print("\n⚠️  No hay proxies configurados.")
        print("   Para agregar proxies, usa la configuración de la GUI")
        print("   o edita directamente la lista de proxies.")
        return

    print(f"\n✅ {stats['total_proxies']} proxies configurados")

    # 3. Activar el sistema
    print("\n🔓 Activando sistema de proxies...")
    pm.enable(True)
    print(f"   Estado: {'ACTIVADO' if pm.is_enabled() else 'INACTIVO'}")

    # 4. Probar la rotación
    print("\n🔄 Probando rotación de proxies:")
    proxies_tested = []

    for i in range(min(5, stats['total_proxies'])):  # Probar hasta 5 proxies
        proxy = pm.get_next_proxy()
        if proxy:
            masked_host = proxy['host'][:3] + "****" + proxy['host'][-3:] if len(proxy['host']) > 6 else proxy['host']
            print(f"   {i+1}. {masked_host}:{proxy['port']} (autenticación: {'SÍ' if proxy.get('username') else 'NO'})")
            proxies_tested.append(proxy['original_string'])
        else:
            print(f"   {i+1}. ❌ No se pudo obtener proxy")
            break

    # 5. Estadísticas
    print("\n📈 Resultados:")
    print(f"   - Proxies probados: {len(proxies_tested)}")
    print(f"   - Proxies únicos: {len(set(proxies_tested))}")

    if len(set(proxies_tested)) > 1:
        print("   ✅ ROTACIÓN FUNCIONANDO (proxies diferentes)")
    else:
        print("   ⚠️  Solo un proxy disponible")

    # 6. Instrucciones para el usuario
    print("\n🎯 PARA USUARIO FINAL:")
    print("   Para activar proxies desde la GUI:")
    print("   1. Abrir la configuración de proxies")
    print("   2. Marcar 'Habilitar proxies'")
    print("   3. Ajustar timeout si es necesario")
    print("   4. Guardar configuración")

    print("\n🔧 DESARROLLADORES:")
    print("   proxy_manager.enable(True)  # Para activar")
    print("   proxy_manager.enable(False) # Para desactivar")

    if pm.is_enabled():
        print("\n✅ SISTEMA LISTO PARA USO")

if __name__ == "__main__":
    asyncio.run(test_proxy_system())