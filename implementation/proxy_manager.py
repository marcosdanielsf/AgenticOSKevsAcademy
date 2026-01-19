"""
Proxy Manager - Gerenciamento de Proxies por Tenant
====================================================
Cada cliente/tenant pode ter seu próprio proxy configurado,
preferencialmente no mesmo país/região para evitar detecção.

BENEFÍCIOS:
    - IP consistente com a localização do cliente
    - Evita detecção por mudança brusca de IP
    - Permite escalar sem sobrecarregar um IP
    - Fallback automático se proxy falhar

TIPOS DE PROXY SUPORTADOS:
    - HTTP/HTTPS
    - SOCKS5
    - Residential (recomendado para Instagram)
    - Datacenter (mais barato, mais arriscado)

PROVIDERS RECOMENDADOS:
    - Bright Data (residential)
    - Smartproxy (residential)
    - IPRoyal (residential)
    - Oxylabs (premium)

Usage:
    from proxy_manager import ProxyManager

    proxy_mgr = ProxyManager()

    # Buscar proxy para um tenant
    proxy = proxy_mgr.get_proxy_for_tenant("dr_alberto")

    # Usar no Playwright
    browser = await playwright.chromium.launch(proxy=proxy.to_playwright())

    # Marcar proxy como falho
    proxy_mgr.mark_proxy_failed(proxy.id, "Connection timeout")
"""

import os
import logging
import random
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from dataclasses import dataclass
from enum import Enum

import requests
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger("ProxyManager")

# Supabase config
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")


class ProxyType(Enum):
    """Tipos de proxy suportados"""
    HTTP = "http"
    HTTPS = "https"
    SOCKS5 = "socks5"


class ProxyProvider(Enum):
    """Providers de proxy conhecidos"""
    BRIGHTDATA = "brightdata"
    SMARTPROXY = "smartproxy"
    IPROYAL = "iproyal"
    OXYLABS = "oxylabs"
    CUSTOM = "custom"


@dataclass
class ProxyConfig:
    """Configuração de um proxy"""
    id: int
    tenant_id: str
    name: str
    host: str
    port: int
    username: Optional[str] = None
    password: Optional[str] = None
    proxy_type: ProxyType = ProxyType.HTTP
    provider: ProxyProvider = ProxyProvider.CUSTOM
    country: Optional[str] = None  # BR, US, etc
    city: Optional[str] = None
    is_residential: bool = False
    is_active: bool = True
    last_used_at: Optional[datetime] = None
    last_failed_at: Optional[datetime] = None
    fail_count: int = 0
    success_count: int = 0

    @property
    def url(self) -> str:
        """Retorna URL completa do proxy"""
        auth = ""
        if self.username and self.password:
            auth = f"{self.username}:{self.password}@"

        protocol = self.proxy_type.value
        return f"{protocol}://{auth}{self.host}:{self.port}"

    @property
    def is_healthy(self) -> bool:
        """Verifica se proxy está saudável"""
        if not self.is_active:
            return False
        # Se falhou mais de 3 vezes nas últimas 24h, considera não saudável
        if self.fail_count >= 3 and self.last_failed_at:
            if datetime.now() - self.last_failed_at < timedelta(hours=24):
                return False
        return True

    @property
    def success_rate(self) -> float:
        """Taxa de sucesso do proxy"""
        total = self.success_count + self.fail_count
        if total == 0:
            return 1.0
        return self.success_count / total

    def to_playwright(self) -> Dict[str, Any]:
        """
        Retorna configuração para usar no Playwright.

        Usage:
            browser = await playwright.chromium.launch(
                proxy=proxy.to_playwright()
            )
        """
        config = {
            "server": f"{self.proxy_type.value}://{self.host}:{self.port}"
        }
        if self.username and self.password:
            config["username"] = self.username
            config["password"] = self.password
        return config

    def to_requests(self) -> Dict[str, str]:
        """
        Retorna configuração para usar com requests/httpx.

        Usage:
            response = requests.get(url, proxies=proxy.to_requests())
        """
        return {
            "http": self.url,
            "https": self.url
        }


class ProxyManager:
    """
    Gerencia proxies para automação do Instagram.

    Responsabilidades:
    - Armazenar proxies por tenant
    - Rotacionar entre proxies disponíveis
    - Marcar proxies que falharam
    - Reativar proxies após período de cooldown
    """

    def __init__(self):
        self.base_url = f"{SUPABASE_URL}/rest/v1"
        self.headers = {
            "apikey": SUPABASE_KEY,
            "Authorization": f"Bearer {SUPABASE_KEY}",
            "Content-Type": "application/json",
            "Prefer": "return=representation"
        }

    def _request(self, method: str, endpoint: str, params: dict = None, data: dict = None) -> Any:
        """Make request to Supabase REST API"""
        url = f"{self.base_url}/{endpoint}"
        response = requests.request(
            method=method,
            url=url,
            headers=self.headers,
            params=params,
            json=data,
            timeout=30
        )
        response.raise_for_status()
        return response.json() if response.text else []

    def get_proxy_for_tenant(self, tenant_id: str) -> Optional[ProxyConfig]:
        """
        Busca o melhor proxy disponível para um tenant.

        Prioridade:
        1. Proxy específico do tenant (se configurado)
        2. Proxy do mesmo país do tenant
        3. Proxy global disponível

        Args:
            tenant_id: ID do tenant

        Returns:
            ProxyConfig ou None se não houver proxy disponível
        """
        try:
            # 1. Buscar proxy específico do tenant
            data = self._request("GET", "instagram_proxies", params={
                "tenant_id": f"eq.{tenant_id}",
                "is_active": "eq.true",
                "select": "*",
                "order": "success_count.desc"
            })

            if data:
                proxy = self._row_to_proxy(data[0])
                if proxy.is_healthy:
                    logger.info(f"🌐 Proxy específico para {tenant_id}: {proxy.host}:{proxy.port}")
                    return proxy

            # 2. Buscar proxy global (tenant_id = 'global')
            data = self._request("GET", "instagram_proxies", params={
                "tenant_id": "eq.global",
                "is_active": "eq.true",
                "select": "*",
                "order": "last_used_at.asc.nullsfirst"
            })

            if data:
                # Filtrar proxies saudáveis
                healthy_proxies = [self._row_to_proxy(row) for row in data]
                healthy_proxies = [p for p in healthy_proxies if p.is_healthy]

                if healthy_proxies:
                    # Escolher o menos usado recentemente
                    proxy = healthy_proxies[0]
                    logger.info(f"🌐 Proxy global para {tenant_id}: {proxy.host}:{proxy.port}")
                    return proxy

            logger.warning(f"⚠️ Nenhum proxy disponível para tenant {tenant_id}")
            return None

        except Exception as e:
            logger.error(f"Erro ao buscar proxy: {e}")
            return None

    def get_proxy_for_account(self, account_id: int) -> Optional[ProxyConfig]:
        """
        Busca proxy vinculado diretamente a uma conta específica.

        Útil quando cada conta do Instagram tem seu próprio proxy.
        """
        try:
            data = self._request("GET", "instagram_proxies", params={
                "account_id": f"eq.{account_id}",
                "is_active": "eq.true",
                "select": "*"
            })

            if data:
                proxy = self._row_to_proxy(data[0])
                if proxy.is_healthy:
                    return proxy

            return None

        except Exception as e:
            logger.error(f"Erro ao buscar proxy para conta {account_id}: {e}")
            return None

    def get_all_proxies(self, tenant_id: str = None, only_healthy: bool = True) -> List[ProxyConfig]:
        """Lista todos os proxies (opcionalmente filtrado por tenant)"""
        try:
            params = {"select": "*"}
            if tenant_id:
                params["tenant_id"] = f"eq.{tenant_id}"
            if only_healthy:
                params["is_active"] = "eq.true"

            data = self._request("GET", "instagram_proxies", params=params)

            proxies = [self._row_to_proxy(row) for row in data]
            if only_healthy:
                proxies = [p for p in proxies if p.is_healthy]

            return proxies

        except Exception as e:
            logger.error(f"Erro ao listar proxies: {e}")
            return []

    def add_proxy(
        self,
        tenant_id: str,
        host: str,
        port: int,
        name: str = None,
        username: str = None,
        password: str = None,
        proxy_type: str = "http",
        provider: str = "custom",
        country: str = None,
        city: str = None,
        is_residential: bool = False,
        account_id: int = None
    ) -> Optional[int]:
        """
        Adiciona um novo proxy ao sistema.

        Args:
            tenant_id: ID do tenant (ou 'global' para proxy compartilhado)
            host: Hostname ou IP do proxy
            port: Porta do proxy
            name: Nome amigável (opcional)
            username: Usuário para autenticação
            password: Senha para autenticação
            proxy_type: http, https ou socks5
            provider: brightdata, smartproxy, iproyal, oxylabs, custom
            country: Código do país (BR, US, etc)
            city: Cidade (opcional)
            is_residential: Se é proxy residential (melhor para Instagram)
            account_id: Vincular a uma conta específica (opcional)

        Returns:
            ID do proxy criado ou None
        """
        try:
            data = {
                "tenant_id": tenant_id,
                "name": name or f"{host}:{port}",
                "host": host,
                "port": port,
                "proxy_type": proxy_type,
                "provider": provider,
                "is_active": True,
                "fail_count": 0,
                "success_count": 0
            }

            if username:
                data["username"] = username
            if password:
                data["password"] = password
            if country:
                data["country"] = country
            if city:
                data["city"] = city
            if is_residential:
                data["is_residential"] = is_residential
            if account_id:
                data["account_id"] = account_id

            result = self._request("POST", "instagram_proxies", data=data)

            if result:
                proxy_id = result[0]['id']
                logger.info(f"✅ Proxy adicionado: {host}:{port} para {tenant_id}")
                return proxy_id

            return None

        except Exception as e:
            logger.error(f"Erro ao adicionar proxy: {e}")
            return None

    def record_success(self, proxy_id: int):
        """Registra uso bem-sucedido do proxy"""
        try:
            # Buscar contagem atual
            data = self._request("GET", "instagram_proxies", params={
                "id": f"eq.{proxy_id}",
                "select": "success_count"
            })

            current_count = data[0]['success_count'] if data else 0

            self._request("PATCH", "instagram_proxies",
                params={"id": f"eq.{proxy_id}"},
                data={
                    "success_count": current_count + 1,
                    "last_used_at": datetime.now().isoformat()
                }
            )
        except Exception as e:
            logger.error(f"Erro ao registrar sucesso: {e}")

    def mark_proxy_failed(self, proxy_id: int, reason: str = None):
        """
        Marca proxy como falho.

        Após 3 falhas em 24h, proxy é considerado não saudável.
        """
        try:
            # Buscar contagem atual
            data = self._request("GET", "instagram_proxies", params={
                "id": f"eq.{proxy_id}",
                "select": "fail_count"
            })

            current_count = data[0]['fail_count'] if data else 0
            new_count = current_count + 1

            update_data = {
                "fail_count": new_count,
                "last_failed_at": datetime.now().isoformat()
            }

            # Se muitas falhas, desativar temporariamente
            if new_count >= 5:
                update_data["is_active"] = False
                logger.warning(f"⛔ Proxy {proxy_id} desativado após {new_count} falhas")

            if reason:
                update_data["notes"] = f"Última falha: {reason}"

            self._request("PATCH", "instagram_proxies",
                params={"id": f"eq.{proxy_id}"},
                data=update_data
            )

            logger.warning(f"⚠️ Proxy {proxy_id} falhou: {reason}")

        except Exception as e:
            logger.error(f"Erro ao marcar falha: {e}")

    def reactivate_proxy(self, proxy_id: int):
        """Reativa um proxy que foi desativado"""
        try:
            self._request("PATCH", "instagram_proxies",
                params={"id": f"eq.{proxy_id}"},
                data={
                    "is_active": True,
                    "fail_count": 0,
                    "notes": f"Reativado em {datetime.now().strftime('%Y-%m-%d %H:%M')}"
                }
            )
            logger.info(f"✅ Proxy {proxy_id} reativado")
        except Exception as e:
            logger.error(f"Erro ao reativar proxy: {e}")

    def test_proxy(self, proxy: ProxyConfig, timeout: int = 10) -> bool:
        """
        Testa se um proxy está funcionando.

        Faz uma requisição simples para verificar conectividade.
        """
        try:
            test_url = "https://api.ipify.org?format=json"
            response = requests.get(
                test_url,
                proxies=proxy.to_requests(),
                timeout=timeout
            )

            if response.status_code == 200:
                ip = response.json().get('ip', 'unknown')
                logger.info(f"✅ Proxy {proxy.host}:{proxy.port} funcionando (IP: {ip})")
                self.record_success(proxy.id)
                return True
            else:
                logger.warning(f"⚠️ Proxy retornou status {response.status_code}")
                return False

        except Exception as e:
            logger.error(f"❌ Proxy {proxy.host}:{proxy.port} falhou: {e}")
            self.mark_proxy_failed(proxy.id, str(e))
            return False

    def get_proxy_stats(self, tenant_id: str = None) -> Dict[str, Any]:
        """Retorna estatísticas dos proxies"""
        proxies = self.get_all_proxies(tenant_id, only_healthy=False)

        total = len(proxies)
        active = len([p for p in proxies if p.is_active])
        healthy = len([p for p in proxies if p.is_healthy])
        residential = len([p for p in proxies if p.is_residential])

        by_country = {}
        for p in proxies:
            country = p.country or "unknown"
            by_country[country] = by_country.get(country, 0) + 1

        return {
            "total": total,
            "active": active,
            "healthy": healthy,
            "residential": residential,
            "by_country": by_country,
            "proxies": [
                {
                    "id": p.id,
                    "name": p.name,
                    "host": p.host,
                    "port": p.port,
                    "country": p.country,
                    "is_healthy": p.is_healthy,
                    "success_rate": round(p.success_rate * 100, 1),
                    "is_residential": p.is_residential
                }
                for p in proxies
            ]
        }

    def _row_to_proxy(self, row: Dict) -> ProxyConfig:
        """Converte row do banco para ProxyConfig"""
        return ProxyConfig(
            id=row['id'],
            tenant_id=row['tenant_id'],
            name=row.get('name', ''),
            host=row['host'],
            port=row['port'],
            username=row.get('username'),
            password=row.get('password'),
            proxy_type=ProxyType(row.get('proxy_type', 'http')),
            provider=ProxyProvider(row.get('provider', 'custom')),
            country=row.get('country'),
            city=row.get('city'),
            is_residential=row.get('is_residential', False),
            is_active=row.get('is_active', True),
            last_used_at=datetime.fromisoformat(row['last_used_at']) if row.get('last_used_at') else None,
            last_failed_at=datetime.fromisoformat(row['last_failed_at']) if row.get('last_failed_at') else None,
            fail_count=row.get('fail_count', 0),
            success_count=row.get('success_count', 0)
        )


# ==============================================
# PROXY ROTATION PARA CAMPANHAS
# ==============================================

class ProxyRotator:
    """
    Rotaciona entre proxies durante uma campanha.

    Útil quando você tem múltiplos proxies e quer distribuir
    as requisições entre eles.
    """

    def __init__(self, tenant_id: str):
        self.tenant_id = tenant_id
        self.manager = ProxyManager()
        self.proxies: List[ProxyConfig] = []
        self.current_index = 0
        self._refresh_proxies()

    def _refresh_proxies(self):
        """Atualiza lista de proxies disponíveis"""
        self.proxies = self.manager.get_all_proxies(self.tenant_id, only_healthy=True)

        # Adicionar proxies globais se não tiver específicos
        if not self.proxies:
            self.proxies = self.manager.get_all_proxies("global", only_healthy=True)

        if self.proxies:
            logger.info(f"🔄 ProxyRotator: {len(self.proxies)} proxies disponíveis")
        else:
            logger.warning(f"⚠️ ProxyRotator: Nenhum proxy disponível para {self.tenant_id}")

    def get_next_proxy(self) -> Optional[ProxyConfig]:
        """Retorna o próximo proxy na rotação"""
        if not self.proxies:
            self._refresh_proxies()
            if not self.proxies:
                return None

        proxy = self.proxies[self.current_index]
        self.current_index = (self.current_index + 1) % len(self.proxies)

        return proxy

    def remove_proxy(self, proxy_id: int):
        """Remove proxy da rotação (ex: após falha)"""
        self.proxies = [p for p in self.proxies if p.id != proxy_id]
        if self.current_index >= len(self.proxies):
            self.current_index = 0


# ==============================================
# MIGRATION SQL
# ==============================================

MIGRATION_SQL = """
-- Tabela de proxies para Instagram
-- Execute no Supabase SQL Editor

CREATE TABLE IF NOT EXISTS instagram_proxies (
    id SERIAL PRIMARY KEY,
    tenant_id TEXT NOT NULL,  -- 'global' para proxy compartilhado
    account_id INTEGER REFERENCES instagram_accounts(id) ON DELETE SET NULL,
    name TEXT,
    host TEXT NOT NULL,
    port INTEGER NOT NULL,
    username TEXT,
    password TEXT,
    proxy_type TEXT DEFAULT 'http' CHECK (proxy_type IN ('http', 'https', 'socks5')),
    provider TEXT DEFAULT 'custom' CHECK (provider IN ('brightdata', 'smartproxy', 'iproyal', 'oxylabs', 'custom')),
    country TEXT,  -- BR, US, etc
    city TEXT,
    is_residential BOOLEAN DEFAULT FALSE,
    is_active BOOLEAN DEFAULT TRUE,
    last_used_at TIMESTAMPTZ,
    last_failed_at TIMESTAMPTZ,
    fail_count INTEGER DEFAULT 0,
    success_count INTEGER DEFAULT 0,
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    UNIQUE(host, port, tenant_id)
);

-- Índices
CREATE INDEX IF NOT EXISTS idx_proxies_tenant ON instagram_proxies(tenant_id);
CREATE INDEX IF NOT EXISTS idx_proxies_account ON instagram_proxies(account_id);
CREATE INDEX IF NOT EXISTS idx_proxies_active ON instagram_proxies(is_active);
CREATE INDEX IF NOT EXISTS idx_proxies_country ON instagram_proxies(country);

-- Trigger para updated_at
CREATE OR REPLACE FUNCTION update_proxy_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trigger_proxy_updated_at ON instagram_proxies;
CREATE TRIGGER trigger_proxy_updated_at
    BEFORE UPDATE ON instagram_proxies
    FOR EACH ROW
    EXECUTE FUNCTION update_proxy_timestamp();

-- Comentários
COMMENT ON TABLE instagram_proxies IS 'Proxies para automação do Instagram por tenant';
COMMENT ON COLUMN instagram_proxies.tenant_id IS 'ID do tenant ou "global" para proxy compartilhado';
COMMENT ON COLUMN instagram_proxies.is_residential IS 'Proxies residential são melhores para Instagram';
"""


def print_migration():
    """Imprime SQL de migration"""
    print("=" * 60)
    print("MIGRATION SQL - Execute no Supabase SQL Editor")
    print("=" * 60)
    print(MIGRATION_SQL)
    print("=" * 60)


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "--migration":
        print_migration()
    else:
        print("Proxy Manager")
        print("-" * 40)
        print("\nPara gerar migration SQL:")
        print("  python proxy_manager.py --migration")
