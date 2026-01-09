#!/usr/bin/env python3
"""
🔄 INSTAGRAM SESSION POOL
=========================
Gerencia pool de sessions do Instagram para scraping escalável.

Features:
- Round-robin automático entre sessions
- Health check e degradação automática
- Rate limiting por conta
- Recuperação automática de sessions bloqueadas
- Fallback para session única (env var)

Uso:
    from instagram_session_pool import SessionPool

    pool = SessionPool()
    session = pool.get_session()
    # usar session.session_id para requests
    pool.report_result(session.id, success=True)
"""

import os
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, List
from dataclasses import dataclass
from supabase import create_client, Client

logger = logging.getLogger(__name__)


@dataclass
class Session:
    """Representa uma session do pool"""
    id: str
    username: str
    session_id: str
    requests_today: int
    health_score: int
    daily_limit: int = 200


class SessionPool:
    """
    Gerenciador de pool de sessions do Instagram.

    Usa Supabase para persistir estado e coordenar
    entre múltiplas instâncias do scraper.
    """

    def __init__(self, supabase_url: str = None, supabase_key: str = None):
        """
        Inicializa o pool de sessions.

        Args:
            supabase_url: URL do Supabase (default: env SUPABASE_URL)
            supabase_key: Service role key (default: env SUPABASE_SERVICE_ROLE_KEY)
        """
        self.supabase_url = supabase_url or os.getenv("SUPABASE_URL")
        self.supabase_key = supabase_key or os.getenv("SUPABASE_SERVICE_ROLE_KEY")

        self.client: Optional[Client] = None
        self._fallback_session_id = os.getenv("INSTAGRAM_SESSION_ID")
        self._pool_available = False

        # Tentar conectar ao Supabase
        if self.supabase_url and self.supabase_key:
            try:
                self.client = create_client(self.supabase_url, self.supabase_key)
                self._pool_available = self._check_pool_table()
                if self._pool_available:
                    logger.info("SessionPool: Conectado ao Supabase, pool disponível")
                else:
                    logger.warning("SessionPool: Tabela não existe, usando fallback")
            except Exception as e:
                logger.warning(f"SessionPool: Erro ao conectar Supabase: {e}")
        else:
            logger.info("SessionPool: Supabase não configurado, usando fallback")

    def _check_pool_table(self) -> bool:
        """Verifica se a tabela de sessions existe"""
        try:
            result = self.client.table("instagram_sessions") \
                .select("id") \
                .limit(1) \
                .execute()
            return True
        except Exception as e:
            logger.debug(f"Tabela instagram_sessions não existe: {e}")
            return False

    def get_session(self) -> Optional[Session]:
        """
        Obtém próxima session disponível do pool.

        Usa round-robin com health check:
        1. Prioriza sessions menos usadas hoje
        2. Prioriza sessions com maior health_score
        3. Evita sessions rate limited ou bloqueadas

        Returns:
            Session object ou None se não houver sessions disponíveis
        """
        # Se pool disponível, usar
        if self._pool_available and self.client:
            try:
                # Chamar função do banco que faz round-robin
                result = self.client.rpc("get_next_available_session").execute()

                if result.data and len(result.data) > 0:
                    row = result.data[0]
                    return Session(
                        id=row["id"],
                        username=row["username"],
                        session_id=row["session_id"],
                        requests_today=row["requests_today"],
                        health_score=row["health_score"]
                    )

                logger.warning("SessionPool: Nenhuma session disponível no pool")

            except Exception as e:
                logger.error(f"SessionPool: Erro ao obter session: {e}")

        # Fallback para session única do env
        if self._fallback_session_id:
            logger.info("SessionPool: Usando session fallback (env)")
            return Session(
                id="fallback",
                username="env_session",
                session_id=self._fallback_session_id,
                requests_today=0,
                health_score=100
            )

        return None

    def report_result(
        self,
        session_id: str,
        operation: str,
        target_username: str = None,
        success: bool = True,
        response_status: int = None,
        error_message: str = None,
        duration_ms: int = None
    ):
        """
        Reporta resultado de uma operação com a session.

        Atualiza contadores, health score e status da session
        baseado no resultado.

        Args:
            session_id: ID da session (UUID)
            operation: Tipo de operação (scrape_profile, get_followers, etc)
            target_username: Username alvo da operação
            success: Se a operação foi bem sucedida
            response_status: Status HTTP da resposta
            error_message: Mensagem de erro (se houver)
            duration_ms: Duração da operação em ms
        """
        # Fallback session não precisa reportar
        if session_id == "fallback":
            return

        if not self._pool_available or not self.client:
            return

        try:
            self.client.rpc(
                "record_session_usage",
                {
                    "p_session_id": session_id,
                    "p_operation": operation,
                    "p_target_username": target_username,
                    "p_success": success,
                    "p_response_status": response_status,
                    "p_error_message": error_message,
                    "p_duration_ms": duration_ms
                }
            ).execute()

        except Exception as e:
            logger.error(f"SessionPool: Erro ao reportar resultado: {e}")

    def add_session(
        self,
        username: str,
        session_id: str,
        daily_limit: int = 200,
        notes: str = None
    ) -> Optional[str]:
        """
        Adiciona nova session ao pool.

        Args:
            username: Username da conta Instagram
            session_id: Session ID (cookie sessionid)
            daily_limit: Limite diário de requests
            notes: Notas/observações sobre a conta

        Returns:
            ID da session criada ou None se falhar
        """
        if not self._pool_available or not self.client:
            logger.error("SessionPool: Pool não disponível para adicionar session")
            return None

        try:
            result = self.client.table("instagram_sessions").insert({
                "username": username,
                "session_id": session_id,
                "daily_limit": daily_limit,
                "notes": notes,
                "status": "active",
                "health_score": 100
            }).execute()

            if result.data:
                session_uuid = result.data[0]["id"]
                logger.info(f"SessionPool: Session adicionada - @{username} ({session_uuid})")
                return session_uuid

        except Exception as e:
            logger.error(f"SessionPool: Erro ao adicionar session: {e}")

        return None

    def remove_session(self, session_id: str) -> bool:
        """
        Remove session do pool.

        Args:
            session_id: ID (UUID) da session

        Returns:
            True se removida com sucesso
        """
        if not self._pool_available or not self.client:
            return False

        try:
            self.client.table("instagram_sessions") \
                .delete() \
                .eq("id", session_id) \
                .execute()

            logger.info(f"SessionPool: Session removida - {session_id}")
            return True

        except Exception as e:
            logger.error(f"SessionPool: Erro ao remover session: {e}")
            return False

    def update_session(
        self,
        session_id: str,
        new_session_id: str = None,
        status: str = None,
        daily_limit: int = None,
        notes: str = None
    ) -> bool:
        """
        Atualiza dados de uma session.

        Args:
            session_id: ID (UUID) da session
            new_session_id: Novo session_id (cookie)
            status: Novo status (active, rate_limited, blocked, expired)
            daily_limit: Novo limite diário
            notes: Novas notas

        Returns:
            True se atualizada com sucesso
        """
        if not self._pool_available or not self.client:
            return False

        try:
            update_data = {"updated_at": datetime.now().isoformat()}

            if new_session_id:
                update_data["session_id"] = new_session_id
            if status:
                update_data["status"] = status
            if daily_limit:
                update_data["daily_limit"] = daily_limit
            if notes:
                update_data["notes"] = notes

            self.client.table("instagram_sessions") \
                .update(update_data) \
                .eq("id", session_id) \
                .execute()

            logger.info(f"SessionPool: Session atualizada - {session_id}")
            return True

        except Exception as e:
            logger.error(f"SessionPool: Erro ao atualizar session: {e}")
            return False

    def get_all_sessions(self) -> List[Dict]:
        """
        Lista todas as sessions do pool com estatísticas.

        Returns:
            Lista de sessions com status e métricas
        """
        if not self._pool_available or not self.client:
            return []

        try:
            result = self.client.table("instagram_sessions_dashboard") \
                .select("*") \
                .execute()

            return result.data or []

        except Exception as e:
            logger.error(f"SessionPool: Erro ao listar sessions: {e}")
            return []

    def get_pool_stats(self) -> Dict:
        """
        Retorna estatísticas gerais do pool.

        Returns:
            Dict com total, active, rate_limited, blocked, usage, etc.
        """
        if not self._pool_available or not self.client:
            return {
                "pool_available": False,
                "using_fallback": bool(self._fallback_session_id)
            }

        try:
            sessions = self.get_all_sessions()

            total = len(sessions)
            active = sum(1 for s in sessions if s.get("status") == "active")
            rate_limited = sum(1 for s in sessions if s.get("status") == "rate_limited")
            blocked = sum(1 for s in sessions if s.get("status") == "blocked")

            total_requests = sum(s.get("requests_today", 0) for s in sessions)
            total_limit = sum(s.get("daily_limit", 200) for s in sessions)
            avg_health = sum(s.get("health_score", 0) for s in sessions) / total if total > 0 else 0

            return {
                "pool_available": True,
                "total_sessions": total,
                "active_sessions": active,
                "rate_limited_sessions": rate_limited,
                "blocked_sessions": blocked,
                "requests_today": total_requests,
                "daily_capacity": total_limit,
                "usage_percent": round((total_requests / total_limit) * 100, 1) if total_limit > 0 else 0,
                "avg_health_score": round(avg_health, 1),
                "estimated_remaining": total_limit - total_requests
            }

        except Exception as e:
            logger.error(f"SessionPool: Erro ao obter stats: {e}")
            return {"pool_available": False, "error": str(e)}

    def health_check_all(self) -> Dict:
        """
        Executa health check em todas as sessions ativas.

        Testa cada session fazendo um request simples e
        atualiza o status baseado no resultado.

        Returns:
            Dict com resultados do health check
        """
        if not self._pool_available or not self.client:
            return {"pool_available": False}

        try:
            # Importar scraper aqui para evitar circular import
            from instagram_api_scraper import InstagramAPIScraper

            sessions = self.client.table("instagram_sessions") \
                .select("id, username, session_id") \
                .eq("status", "active") \
                .execute()

            results = {
                "checked": 0,
                "healthy": 0,
                "degraded": 0,
                "blocked": 0,
                "details": []
            }

            for session in sessions.data or []:
                results["checked"] += 1

                try:
                    # Tentar um request simples
                    scraper = InstagramAPIScraper(session_id=session["session_id"])
                    # Buscar o próprio perfil da session (mais seguro)
                    test_result = scraper.get_user_id(session["username"])

                    if test_result:
                        results["healthy"] += 1
                        status = "healthy"
                    else:
                        results["degraded"] += 1
                        status = "degraded"
                        # Degradar health
                        self.client.table("instagram_sessions") \
                            .update({"health_score": 50}) \
                            .eq("id", session["id"]) \
                            .execute()

                except Exception as e:
                    error_str = str(e).lower()

                    if "login" in error_str or "challenge" in error_str:
                        results["blocked"] += 1
                        status = "blocked"
                        self.client.table("instagram_sessions") \
                            .update({"status": "blocked", "health_score": 0}) \
                            .eq("id", session["id"]) \
                            .execute()
                    else:
                        results["degraded"] += 1
                        status = "degraded"

                results["details"].append({
                    "username": session["username"],
                    "status": status
                })

                # Delay entre checks
                import time
                time.sleep(2)

            return results

        except Exception as e:
            logger.error(f"SessionPool: Erro no health check: {e}")
            return {"error": str(e)}


# ============================================
# SINGLETON INSTANCE
# ============================================

_pool_instance: Optional[SessionPool] = None


def get_session_pool() -> SessionPool:
    """
    Retorna instância singleton do SessionPool.

    Uso:
        from instagram_session_pool import get_session_pool

        pool = get_session_pool()
        session = pool.get_session()
    """
    global _pool_instance

    if _pool_instance is None:
        _pool_instance = SessionPool()

    return _pool_instance


# ============================================
# CLI
# ============================================

def main():
    """CLI para gerenciar o pool de sessions"""
    import argparse

    parser = argparse.ArgumentParser(description="Instagram Session Pool Manager")
    subparsers = parser.add_subparsers(dest="command", help="Comandos disponíveis")

    # list
    subparsers.add_parser("list", help="Listar todas as sessions")

    # stats
    subparsers.add_parser("stats", help="Mostrar estatísticas do pool")

    # add
    add_parser = subparsers.add_parser("add", help="Adicionar nova session")
    add_parser.add_argument("username", help="Username da conta Instagram")
    add_parser.add_argument("session_id", help="Session ID (cookie)")
    add_parser.add_argument("--limit", type=int, default=200, help="Limite diário")
    add_parser.add_argument("--notes", help="Notas sobre a conta")

    # remove
    remove_parser = subparsers.add_parser("remove", help="Remover session")
    remove_parser.add_argument("session_id", help="ID (UUID) da session")

    # update
    update_parser = subparsers.add_parser("update", help="Atualizar session")
    update_parser.add_argument("session_id", help="ID (UUID) da session")
    update_parser.add_argument("--new-session-id", help="Novo session_id")
    update_parser.add_argument("--status", choices=["active", "rate_limited", "blocked", "expired"])
    update_parser.add_argument("--limit", type=int)
    update_parser.add_argument("--notes")

    # health-check
    subparsers.add_parser("health-check", help="Executar health check em todas sessions")

    args = parser.parse_args()

    pool = get_session_pool()

    if args.command == "list":
        sessions = pool.get_all_sessions()
        if not sessions:
            print("Nenhuma session encontrada no pool.")
            return

        print("\n" + "="*80)
        print("SESSIONS DO POOL")
        print("="*80)
        for s in sessions:
            status_emoji = {
                "active": "✅",
                "rate_limited": "⏳",
                "blocked": "🚫",
                "expired": "❌"
            }.get(s.get("status"), "❓")

            print(f"\n{status_emoji} @{s.get('username')}")
            print(f"   ID: {s.get('id')}")
            print(f"   Status: {s.get('status')} | Health: {s.get('health_score')}/100")
            print(f"   Requests: {s.get('requests_today')}/{s.get('daily_limit')} ({s.get('usage_percent', 0)}%)")
            print(f"   Last: {s.get('last_request_at') or 'Never'}")

    elif args.command == "stats":
        stats = pool.get_pool_stats()
        print("\n" + "="*50)
        print("ESTATÍSTICAS DO POOL")
        print("="*50)
        for key, value in stats.items():
            print(f"{key}: {value}")

    elif args.command == "add":
        result = pool.add_session(
            username=args.username,
            session_id=args.session_id,
            daily_limit=args.limit,
            notes=args.notes
        )
        if result:
            print(f"✅ Session adicionada: {result}")
        else:
            print("❌ Erro ao adicionar session")

    elif args.command == "remove":
        if pool.remove_session(args.session_id):
            print("✅ Session removida")
        else:
            print("❌ Erro ao remover session")

    elif args.command == "update":
        if pool.update_session(
            session_id=args.session_id,
            new_session_id=args.new_session_id,
            status=args.status,
            daily_limit=args.limit,
            notes=args.notes
        ):
            print("✅ Session atualizada")
        else:
            print("❌ Erro ao atualizar session")

    elif args.command == "health-check":
        print("Executando health check...")
        results = pool.health_check_all()
        print(f"\nResultados:")
        print(f"  Checked: {results.get('checked', 0)}")
        print(f"  Healthy: {results.get('healthy', 0)}")
        print(f"  Degraded: {results.get('degraded', 0)}")
        print(f"  Blocked: {results.get('blocked', 0)}")

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
