#!/usr/bin/env python3
"""
Instagram Followers Downloader
Baixa lista completa de seguidores de um perfil do Instagram

ATENÇÃO: Respeite os limites de rate da API do Instagram
"""

import instaloader
import csv
import json
import os
from datetime import datetime
from typing import List, Dict, Optional
import time
import logging
from pathlib import Path

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('instagram_followers.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class InstagramFollowersDownloader:
    """Baixa e exporta seguidores do Instagram"""

    def __init__(self, username: str, password: str):
        """
        Inicializa o downloader

        Args:
            username: Seu username do Instagram
            password: Sua senha do Instagram
        """
        self.username = username
        self.password = password
        self.loader = instaloader.Instaloader(
            download_pictures=False,
            download_videos=False,
            download_video_thumbnails=False,
            download_geotags=False,
            download_comments=False,
            save_metadata=False,
            compress_json=False,
            max_connection_attempts=3
        )
        self.session_file = Path(f"session-{username}")

    def login(self) -> bool:
        """
        Faz login no Instagram

        Returns:
            True se login bem sucedido, False caso contrário
        """
        try:
            # Tentar carregar sessão existente
            if self.session_file.exists():
                logger.info(f"Carregando sessão salva de {self.session_file}")
                self.loader.load_session_from_file(self.username, str(self.session_file))
                logger.info("✅ Sessão carregada com sucesso")
                return True

            # Fazer novo login
            logger.info(f"Fazendo login como {self.username}...")
            self.loader.login(self.username, self.password)

            # Salvar sessão
            self.loader.save_session_to_file(str(self.session_file))
            logger.info("✅ Login realizado e sessão salva")
            return True

        except instaloader.exceptions.BadCredentialsException:
            logger.error("❌ Credenciais inválidas")
            return False
        except instaloader.exceptions.TwoFactorAuthRequiredException:
            logger.error("❌ Autenticação de dois fatores necessária")
            logger.info("Por favor, desabilite 2FA temporariamente ou use código manualmente")
            return False
        except Exception as e:
            logger.error(f"❌ Erro no login: {str(e)}")
            return False

    def get_followers(self, target_username: Optional[str] = None) -> List[Dict[str, any]]:
        """
        Obtém lista de seguidores

        Args:
            target_username: Username do perfil (None = seu próprio perfil)

        Returns:
            Lista de dicionários com dados dos seguidores
        """
        target = target_username or self.username
        followers_data = []

        try:
            logger.info(f"Buscando perfil de {target}...")
            profile = instaloader.Profile.from_username(self.loader.context, target)

            total_followers = profile.followers
            logger.info(f"Total de seguidores: {total_followers}")

            logger.info("Baixando lista de seguidores... (isso pode demorar)")

            count = 0
            for follower in profile.get_followers():
                count += 1

                follower_info = {
                    'username': follower.username,
                    'full_name': follower.full_name,
                    'user_id': follower.userid,
                    'is_verified': follower.is_verified,
                    'is_private': follower.is_private,
                    'followers_count': follower.followers,
                    'following_count': follower.followees,
                    'posts_count': follower.mediacount,
                    'biography': follower.biography,
                    'external_url': follower.external_url,
                    'profile_pic_url': follower.profile_pic_url,
                    'is_business_account': follower.is_business_account,
                    'collected_at': datetime.now().isoformat()
                }

                followers_data.append(follower_info)

                # Log de progresso
                if count % 50 == 0:
                    logger.info(f"Progresso: {count}/{total_followers} seguidores baixados")

                # Rate limiting - pequena pausa a cada 100 seguidores
                if count % 100 == 0:
                    logger.info("Pausando para evitar rate limit...")
                    time.sleep(10)

            logger.info(f"✅ Total de {len(followers_data)} seguidores baixados")
            return followers_data

        except instaloader.exceptions.ProfileNotExistsException:
            logger.error(f"❌ Perfil {target} não existe")
            return []
        except instaloader.exceptions.LoginRequiredException:
            logger.error("❌ Login necessário. Sessão pode ter expirado")
            return []
        except Exception as e:
            logger.error(f"❌ Erro ao buscar seguidores: {str(e)}")
            return []

    def export_to_csv(self, followers: List[Dict], filename: str = None):
        """
        Exporta seguidores para CSV

        Args:
            followers: Lista de seguidores
            filename: Nome do arquivo (None = auto-gerar)
        """
        if not followers:
            logger.warning("Nenhum seguidor para exportar")
            return

        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"instagram_followers_{timestamp}.csv"

        try:
            with open(filename, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=followers[0].keys())
                writer.writeheader()
                writer.writerows(followers)

            logger.info(f"✅ CSV exportado: {filename}")
        except Exception as e:
            logger.error(f"❌ Erro ao exportar CSV: {str(e)}")

    def export_to_json(self, followers: List[Dict], filename: str = None):
        """
        Exporta seguidores para JSON

        Args:
            followers: Lista de seguidores
            filename: Nome do arquivo (None = auto-gerar)
        """
        if not followers:
            logger.warning("Nenhum seguidor para exportar")
            return

        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"instagram_followers_{timestamp}.json"

        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(followers, f, indent=2, ensure_ascii=False)

            logger.info(f"✅ JSON exportado: {filename}")
        except Exception as e:
            logger.error(f"❌ Erro ao exportar JSON: {str(e)}")

    def export_simple_list(self, followers: List[Dict], filename: str = None):
        """
        Exporta apenas usernames (lista simples)

        Args:
            followers: Lista de seguidores
            filename: Nome do arquivo (None = auto-gerar)
        """
        if not followers:
            logger.warning("Nenhum seguidor para exportar")
            return

        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"instagram_followers_usernames_{timestamp}.txt"

        try:
            with open(filename, 'w', encoding='utf-8') as f:
                for follower in followers:
                    f.write(f"{follower['username']}\n")

            logger.info(f"✅ Lista de usernames exportada: {filename}")
        except Exception as e:
            logger.error(f"❌ Erro ao exportar lista: {str(e)}")


def main():
    """Função principal"""
    print("=" * 60)
    print("INSTAGRAM FOLLOWERS DOWNLOADER")
    print("=" * 60)
    print()

    # Solicitar credenciais
    username = input("Seu username do Instagram: ").strip()
    password = input("Sua senha: ").strip()

    print()
    target = input("Username do perfil (deixe vazio para usar o seu próprio): ").strip()
    if not target:
        target = None

    print()
    print("Formatos de exportação:")
    print("1 - CSV (completo)")
    print("2 - JSON (completo)")
    print("3 - TXT (apenas usernames)")
    print("4 - Todos os formatos")
    export_choice = input("Escolha (1-4): ").strip()

    # Inicializar downloader
    downloader = InstagramFollowersDownloader(username, password)

    # Login
    print("\n" + "=" * 60)
    if not downloader.login():
        print("❌ Não foi possível fazer login. Verifique suas credenciais.")
        return

    # Baixar seguidores
    print("\n" + "=" * 60)
    followers = downloader.get_followers(target)

    if not followers:
        print("❌ Nenhum seguidor encontrado ou erro ao buscar.")
        return

    # Exportar
    print("\n" + "=" * 60)
    print("Exportando dados...")

    if export_choice in ['1', '4']:
        downloader.export_to_csv(followers)

    if export_choice in ['2', '4']:
        downloader.export_to_json(followers)

    if export_choice in ['3', '4']:
        downloader.export_simple_list(followers)

    print("\n" + "=" * 60)
    print("✅ PROCESSO CONCLUÍDO!")
    print(f"Total de seguidores baixados: {len(followers)}")
    print("=" * 60)


if __name__ == "__main__":
    main()
