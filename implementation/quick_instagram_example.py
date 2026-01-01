#!/usr/bin/env python3
"""
Exemplo rápido de uso do Instagram Followers Downloader
"""

from instagram_followers_downloader import InstagramFollowersDownloader
import os
from dotenv import load_dotenv

load_dotenv()


def quick_download():
    """Exemplo simples de download de seguidores"""

    # Suas credenciais (use variáveis de ambiente em produção)
    USERNAME = os.getenv('INSTAGRAM_USERNAME', 'seu_usuario')
    PASSWORD = os.getenv('INSTAGRAM_PASSWORD', 'sua_senha')

    # Perfil alvo (None = seu próprio perfil)
    TARGET = None  # ou "username_alvo"

    print("Iniciando download de seguidores...")

    # Criar downloader
    downloader = InstagramFollowersDownloader(USERNAME, PASSWORD)

    # Login
    if not downloader.login():
        print("Erro no login!")
        return

    # Baixar seguidores
    followers = downloader.get_followers(TARGET)

    if not followers:
        print("Nenhum seguidor encontrado!")
        return

    # Exportar em todos os formatos
    print(f"\n✅ {len(followers)} seguidores baixados!")
    print("\nExportando...")

    downloader.export_to_csv(followers)
    downloader.export_to_json(followers)
    downloader.export_simple_list(followers)

    print("\n✅ Exportação concluída!")

    # Mostrar alguns dados
    print("\n📊 Primeiros 5 seguidores:")
    for i, follower in enumerate(followers[:5], 1):
        print(f"{i}. @{follower['username']} - {follower['full_name']}")
        print(f"   Seguidores: {follower['followers_count']} | Posts: {follower['posts_count']}")


if __name__ == "__main__":
    quick_download()
