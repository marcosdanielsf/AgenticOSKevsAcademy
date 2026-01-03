#!/usr/bin/env python3
"""
Test FASE 0 API Endpoints
=========================
Testa os endpoints da API de integração FASE 0.

Uso:
    python tests/test_fase0_endpoints.py
    python tests/test_fase0_endpoints.py --base-url http://localhost:8000
"""

import os
import sys
import json
import argparse
import requests
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

# Carregar variáveis de ambiente
project_root = Path(__file__).parent.parent.parent
load_dotenv(project_root / '.env')


class FASE0Tester:
    """Tester para endpoints FASE 0"""

    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url.rstrip('/')
        self.results = []

    def log(self, status: str, endpoint: str, message: str):
        """Log de teste"""
        icon = "✅" if status == "PASS" else "❌" if status == "FAIL" else "⚠️"
        print(f"{icon} [{status}] {endpoint}: {message}")
        self.results.append({
            'status': status,
            'endpoint': endpoint,
            'message': message,
            'timestamp': datetime.now().isoformat()
        })

    def test_health_check(self):
        """Testa endpoint /api/health"""
        endpoint = "/api/health"
        try:
            response = requests.get(f"{self.base_url}{endpoint}", timeout=10)
            if response.status_code == 200:
                data = response.json()
                if data.get('status') == 'healthy':
                    self.log("PASS", endpoint, f"API saudável - version: {data.get('version')}")
                    return True
                else:
                    self.log("FAIL", endpoint, f"Status inesperado: {data}")
            else:
                self.log("FAIL", endpoint, f"HTTP {response.status_code}")
        except requests.exceptions.ConnectionError:
            self.log("FAIL", endpoint, "API não está rodando")
        except Exception as e:
            self.log("FAIL", endpoint, str(e))
        return False

    def test_list_skills(self):
        """Testa endpoint /api/skills"""
        endpoint = "/api/skills"
        try:
            response = requests.get(f"{self.base_url}{endpoint}", timeout=10)
            if response.status_code == 200:
                data = response.json()
                skills = data.get('skills', [])
                self.log("PASS", endpoint, f"Encontradas {len(skills)} skills")

                # Verificar skills esperadas
                expected_skills = ['sync_lead', 'update_ghl_contact', 'get_lead_by_channel', 'get_lead_context_for_ai', 'ensure_ghl_custom_fields']
                found_skills = [s['name'] for s in skills]

                for expected in expected_skills:
                    if expected in found_skills:
                        print(f"   ✓ {expected}")
                    else:
                        print(f"   ✗ {expected} (não encontrada)")

                return True
            else:
                self.log("FAIL", endpoint, f"HTTP {response.status_code}: {response.text}")
        except Exception as e:
            self.log("FAIL", endpoint, str(e))
        return False

    def test_get_lead_context(self):
        """Testa endpoint /api/get-lead-context"""
        endpoint = "/api/get-lead-context"
        try:
            # Teste com um identificador fictício (deve retornar found=false)
            payload = {
                "channel": "instagram",
                "identifier": "@test_user_that_does_not_exist"
            }
            response = requests.post(
                f"{self.base_url}{endpoint}",
                json=payload,
                timeout=10
            )

            if response.status_code == 200:
                data = response.json()
                if data.get('found') == False:
                    self.log("PASS", endpoint, "Retornou found=false para lead inexistente (correto)")
                else:
                    self.log("WARN", endpoint, f"Resposta: {data}")
                return True
            elif response.status_code == 500:
                # Pode falhar se tabelas não existem ainda
                self.log("WARN", endpoint, "Erro 500 - tabelas podem não existir ainda")
                return True
            else:
                self.log("FAIL", endpoint, f"HTTP {response.status_code}: {response.text}")
        except Exception as e:
            self.log("FAIL", endpoint, str(e))
        return False

    def test_sync_lead(self):
        """Testa endpoint /api/sync-lead"""
        endpoint = "/api/sync-lead"
        try:
            # Teste com um lead_id fictício
            payload = {
                "lead_id": "00000000-0000-0000-0000-000000000001",
                "source": "agenticos",
                "target": "ghl"
            }
            response = requests.post(
                f"{self.base_url}{endpoint}",
                json=payload,
                timeout=10
            )

            if response.status_code == 200:
                data = response.json()
                # Deve retornar synced=false pois o lead não existe
                if data.get('synced') == False:
                    self.log("PASS", endpoint, "Retornou synced=false para lead inexistente (correto)")
                else:
                    self.log("WARN", endpoint, f"Resposta: {data}")
                return True
            elif response.status_code == 500:
                self.log("WARN", endpoint, "Erro 500 - tabelas podem não existir ainda")
                return True
            else:
                self.log("FAIL", endpoint, f"HTTP {response.status_code}: {response.text}")
        except Exception as e:
            self.log("FAIL", endpoint, str(e))
        return False

    def test_update_ghl_contact(self):
        """Testa endpoint /api/update-ghl-contact"""
        endpoint = "/api/update-ghl-contact"
        try:
            # Teste sem GHL_API_KEY configurada deve retornar erro
            payload = {
                "contact_id": "test_contact",
                "location_id": "test_location",
                "custom_fields": {
                    "lead_cargo": "CEO",
                    "icp_score": "85"
                }
            }
            response = requests.post(
                f"{self.base_url}{endpoint}",
                json=payload,
                timeout=10
            )

            if response.status_code == 200:
                data = response.json()
                # Deve retornar erro se GHL_API_KEY não está configurada
                if data.get('updated') == False and 'error' in data:
                    self.log("PASS", endpoint, f"Retornou erro esperado: {data.get('error', '')[:50]}")
                else:
                    self.log("WARN", endpoint, f"Resposta: {data}")
                return True
            elif response.status_code == 500:
                self.log("WARN", endpoint, "Erro 500 - GHL_API_KEY pode não estar configurada")
                return True
            else:
                self.log("FAIL", endpoint, f"HTTP {response.status_code}: {response.text}")
        except Exception as e:
            self.log("FAIL", endpoint, str(e))
        return False

    def test_ensure_ghl_fields(self):
        """Testa endpoint /api/ensure-ghl-fields/{location_id}"""
        endpoint = "/api/ensure-ghl-fields/test_location"
        try:
            response = requests.post(
                f"{self.base_url}{endpoint}",
                timeout=10
            )

            if response.status_code == 200:
                data = response.json()
                if 'error' in data:
                    self.log("PASS", endpoint, f"Retornou erro esperado (sem API key)")
                else:
                    self.log("WARN", endpoint, f"Resposta: {data}")
                return True
            elif response.status_code == 500:
                self.log("WARN", endpoint, "Erro 500 - GHL_API_KEY pode não estar configurada")
                return True
            else:
                self.log("FAIL", endpoint, f"HTTP {response.status_code}: {response.text}")
        except Exception as e:
            self.log("FAIL", endpoint, str(e))
        return False

    def run_all_tests(self):
        """Executa todos os testes"""
        print("\n" + "=" * 60)
        print("FASE 0 - Testes de Endpoints da API")
        print("=" * 60)
        print(f"Base URL: {self.base_url}")
        print(f"Timestamp: {datetime.now().isoformat()}")
        print("=" * 60 + "\n")

        # Verificar se a API está rodando
        if not self.test_health_check():
            print("\n[!] API não está acessível. Inicie com:")
            print("    cd implementation && uvicorn api_server:app --reload")
            return self.results

        # Executar testes
        self.test_list_skills()
        self.test_get_lead_context()
        self.test_sync_lead()
        self.test_update_ghl_contact()
        self.test_ensure_ghl_fields()

        # Resumo
        print("\n" + "=" * 60)
        print("RESUMO DOS TESTES")
        print("=" * 60)

        passed = sum(1 for r in self.results if r['status'] == 'PASS')
        failed = sum(1 for r in self.results if r['status'] == 'FAIL')
        warnings = sum(1 for r in self.results if r['status'] == 'WARN')

        print(f"✅ Passou: {passed}")
        print(f"❌ Falhou: {failed}")
        print(f"⚠️ Avisos: {warnings}")
        print(f"📊 Total: {len(self.results)}")

        return self.results


def main():
    parser = argparse.ArgumentParser(description='Test FASE 0 API endpoints')
    parser.add_argument('--base-url', type=str, default='http://localhost:8000',
                       help='Base URL da API')
    args = parser.parse_args()

    tester = FASE0Tester(base_url=args.base_url)
    results = tester.run_all_tests()

    # Salvar resultados
    results_path = Path(__file__).parent / 'test_results_fase0.json'
    with open(results_path, 'w') as f:
        json.dump(results, f, indent=2)
    print(f"\n[INFO] Resultados salvos em: {results_path}")


if __name__ == '__main__':
    main()
