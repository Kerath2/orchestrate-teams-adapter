#!/usr/bin/env python3
"""
Script de validación de configuración
Verifica que todas las variables de entorno necesarias estén configuradas
"""
from dotenv import load_dotenv
load_dotenv()

import os
from typing import List, Tuple

# Colores
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'

def check_required(name: str, value: str) -> Tuple[bool, str]:
    """Verifica si una variable requerida está configurada."""
    if not value:
        return False, f"{Colors.RED}✗ {name}: NO CONFIGURADO{Colors.ENDC}"
    return True, f"{Colors.GREEN}✓ {name}: {value[:20]}...{Colors.ENDC}"

def check_optional(name: str, value: str, default: str = "") -> str:
    """Verifica una variable opcional."""
    if not value:
        return f"{Colors.YELLOW}○ {name}: Usando valor por defecto ({default}){Colors.ENDC}"
    return f"{Colors.GREEN}✓ {name}: {value}{Colors.ENDC}"

def main():
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'='*70}")
    print("VALIDACIÓN DE CONFIGURACIÓN - TEAMS ADAPTER")
    print(f"{'='*70}{Colors.ENDC}\n")

    all_valid = True
    warnings: List[str] = []

    # Microsoft Teams Bot
    print(f"{Colors.BOLD}📱 Microsoft Teams Bot{Colors.ENDC}")
    teams_vars = [
        ("MICROSOFT_APP_ID", os.getenv("MICROSOFT_APP_ID", "")),
        ("MICROSOFT_APP_PASSWORD", os.getenv("MICROSOFT_APP_PASSWORD", "")),
    ]

    for name, value in teams_vars:
        if not value:
            print(f"{Colors.YELLOW}○ {name}: No configurado (opcional para pruebas){Colors.ENDC}")
            warnings.append(f"Microsoft Teams: {name} no está configurado")
        else:
            print(f"{Colors.GREEN}✓ {name}: Configurado{Colors.ENDC}")

    print(check_optional("MICROSOFT_TENANT_ID", os.getenv("MICROSOFT_TENANT_ID", ""), "None"))

    # Watsonx Orchestrate
    print(f"\n{Colors.BOLD}🤖 Watsonx Orchestrate{Colors.ENDC}")
    orchestrate_required = [
        ("WATSONX_ORCHESTRATE_API_KEY", os.getenv("WATSONX_ORCHESTRATE_API_KEY", "")),
        ("WATSONX_ORCHESTRATE_URL", os.getenv("WATSONX_ORCHESTRATE_URL", "")),
        ("WATSONX_ORCHESTRATE_AGENT_ID", os.getenv("WATSONX_ORCHESTRATE_AGENT_ID", "")),
    ]

    for name, value in orchestrate_required:
        valid, msg = check_required(name, value)
        print(msg)
        if not valid:
            all_valid = False

    # Watsonx.ai
    print(f"\n{Colors.BOLD}🧠 Watsonx.ai (Control de Idioma){Colors.ENDC}")
    wx_required = [
        ("WX_APIKEY", os.getenv("WX_APIKEY", "")),
        ("WX_PROJECT_ID", os.getenv("WX_PROJECT_ID", "")),
    ]

    wx_enabled = True
    for name, value in wx_required:
        valid, msg = check_required(name, value)
        print(msg)
        if not valid:
            wx_enabled = False
            warnings.append(f"Watsonx.ai: {name} no configurado - control de idioma deshabilitado")

    if wx_enabled:
        print(check_optional("WX_URL", os.getenv("WX_URL", ""), "https://us-south.ml.cloud.ibm.com"))
        print(check_optional("WX_MODEL_ID", os.getenv("WX_MODEL_ID", ""), "ibm/granite-3-8b-instruct"))
        print(check_optional("WX_MAX_NEW_TOKENS", os.getenv("WX_MAX_NEW_TOKENS", ""), "2000"))
        print(check_optional("WX_TEMPERATURE", os.getenv("WX_TEMPERATURE", ""), "0.3"))
        print(check_optional("WX_MAX_CONCURRENT", os.getenv("WX_MAX_CONCURRENT", ""), "7"))

    # Redis
    print(f"\n{Colors.BOLD}💾 Redis (Gestión de Sesiones){Colors.ENDC}")
    print(check_optional("REDIS_HOST", os.getenv("REDIS_HOST", ""), "localhost"))
    print(check_optional("REDIS_PORT", os.getenv("REDIS_PORT", ""), "6379"))
    print(check_optional("REDIS_DB", os.getenv("REDIS_DB", ""), "0"))

    redis_ssl = os.getenv("REDIS_SSL", "false").lower() == "true"
    if redis_ssl:
        print(f"{Colors.GREEN}✓ REDIS_SSL: Habilitado{Colors.ENDC}")
    else:
        print(f"{Colors.YELLOW}○ REDIS_SSL: Deshabilitado{Colors.ENDC}")

    # User Profile Service
    print(f"\n{Colors.BOLD}👤 User Profile Service (Opcional){Colors.ENDC}")
    profile_url = os.getenv("USER_PROFILE_API_URL", "")
    profile_secret = os.getenv("USER_PROFILE_CLIENT_SECRET", "")

    if profile_url and profile_secret:
        print(f"{Colors.GREEN}✓ User Profile Service: Habilitado{Colors.ENDC}")
        print(f"{Colors.GREEN}  - URL: {profile_url}{Colors.ENDC}")
    else:
        print(f"{Colors.YELLOW}○ User Profile Service: Deshabilitado{Colors.ENDC}")

    # Resumen
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'='*70}")
    print("RESUMEN")
    print(f"{'='*70}{Colors.ENDC}\n")

    if all_valid:
        print(f"{Colors.GREEN}{Colors.BOLD}✓ Configuración válida - Listo para ejecutar{Colors.ENDC}\n")
    else:
        print(f"{Colors.RED}{Colors.BOLD}✗ Configuración incompleta - Faltan variables requeridas{Colors.ENDC}\n")

    if warnings:
        print(f"{Colors.YELLOW}{Colors.BOLD}⚠️  ADVERTENCIAS:{Colors.ENDC}")
        for warning in warnings:
            print(f"  - {warning}")
        print()

    # Instrucciones
    print(f"{Colors.BLUE}{Colors.BOLD}📝 PRÓXIMOS PASOS:{Colors.ENDC}")
    if not all_valid:
        print(f"  1. Copia .env.example a .env: {Colors.BOLD}cp .env.example .env{Colors.ENDC}")
        print(f"  2. Edita .env y completa las variables faltantes")
        print(f"  3. Ejecuta de nuevo: {Colors.BOLD}python validate_config.py{Colors.ENDC}")
    else:
        print(f"  1. Para probar: {Colors.BOLD}python test_watsonx.py{Colors.ENDC}")
        print(f"  2. Para probar conversación completa: {Colors.BOLD}python test_conversation_flow.py{Colors.ENDC}")
        print(f"  3. Para iniciar servidor: {Colors.BOLD}python server.py{Colors.ENDC}")
    print()

if __name__ == "__main__":
    main()
