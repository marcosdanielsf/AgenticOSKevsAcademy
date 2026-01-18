#!/usr/bin/env python3
"""
🔍 NEW FOLLOWERS DETECTOR
==========================
Detecta novos seguidores comparando snapshots e prepara para outreach.

Fluxo:
1. Busca seguidores atuais via InstagramAPIScraper.get_followers()
2. Compara com ultimo snapshot para detectar novos
3. Calcula ICP score para cada novo seguidor
4. Salva no Supabase para processamento

Uso:
    from new_followers_detector import NewFollowersDetector

    detector = NewFollowersDetector()
    new_followers = await detector.detect_new("account_id")
    print(f"Encontrados {len(new_followers)} novos seguidores")

Endpoints:
    POST /followers/detect-new    - Detecta novos seguidores
    POST /followers/outreach      - Envia DM para novos
    GET  /followers/stats/{id}    - Estatisticas da conta
"""

import os
import json
import logging
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

# Import local modules
try:
    from instagram_api_scraper import InstagramAPIScraper
except ImportError:
    from implementation.instagram_api_scraper import InstagramAPIScraper

try:
    import sys
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from database.supabase_client import SupabaseClient
except ImportError:
    from supabase_client import SupabaseClient


@dataclass
class NewFollower:
    """Representa um novo seguidor detectado"""
    follower_user_id: str
    follower_username: str
    follower_full_name: Optional[str] = None
    follower_bio: Optional[str] = None
    follower_profile_pic: Optional[str] = None
    follower_followers_count: Optional[int] = None
    follower_following_count: Optional[int] = None
    follower_is_business: Optional[bool] = None
    follower_is_verified: Optional[bool] = None
    icp_score: Optional[int] = None
    icp_analysis: Optional[Dict] = None


class NewFollowersDetector:
    """
    Detecta novos seguidores comparando snapshots do Instagram.
    Usa o metodo de scraping Bruno Fraga via InstagramAPIScraper.
    """

    def __init__(self, session_id: str = None):
        """
        Inicializa o detector.

        Args:
            session_id: Session ID do Instagram (opcional, usa pool se nao fornecido)
        """
        self.scraper = InstagramAPIScraper(session_id=session_id)
        self.db = SupabaseClient()
        logger.info("NewFollowersDetector inicializado")

    def get_monitored_accounts(self, active_only: bool = True) -> List[Dict]:
        """
        Retorna lista de contas monitoradas.

        Args:
            active_only: Se True, retorna apenas contas ativas

        Returns:
            Lista de contas do instagram_accounts
        """
        try:
            filters = {}
            if active_only:
                filters["is_active"] = "eq.true"

            accounts = self.db.select("instagram_accounts", filters=filters)
            logger.info(f"Encontradas {len(accounts)} contas monitoradas")
            return accounts

        except Exception as e:
            logger.error(f"Erro ao buscar contas monitoradas: {e}")
            return []

    def get_account_by_id(self, account_id: str) -> Optional[Dict]:
        """Busca conta por ID"""
        try:
            accounts = self.db.select(
                "instagram_accounts",
                filters={"id": f"eq.{account_id}"}
            )
            return accounts[0] if accounts else None
        except Exception as e:
            logger.error(f"Erro ao buscar conta {account_id}: {e}")
            return None

    def fetch_current_followers(self, username: str, max_count: int = 500) -> List[Dict]:
        """
        Busca seguidores atuais de uma conta via API.

        Args:
            username: Username da conta Instagram
            max_count: Maximo de seguidores a buscar (default: 500)

        Returns:
            Lista de seguidores com dados basicos
        """
        try:
            logger.info(f"Buscando seguidores atuais de @{username} (max: {max_count})")

            result = self.scraper.get_followers(username, max_count=max_count)

            if not result.get("success"):
                logger.error(f"Erro ao buscar seguidores: {result.get('error')}")
                return []

            followers = result.get("followers", [])
            logger.info(f"Encontrados {len(followers)} seguidores de @{username}")
            return followers

        except Exception as e:
            logger.error(f"Erro ao buscar seguidores de @{username}: {e}")
            return []

    def get_last_snapshot(self, account_id: str) -> Optional[Dict]:
        """
        Busca ultimo snapshot de seguidores de uma conta.

        Args:
            account_id: UUID da conta no instagram_accounts

        Returns:
            Ultimo snapshot ou None se nao existir
        """
        try:
            snapshots = self.db.select(
                "instagram_followers_snapshots",
                filters={"account_id": f"eq.{account_id}"},
            )

            if not snapshots:
                return None

            # Ordenar por data e pegar o mais recente
            snapshots.sort(key=lambda x: x.get("snapshot_at", ""), reverse=True)
            return snapshots[0]

        except Exception as e:
            logger.error(f"Erro ao buscar snapshot: {e}")
            return None

    def save_snapshot(self, account_id: str, followers: List[Dict]) -> bool:
        """
        Salva snapshot de seguidores no banco.

        Args:
            account_id: UUID da conta
            followers: Lista de seguidores

        Returns:
            True se salvou com sucesso
        """
        try:
            # Extrair apenas user_ids para o snapshot (mais leve)
            followers_data = [
                {
                    "user_id": f.get("user_id"),
                    "username": f.get("username"),
                }
                for f in followers
            ]

            snapshot_data = {
                "account_id": account_id,
                "snapshot_at": datetime.now().isoformat(),
                "followers_data": json.dumps(followers_data),
                "total_count": len(followers),
            }

            self.db.insert("instagram_followers_snapshots", snapshot_data)
            logger.info(f"Snapshot salvo: {len(followers)} seguidores")
            return True

        except Exception as e:
            logger.error(f"Erro ao salvar snapshot: {e}")
            return False

    def detect_new_followers(
        self,
        account_id: str,
        current_followers: List[Dict],
        last_snapshot: Optional[Dict]
    ) -> List[Dict]:
        """
        Compara seguidores atuais com snapshot anterior para detectar novos.

        Args:
            account_id: UUID da conta
            current_followers: Lista de seguidores atuais
            last_snapshot: Ultimo snapshot (pode ser None)

        Returns:
            Lista de novos seguidores detectados
        """
        if not last_snapshot:
            logger.info("Primeiro snapshot - todos serao considerados novos")
            return current_followers

        try:
            # Extrair user_ids do snapshot anterior
            previous_data = json.loads(last_snapshot.get("followers_data", "[]"))
            previous_ids = {str(f.get("user_id")) for f in previous_data}

            # Encontrar novos (que nao estavam no snapshot anterior)
            new_followers = [
                f for f in current_followers
                if str(f.get("user_id")) not in previous_ids
            ]

            logger.info(
                f"Detectados {len(new_followers)} novos seguidores "
                f"(de {len(current_followers)} atuais vs {len(previous_ids)} anteriores)"
            )
            return new_followers

        except Exception as e:
            logger.error(f"Erro ao detectar novos: {e}")
            return []

    def enrich_follower(self, follower: Dict) -> Dict:
        """
        Enriquece dados do seguidor buscando perfil completo.

        Args:
            follower: Dados basicos do seguidor

        Returns:
            Dados enriquecidos com bio, metricas, etc
        """
        try:
            username = follower.get("username")
            if not username:
                return follower

            # Buscar perfil completo
            profile = self.scraper.get_profile(username)

            if profile.get("success"):
                follower.update({
                    "follower_bio": profile.get("bio"),
                    "follower_followers_count": profile.get("followers_count"),
                    "follower_following_count": profile.get("following_count"),
                    "follower_is_business": profile.get("is_business"),
                    "follower_is_verified": profile.get("is_verified"),
                    "follower_profile_pic": profile.get("profile_pic_url"),
                })

            return follower

        except Exception as e:
            logger.warning(f"Erro ao enriquecer {follower.get('username')}: {e}")
            return follower

    def calculate_icp_score(self, follower: Dict) -> Dict:
        """
        Calcula ICP score usando o metodo existente do scraper.

        Args:
            follower: Dados do seguidor

        Returns:
            Dict com score, classification e signals
        """
        try:
            # Usar metodo existente do scraper
            score_data = self.scraper.calculate_lead_score(follower)
            return score_data

        except Exception as e:
            logger.warning(f"Erro ao calcular score: {e}")
            return {"score": 0, "classification": "LEAD_COLD", "signals": []}

    def save_new_followers(
        self,
        account_id: str,
        new_followers: List[Dict],
        enrich: bool = True
    ) -> int:
        """
        Salva novos seguidores no banco.

        Args:
            account_id: UUID da conta
            new_followers: Lista de novos seguidores
            enrich: Se True, enriquece dados antes de salvar

        Returns:
            Numero de seguidores salvos
        """
        saved_count = 0

        for follower in new_followers:
            try:
                # Enriquecer se solicitado
                if enrich:
                    follower = self.enrich_follower(follower)
                    # Rate limiting
                    import time
                    time.sleep(1)

                # Calcular ICP score
                score_data = self.calculate_icp_score(follower)

                # Preparar dados para insert
                data = {
                    "account_id": account_id,
                    "follower_user_id": str(follower.get("user_id")),
                    "follower_username": follower.get("username"),
                    "follower_full_name": follower.get("full_name"),
                    "follower_bio": follower.get("follower_bio") or follower.get("bio"),
                    "follower_profile_pic": follower.get("follower_profile_pic") or follower.get("profile_pic_url"),
                    "follower_followers_count": follower.get("follower_followers_count") or follower.get("followers_count"),
                    "follower_following_count": follower.get("follower_following_count") or follower.get("following_count"),
                    "follower_is_business": follower.get("follower_is_business") or follower.get("is_business"),
                    "follower_is_verified": follower.get("follower_is_verified") or follower.get("is_verified"),
                    "icp_score": score_data.get("score"),
                    "icp_analysis": json.dumps(score_data),
                    "outreach_status": "pending",
                    "detected_at": datetime.now().isoformat(),
                }

                # Upsert para evitar duplicatas
                self.db.upsert("new_followers_detected", data)
                saved_count += 1

            except Exception as e:
                logger.warning(f"Erro ao salvar seguidor {follower.get('username')}: {e}")
                continue

        logger.info(f"Salvos {saved_count} novos seguidores")
        return saved_count

    def update_account_check(self, account_id: str) -> bool:
        """Atualiza timestamp de ultima verificacao da conta"""
        try:
            self.db.update(
                "instagram_accounts",
                {"last_check_at": datetime.now().isoformat()},
                {"id": account_id}
            )
            return True
        except Exception as e:
            logger.error(f"Erro ao atualizar conta: {e}")
            return False

    def detect_new(
        self,
        account_id: str,
        max_followers: int = 500,
        enrich: bool = True,
        save_snapshot: bool = True
    ) -> Dict:
        """
        Metodo principal: detecta novos seguidores de uma conta.

        Args:
            account_id: UUID da conta no instagram_accounts
            max_followers: Maximo de seguidores a buscar
            enrich: Se True, busca perfil completo de cada novo
            save_snapshot: Se True, salva snapshot apos deteccao

        Returns:
            Dict com resultados da deteccao
        """
        result = {
            "success": False,
            "account_id": account_id,
            "new_followers_count": 0,
            "saved_count": 0,
            "error": None,
            "detected_at": datetime.now().isoformat(),
        }

        try:
            # 1. Buscar conta
            account = self.get_account_by_id(account_id)
            if not account:
                result["error"] = "Conta nao encontrada"
                return result

            username = account.get("username")
            result["username"] = username
            logger.info(f"Iniciando deteccao para @{username}")

            # 2. Extrair session_id da conta monitorada
            session_data = account.get("session_data")
            account_session_id = None
            if session_data:
                cookies = session_data.get("cookies", [])
                for cookie in cookies:
                    if cookie.get("name") == "sessionid":
                        # Decodificar URL encoding (%3A -> :)
                        from urllib.parse import unquote
                        account_session_id = unquote(cookie.get("value", ""))
                        break

                if account_session_id:
                    logger.info(f"Usando session_id da conta @{username}")
                    # Criar scraper temporario com session da conta
                    self.scraper = InstagramAPIScraper(session_id=account_session_id)
                else:
                    logger.error(f"Conta @{username} nao tem sessionid nos cookies")
                    result["error"] = "Conta sem sessionid nos cookies"
                    return result
            else:
                logger.error(f"Conta @{username} nao tem session_data configurada")
                result["error"] = "Conta sem session_data configurada"
                return result

            # 3. Buscar seguidores atuais (usando session da conta)
            current_followers = self.fetch_current_followers(username, max_followers)
            if not current_followers:
                result["error"] = "Nao foi possivel buscar seguidores"
                return result

            result["current_followers_count"] = len(current_followers)

            # 4. Buscar ultimo snapshot
            last_snapshot = self.get_last_snapshot(account_id)
            result["has_previous_snapshot"] = last_snapshot is not None

            # 5. Detectar novos
            new_followers = self.detect_new_followers(
                account_id, current_followers, last_snapshot
            )
            result["new_followers_count"] = len(new_followers)

            # 6. Salvar novos seguidores
            if new_followers:
                saved = self.save_new_followers(account_id, new_followers, enrich=enrich)
                result["saved_count"] = saved

            # 7. Salvar novo snapshot
            if save_snapshot:
                self.save_snapshot(account_id, current_followers)

            # 8. Atualizar conta
            self.update_account_check(account_id)

            result["success"] = True
            logger.info(
                f"Deteccao concluida: {result['new_followers_count']} novos, "
                f"{result['saved_count']} salvos"
            )

        except Exception as e:
            logger.error(f"Erro na deteccao: {e}")
            result["error"] = str(e)

        return result

    def detect_all_accounts(
        self,
        max_followers_per_account: int = 500,
        enrich: bool = False,
        delay_between_accounts: int = 60
    ) -> Dict:
        """
        Detecta novos seguidores para todas as contas ativas.

        Args:
            max_followers_per_account: Max seguidores por conta
            enrich: Se True, enriquece dados (mais lento)
            delay_between_accounts: Delay em segundos entre contas

        Returns:
            Dict com resultados agregados
        """
        results = {
            "success": True,
            "accounts_processed": 0,
            "total_new_followers": 0,
            "total_saved": 0,
            "errors": [],
            "details": [],
        }

        accounts = self.get_monitored_accounts(active_only=True)

        for i, account in enumerate(accounts):
            account_id = account.get("id")
            username = account.get("username")

            logger.info(f"[{i+1}/{len(accounts)}] Processando @{username}")

            try:
                detection_result = self.detect_new(
                    account_id=account_id,
                    max_followers=max_followers_per_account,
                    enrich=enrich,
                )

                results["accounts_processed"] += 1
                results["total_new_followers"] += detection_result.get("new_followers_count", 0)
                results["total_saved"] += detection_result.get("saved_count", 0)
                results["details"].append(detection_result)

                if detection_result.get("error"):
                    results["errors"].append({
                        "account": username,
                        "error": detection_result["error"]
                    })

            except Exception as e:
                logger.error(f"Erro ao processar @{username}: {e}")
                results["errors"].append({
                    "account": username,
                    "error": str(e)
                })

            # Delay entre contas
            if i < len(accounts) - 1:
                import time
                time.sleep(delay_between_accounts)

        results["success"] = len(results["errors"]) == 0
        return results

    def get_pending_outreach(
        self,
        account_id: Optional[str] = None,
        min_icp_score: int = 70,
        limit: int = 50
    ) -> List[Dict]:
        """
        Busca seguidores pendentes para outreach.

        Args:
            account_id: Filtrar por conta (opcional)
            min_icp_score: Score minimo para outreach
            limit: Maximo de resultados

        Returns:
            Lista de seguidores prontos para outreach
        """
        try:
            filters = {
                "outreach_status": "eq.pending",
                "icp_score": f"gte.{min_icp_score}",
            }

            if account_id:
                filters["account_id"] = f"eq.{account_id}"

            followers = self.db.select(
                "new_followers_detected",
                filters=filters,
            )

            # Ordenar por ICP score (maior primeiro) e limitar
            followers.sort(key=lambda x: x.get("icp_score", 0), reverse=True)
            return followers[:limit]

        except Exception as e:
            logger.error(f"Erro ao buscar pendentes: {e}")
            return []

    def update_outreach_status(
        self,
        follower_id: str,
        status: str,
        message: Optional[str] = None
    ) -> bool:
        """
        Atualiza status de outreach de um seguidor.

        Args:
            follower_id: UUID do seguidor
            status: Novo status (sent, responded, skipped, failed)
            message: Mensagem enviada (opcional)

        Returns:
            True se atualizou com sucesso
        """
        try:
            data = {
                "outreach_status": status,
            }

            if status == "sent" and message:
                data["outreach_message"] = message
                data["outreach_sent_at"] = datetime.now().isoformat()

            if status == "responded":
                data["outreach_responded_at"] = datetime.now().isoformat()

            self.db.update(
                "new_followers_detected",
                data,
                {"id": follower_id}
            )
            return True

        except Exception as e:
            logger.error(f"Erro ao atualizar status: {e}")
            return False

    def get_stats(self, account_id: Optional[str] = None) -> Dict:
        """
        Retorna estatisticas de novos seguidores.

        Args:
            account_id: Filtrar por conta (opcional)

        Returns:
            Dict com estatisticas agregadas
        """
        try:
            # Usar a view de summary se disponivel
            if account_id:
                summaries = self.db.select(
                    "vw_new_followers_summary",
                    filters={"account_id": f"eq.{account_id}"}
                )
            else:
                summaries = self.db.select("vw_new_followers_summary")

            if not summaries:
                return {
                    "total_accounts": 0,
                    "total_new_followers": 0,
                    "pending": 0,
                    "sent": 0,
                    "responded": 0,
                    "skipped": 0,
                    "avg_icp_score": 0,
                }

            # Agregar stats
            stats = {
                "total_accounts": len(summaries),
                "total_new_followers": sum(s.get("total_new_followers", 0) for s in summaries),
                "pending": sum(s.get("pending_count", 0) for s in summaries),
                "sent": sum(s.get("sent_count", 0) for s in summaries),
                "responded": sum(s.get("responded_count", 0) for s in summaries),
                "skipped": sum(s.get("skipped_count", 0) for s in summaries),
                "ready_for_outreach": sum(s.get("ready_for_outreach", 0) for s in summaries),
                "accounts": summaries,
            }

            # Calcular media de ICP
            scores = [s.get("avg_icp_score") for s in summaries if s.get("avg_icp_score")]
            stats["avg_icp_score"] = sum(scores) / len(scores) if scores else 0

            return stats

        except Exception as e:
            logger.error(f"Erro ao buscar stats: {e}")
            return {}


# ============================================
# FUNCOES DE CONVENIENCIA
# ============================================

def detect_new_followers(account_id: str, enrich: bool = False) -> Dict:
    """
    Funcao de conveniencia para detectar novos seguidores.

    Uso:
        from new_followers_detector import detect_new_followers

        result = detect_new_followers("uuid-da-conta")
        print(f"Novos: {result['new_followers_count']}")
    """
    detector = NewFollowersDetector()
    return detector.detect_new(account_id, enrich=enrich)


def get_pending_for_outreach(min_score: int = 70, limit: int = 50) -> List[Dict]:
    """
    Funcao de conveniencia para buscar pendentes de outreach.
    """
    detector = NewFollowersDetector()
    return detector.get_pending_outreach(min_icp_score=min_score, limit=limit)


# ============================================
# CLI
# ============================================

def main():
    """CLI para testar o detector"""
    import argparse

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    parser = argparse.ArgumentParser(description="New Followers Detector")
    parser.add_argument("--account-id", help="UUID da conta para detectar")
    parser.add_argument("--all", action="store_true", help="Processar todas as contas")
    parser.add_argument("--stats", action="store_true", help="Mostrar estatisticas")
    parser.add_argument("--pending", action="store_true", help="Listar pendentes de outreach")
    parser.add_argument("--enrich", action="store_true", help="Enriquecer dados (mais lento)")
    parser.add_argument("--max", type=int, default=500, help="Max seguidores a buscar")
    parser.add_argument("--min-score", type=int, default=70, help="Score minimo para outreach")

    args = parser.parse_args()

    detector = NewFollowersDetector()

    print("\n" + "="*60)
    print("  NEW FOLLOWERS DETECTOR - MOTTIVME")
    print("="*60 + "\n")

    if args.stats:
        print("📊 Estatisticas:\n")
        stats = detector.get_stats(args.account_id)
        for key, value in stats.items():
            if key != "accounts":
                print(f"   {key}: {value}")
        return

    if args.pending:
        print(f"📋 Pendentes para outreach (score >= {args.min_score}):\n")
        pending = detector.get_pending_outreach(
            account_id=args.account_id,
            min_icp_score=args.min_score
        )
        for p in pending[:20]:
            print(f"   @{p.get('follower_username')} - Score: {p.get('icp_score')}")
        print(f"\n   Total: {len(pending)}")
        return

    if args.all:
        print("🔍 Processando todas as contas ativas...\n")
        result = detector.detect_all_accounts(
            max_followers_per_account=args.max,
            enrich=args.enrich
        )
        print(f"\n✅ Concluido!")
        print(f"   Contas processadas: {result['accounts_processed']}")
        print(f"   Total novos: {result['total_new_followers']}")
        print(f"   Total salvos: {result['total_saved']}")
        if result["errors"]:
            print(f"   Erros: {len(result['errors'])}")
        return

    if args.account_id:
        print(f"🔍 Detectando novos seguidores para conta {args.account_id}...\n")
        result = detector.detect_new(
            account_id=args.account_id,
            max_followers=args.max,
            enrich=args.enrich
        )

        if result["success"]:
            print(f"✅ Sucesso!")
            print(f"   Username: @{result.get('username')}")
            print(f"   Seguidores atuais: {result.get('current_followers_count')}")
            print(f"   Novos detectados: {result.get('new_followers_count')}")
            print(f"   Salvos: {result.get('saved_count')}")
        else:
            print(f"❌ Erro: {result.get('error')}")
        return

    print("Use --help para ver opcoes disponiveis")


if __name__ == "__main__":
    main()
