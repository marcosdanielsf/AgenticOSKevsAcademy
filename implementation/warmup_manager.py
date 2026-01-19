"""
Warm-up Protocol Manager
========================
Gerencia aquecimento gradual de contas do Instagram para evitar bloqueios.

Contas novas ou que ficaram paradas precisam "aquecer" antes de enviar
muitas DMs. Este módulo implementa um protocolo de aquecimento progressivo.

ESTÁGIOS DO WARM-UP:
    Dia 1-3   (NEW):         5 DMs/dia   - Conta muito nova, cuidado máximo
    Dia 4-7   (WARMING):    15 DMs/dia   - Iniciando aquecimento
    Dia 8-14  (PROGRESSING): 30 DMs/dia  - Progredindo bem
    Dia 15+   (READY):       50 DMs/dia  - Conta aquecida, limite normal

AÇÕES COMPLEMENTARES (humanização):
    - Seguir 5-10 perfis relevantes/dia
    - Curtir 10-20 posts/dia
    - Ver stories
    - Postar 1x a cada 2-3 dias

REGRAS:
    1. Conta nova → inicia em NEW
    2. Conta parada 7+ dias → volta para WARMING
    3. Conta parada 30+ dias → volta para NEW
    4. Bloqueio detectado → volta 1 estágio

Usage:
    from warmup_manager import WarmupManager, WarmupStage

    warmup = WarmupManager()

    # Verificar estágio de uma conta
    stage = warmup.get_account_stage(account_id)
    daily_limit = warmup.get_daily_limit(account_id)

    # Iniciar warmup de conta nova
    warmup.start_warmup(account_id)

    # Verificar se conta está pronta
    if warmup.is_account_ready(account_id):
        # Pode usar limite normal
        pass
"""

import os
import logging
from datetime import datetime, timedelta, date
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from enum import Enum

import requests
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger("WarmupManager")

# Supabase config
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")


class WarmupStage(Enum):
    """Estágios do protocolo de aquecimento"""
    NEW = "new"              # Dia 1-3: 5 DMs/dia
    WARMING = "warming"      # Dia 4-7: 15 DMs/dia
    PROGRESSING = "progressing"  # Dia 8-14: 30 DMs/dia
    READY = "ready"          # Dia 15+: Limite normal


@dataclass
class WarmupStatus:
    """Status de aquecimento de uma conta"""
    account_id: int
    username: str
    stage: WarmupStage
    started_at: Optional[datetime]
    current_day: int  # Dia atual do warmup (1-14+)
    daily_limit: int  # Limite de DMs para hoje
    is_ready: bool  # True se warmup completo
    last_active_at: Optional[datetime]
    notes: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "account_id": self.account_id,
            "username": self.username,
            "stage": self.stage.value,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "current_day": self.current_day,
            "daily_limit": self.daily_limit,
            "is_ready": self.is_ready,
            "last_active_at": self.last_active_at.isoformat() if self.last_active_at else None,
            "notes": self.notes
        }


# Configuração dos estágios
WARMUP_CONFIG = {
    WarmupStage.NEW: {
        "days": (1, 3),
        "daily_limit": 5,
        "hourly_limit": 2,
        "description": "Conta nova - máximo cuidado"
    },
    WarmupStage.WARMING: {
        "days": (4, 7),
        "daily_limit": 15,
        "hourly_limit": 4,
        "description": "Iniciando aquecimento"
    },
    WarmupStage.PROGRESSING: {
        "days": (8, 14),
        "daily_limit": 30,
        "hourly_limit": 7,
        "description": "Progredindo bem"
    },
    WarmupStage.READY: {
        "days": (15, 999),
        "daily_limit": 50,
        "hourly_limit": 10,
        "description": "Conta aquecida - limite normal"
    }
}


class WarmupManager:
    """
    Gerencia o protocolo de warm-up de contas do Instagram.

    Responsabilidades:
    - Rastrear em que dia do warmup cada conta está
    - Calcular limite diário baseado no estágio
    - Detectar contas que voltaram de inatividade
    - Ajustar estágio após bloqueios
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

    def get_account_warmup(self, account_id: int) -> Optional[Dict[str, Any]]:
        """Busca dados de warmup de uma conta"""
        try:
            data = self._request("GET", "instagram_account_warmup", params={
                "account_id": f"eq.{account_id}",
                "select": "*"
            })
            return data[0] if data else None
        except Exception as e:
            logger.error(f"Erro ao buscar warmup: {e}")
            return None

    def start_warmup(self, account_id: int, username: str) -> WarmupStatus:
        """
        Inicia ou reinicia o warm-up de uma conta.

        Args:
            account_id: ID da conta no banco
            username: Username da conta

        Returns:
            WarmupStatus com o estado inicial
        """
        now = datetime.now()

        try:
            # Verifica se já existe registro
            existing = self.get_account_warmup(account_id)

            if existing:
                # Atualiza registro existente
                self._request("PATCH", "instagram_account_warmup",
                    params={"account_id": f"eq.{account_id}"},
                    data={
                        "warmup_started_at": now.isoformat(),
                        "stage": WarmupStage.NEW.value,
                        "last_active_at": now.isoformat(),
                        "is_ready": False,
                        "notes": f"Warmup reiniciado em {now.strftime('%Y-%m-%d')}"
                    }
                )
            else:
                # Cria novo registro
                self._request("POST", "instagram_account_warmup", data={
                    "account_id": account_id,
                    "username": username,
                    "warmup_started_at": now.isoformat(),
                    "stage": WarmupStage.NEW.value,
                    "last_active_at": now.isoformat(),
                    "is_ready": False,
                    "notes": f"Warmup iniciado em {now.strftime('%Y-%m-%d')}"
                })

            logger.info(f"🔥 Warm-up iniciado para @{username}")

            return WarmupStatus(
                account_id=account_id,
                username=username,
                stage=WarmupStage.NEW,
                started_at=now,
                current_day=1,
                daily_limit=WARMUP_CONFIG[WarmupStage.NEW]["daily_limit"],
                is_ready=False,
                last_active_at=now,
                notes="Warmup iniciado"
            )

        except Exception as e:
            logger.error(f"Erro ao iniciar warmup: {e}")
            # Retorna status padrão em caso de erro
            return WarmupStatus(
                account_id=account_id,
                username=username,
                stage=WarmupStage.NEW,
                started_at=now,
                current_day=1,
                daily_limit=WARMUP_CONFIG[WarmupStage.NEW]["daily_limit"],
                is_ready=False,
                last_active_at=now
            )

    def get_account_status(self, account_id: int, username: str = "") -> WarmupStatus:
        """
        Retorna o status atual de warmup de uma conta.

        Calcula automaticamente:
        - Em que dia do warmup está
        - Qual o estágio atual
        - Se precisa regredir por inatividade
        - Limite diário atual

        Args:
            account_id: ID da conta
            username: Username (opcional, para logs)

        Returns:
            WarmupStatus com todos os dados
        """
        warmup_data = self.get_account_warmup(account_id)

        # Se não tem registro, conta é nova
        if not warmup_data:
            logger.info(f"📝 Conta {account_id} sem warmup - iniciando...")
            return self.start_warmup(account_id, username)

        # Parse dados
        started_at = datetime.fromisoformat(warmup_data['warmup_started_at']) if warmup_data.get('warmup_started_at') else None
        last_active = datetime.fromisoformat(warmup_data['last_active_at']) if warmup_data.get('last_active_at') else None
        is_ready = warmup_data.get('is_ready', False)
        stored_stage = warmup_data.get('stage', 'new')
        username = warmup_data.get('username', username)

        now = datetime.now()

        # Verificar inatividade
        if last_active:
            days_inactive = (now - last_active).days

            if days_inactive >= 30:
                # Inativo 30+ dias → volta para NEW
                logger.warning(f"⚠️ @{username} inativa por {days_inactive} dias - voltando para NEW")
                return self.start_warmup(account_id, username)

            elif days_inactive >= 7 and is_ready:
                # Inativo 7+ dias → volta para WARMING
                logger.warning(f"⚠️ @{username} inativa por {days_inactive} dias - voltando para WARMING")
                self._set_stage(account_id, WarmupStage.WARMING)
                started_at = now - timedelta(days=3)  # Simula dia 4
                is_ready = False

        # Calcular dia atual do warmup
        if started_at:
            current_day = (now - started_at).days + 1
        else:
            current_day = 1

        # Determinar estágio baseado no dia
        stage = self._get_stage_for_day(current_day)

        # Se mudou de estágio, atualizar no banco
        if stage.value != stored_stage:
            self._set_stage(account_id, stage)

        # Marcar como ready se atingiu dia 15
        if current_day >= 15 and not is_ready:
            self._mark_ready(account_id)
            is_ready = True
            logger.info(f"✅ @{username} completou warm-up! Conta pronta.")

        # Atualizar last_active
        self._update_last_active(account_id)

        config = WARMUP_CONFIG[stage]

        return WarmupStatus(
            account_id=account_id,
            username=username,
            stage=stage,
            started_at=started_at,
            current_day=current_day,
            daily_limit=config["daily_limit"],
            is_ready=is_ready,
            last_active_at=now,
            notes=config["description"]
        )

    def get_daily_limit(self, account_id: int, username: str = "") -> int:
        """
        Retorna o limite diário de DMs para uma conta.

        Considera:
        - Estágio atual do warmup
        - Limites configurados
        - Limite base da conta (se maior que warmup, usa warmup)

        Args:
            account_id: ID da conta
            username: Username (opcional)

        Returns:
            Limite de DMs para hoje
        """
        status = self.get_account_status(account_id, username)
        return status.daily_limit

    def get_hourly_limit(self, account_id: int, username: str = "") -> int:
        """Retorna limite por hora baseado no estágio"""
        status = self.get_account_status(account_id, username)
        config = WARMUP_CONFIG[status.stage]
        return config["hourly_limit"]

    def is_account_ready(self, account_id: int) -> bool:
        """Verifica se conta completou o warm-up"""
        warmup_data = self.get_account_warmup(account_id)
        return warmup_data.get('is_ready', False) if warmup_data else False

    def handle_block_detected(self, account_id: int, block_type: str = "unknown"):
        """
        Ajusta warmup quando um bloqueio é detectado.

        Estratégia:
        - Bloqueio leve (rate_limit): não muda estágio, só pausa
        - Bloqueio médio (action_blocked): volta 1 estágio
        - Bloqueio grave (checkpoint): volta para NEW

        Args:
            account_id: ID da conta
            block_type: Tipo de bloqueio detectado
        """
        status = self.get_account_status(account_id)
        current_stage = status.stage

        # Determinar novo estágio
        if block_type in ['checkpoint', 'account_disabled', 'suspicious_activity']:
            # Bloqueio grave → volta para NEW
            new_stage = WarmupStage.NEW
            logger.warning(f"⛔ Bloqueio grave ({block_type}) - voltando @{status.username} para NEW")

        elif block_type in ['action_blocked', 'two_factor']:
            # Bloqueio médio → volta 1 estágio
            stage_order = [WarmupStage.NEW, WarmupStage.WARMING, WarmupStage.PROGRESSING, WarmupStage.READY]
            current_idx = stage_order.index(current_stage)
            new_idx = max(0, current_idx - 1)
            new_stage = stage_order[new_idx]
            logger.warning(f"⚠️ Bloqueio ({block_type}) - voltando @{status.username} para {new_stage.value}")

        else:
            # Bloqueio leve → mantém estágio
            new_stage = current_stage
            logger.info(f"⏸️ Bloqueio leve ({block_type}) - mantendo estágio de @{status.username}")

        # Atualizar no banco
        if new_stage != current_stage:
            self._set_stage(account_id, new_stage)
            self._request("PATCH", "instagram_account_warmup",
                params={"account_id": f"eq.{account_id}"},
                data={
                    "is_ready": False,
                    "warmup_started_at": datetime.now().isoformat() if new_stage == WarmupStage.NEW else None,
                    "notes": f"Regredido para {new_stage.value} após {block_type}"
                }
            )

    def _get_stage_for_day(self, day: int) -> WarmupStage:
        """Determina estágio baseado no dia do warmup"""
        for stage, config in WARMUP_CONFIG.items():
            min_day, max_day = config["days"]
            if min_day <= day <= max_day:
                return stage
        return WarmupStage.READY

    def _set_stage(self, account_id: int, stage: WarmupStage):
        """Atualiza estágio no banco"""
        try:
            self._request("PATCH", "instagram_account_warmup",
                params={"account_id": f"eq.{account_id}"},
                data={"stage": stage.value}
            )
        except Exception as e:
            logger.error(f"Erro ao atualizar estágio: {e}")

    def _mark_ready(self, account_id: int):
        """Marca conta como pronta (warmup completo)"""
        try:
            self._request("PATCH", "instagram_account_warmup",
                params={"account_id": f"eq.{account_id}"},
                data={
                    "is_ready": True,
                    "stage": WarmupStage.READY.value,
                    "notes": f"Warmup completo em {datetime.now().strftime('%Y-%m-%d')}"
                }
            )
        except Exception as e:
            logger.error(f"Erro ao marcar ready: {e}")

    def mark_account_ready(self, account_id: int, username: str) -> WarmupStatus:
        """
        Marca conta como "ready" imediatamente (pula warm-up).

        Use para contas maduras que já existem há muito tempo
        e não precisam passar pelos 15 dias de aquecimento.

        Args:
            account_id: ID da conta no banco
            username: Username da conta

        Returns:
            WarmupStatus com stage=READY
        """
        now = datetime.now()

        try:
            # Verifica se já existe registro
            existing = self.get_account_warmup(account_id)

            data = {
                "warmup_started_at": (now - timedelta(days=30)).isoformat(),  # Simula 30 dias atrás
                "stage": WarmupStage.READY.value,
                "last_active_at": now.isoformat(),
                "is_ready": True,
                "notes": f"Conta madura - warmup pulado em {now.strftime('%Y-%m-%d')}"
            }

            if existing:
                self._request("PATCH", "instagram_account_warmup",
                    params={"account_id": f"eq.{account_id}"},
                    data=data
                )
            else:
                data["account_id"] = account_id
                data["username"] = username
                self._request("POST", "instagram_account_warmup", data=data)

            logger.info(f"✅ @{username} marcada como ready (conta madura)")

            return WarmupStatus(
                account_id=account_id,
                username=username,
                stage=WarmupStage.READY,
                started_at=now - timedelta(days=30),
                current_day=30,
                daily_limit=WARMUP_CONFIG[WarmupStage.READY]["daily_limit"],
                is_ready=True,
                last_active_at=now,
                notes="Conta madura - warmup pulado"
            )

        except Exception as e:
            logger.error(f"Erro ao marcar conta como ready: {e}")
            return WarmupStatus(
                account_id=account_id,
                username=username,
                stage=WarmupStage.READY,
                started_at=now,
                current_day=30,
                daily_limit=WARMUP_CONFIG[WarmupStage.READY]["daily_limit"],
                is_ready=True,
                last_active_at=now
            )

    def _update_last_active(self, account_id: int):
        """Atualiza timestamp de última atividade"""
        try:
            self._request("PATCH", "instagram_account_warmup",
                params={"account_id": f"eq.{account_id}"},
                data={"last_active_at": datetime.now().isoformat()}
            )
        except Exception as e:
            # Não loga erro para não poluir - operação não crítica
            pass

    def get_all_accounts_status(self, tenant_id: str = None) -> List[WarmupStatus]:
        """Retorna status de warmup de todas as contas (ou de um tenant)"""
        try:
            params = {"select": "*"}
            if tenant_id:
                # Precisa fazer join com instagram_accounts
                # Por simplicidade, busca todos e filtra
                pass

            data = self._request("GET", "instagram_account_warmup", params=params)

            statuses = []
            for row in data:
                status = self.get_account_status(row['account_id'], row.get('username', ''))
                statuses.append(status)

            return statuses

        except Exception as e:
            logger.error(f"Erro ao buscar status de contas: {e}")
            return []

    def get_warmup_summary(self) -> Dict[str, Any]:
        """Retorna resumo do warmup de todas as contas"""
        try:
            statuses = self.get_all_accounts_status()

            summary = {
                "total_accounts": len(statuses),
                "by_stage": {
                    "new": 0,
                    "warming": 0,
                    "progressing": 0,
                    "ready": 0
                },
                "accounts": []
            }

            for status in statuses:
                summary["by_stage"][status.stage.value] += 1
                summary["accounts"].append({
                    "username": status.username,
                    "stage": status.stage.value,
                    "day": status.current_day,
                    "limit": status.daily_limit,
                    "ready": status.is_ready
                })

            return summary

        except Exception as e:
            logger.error(f"Erro ao gerar resumo: {e}")
            return {"error": str(e)}


# ==============================================
# MIGRATION SQL
# ==============================================

MIGRATION_SQL = """
-- Tabela de warmup de contas Instagram
-- Execute este SQL no Supabase SQL Editor

CREATE TABLE IF NOT EXISTS instagram_account_warmup (
    id SERIAL PRIMARY KEY,
    account_id INTEGER NOT NULL UNIQUE REFERENCES instagram_accounts(id) ON DELETE CASCADE,
    username TEXT NOT NULL,
    warmup_started_at TIMESTAMPTZ DEFAULT NOW(),
    stage TEXT DEFAULT 'new' CHECK (stage IN ('new', 'warming', 'progressing', 'ready')),
    last_active_at TIMESTAMPTZ DEFAULT NOW(),
    is_ready BOOLEAN DEFAULT FALSE,
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Índices para performance
CREATE INDEX IF NOT EXISTS idx_warmup_account_id ON instagram_account_warmup(account_id);
CREATE INDEX IF NOT EXISTS idx_warmup_stage ON instagram_account_warmup(stage);
CREATE INDEX IF NOT EXISTS idx_warmup_is_ready ON instagram_account_warmup(is_ready);

-- Trigger para updated_at
CREATE OR REPLACE FUNCTION update_warmup_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trigger_warmup_updated_at ON instagram_account_warmup;
CREATE TRIGGER trigger_warmup_updated_at
    BEFORE UPDATE ON instagram_account_warmup
    FOR EACH ROW
    EXECUTE FUNCTION update_warmup_timestamp();

-- Comentários
COMMENT ON TABLE instagram_account_warmup IS 'Rastreia o warm-up de contas Instagram para evitar bloqueios';
COMMENT ON COLUMN instagram_account_warmup.stage IS 'Estágio: new (1-3d), warming (4-7d), progressing (8-14d), ready (15+d)';
COMMENT ON COLUMN instagram_account_warmup.is_ready IS 'True quando warmup completo (dia 15+)';
"""


def print_migration():
    """Imprime SQL de migration para copiar no Supabase"""
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
        # Teste básico
        print("Warm-up Manager - Teste")
        print("-" * 40)

        manager = WarmupManager()
        summary = manager.get_warmup_summary()
        print(f"Contas rastreadas: {summary.get('total_accounts', 0)}")
        print(f"Por estágio: {summary.get('by_stage', {})}")

        print("\nPara gerar migration SQL:")
        print("  python warmup_manager.py --migration")
