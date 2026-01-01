#!/usr/bin/env python3
"""
Instagram Followers to Google Sheets
Exporta seguidores do Instagram diretamente para Google Sheets
"""

import gspread
from oauth2client.service_account import ServiceAccountCredentials
from instagram_followers_downloader import InstagramFollowersDownloader
import logging
from typing import List, Dict
import os
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class InstagramToSheets:
    """Exporta seguidores do Instagram para Google Sheets"""

    def __init__(self, service_account_file: str = 'service_account.json'):
        """
        Inicializa conexão com Google Sheets

        Args:
            service_account_file: Caminho para arquivo JSON da service account
        """
        self.service_account_file = service_account_file
        self.client = None

    def authenticate(self):
        """Autentica com Google Sheets API"""
        try:
            scope = [
                'https://spreadsheets.google.com/feeds',
                'https://www.googleapis.com/auth/drive'
            ]
            creds = ServiceAccountCredentials.from_json_keyfile_name(
                self.service_account_file, scope
            )
            self.client = gspread.authorize(creds)
            logger.info("✅ Autenticado com Google Sheets")
        except FileNotFoundError:
            logger.error(f"❌ Arquivo {self.service_account_file} não encontrado")
            raise
        except Exception as e:
            logger.error(f"❌ Erro na autenticação: {str(e)}")
            raise

    def create_or_open_sheet(self, sheet_name: str) -> gspread.Worksheet:
        """
        Cria ou abre uma planilha

        Args:
            sheet_name: Nome da planilha

        Returns:
            Worksheet object
        """
        try:
            # Tentar abrir planilha existente
            spreadsheet = self.client.open(sheet_name)
            logger.info(f"Planilha '{sheet_name}' já existe, abrindo...")
        except gspread.SpreadsheetNotFound:
            # Criar nova planilha
            logger.info(f"Criando nova planilha '{sheet_name}'...")
            spreadsheet = self.client.create(sheet_name)

        # Pegar primeira aba
        worksheet = spreadsheet.sheet1
        return worksheet

    def export_followers(
        self,
        followers: List[Dict],
        sheet_name: str,
        clear_existing: bool = True
    ):
        """
        Exporta seguidores para Google Sheets

        Args:
            followers: Lista de seguidores
            sheet_name: Nome da planilha
            clear_existing: Se True, limpa dados existentes
        """
        if not followers:
            logger.warning("Nenhum seguidor para exportar")
            return

        try:
            worksheet = self.create_or_open_sheet(sheet_name)

            # Limpar dados existentes se solicitado
            if clear_existing:
                worksheet.clear()
                logger.info("Dados existentes limpos")

            # Preparar headers
            headers = list(followers[0].keys())

            # Preparar dados
            all_data = [headers]
            for follower in followers:
                row = [str(follower.get(key, '')) for key in headers]
                all_data.append(row)

            # Atualizar planilha de uma vez (mais eficiente)
            logger.info(f"Escrevendo {len(followers)} seguidores na planilha...")
            worksheet.update(
                range_name='A1',
                values=all_data,
                value_input_option='RAW'
            )

            # Formatar header
            worksheet.format('A1:Z1', {
                "backgroundColor": {
                    "red": 0.2,
                    "green": 0.2,
                    "blue": 0.2
                },
                "textFormat": {
                    "foregroundColor": {
                        "red": 1.0,
                        "green": 1.0,
                        "blue": 1.0
                    },
                    "fontSize": 11,
                    "bold": True
                }
            })

            # Congelar primeira linha
            worksheet.freeze(rows=1)

            # Ajustar largura das colunas
            worksheet.columns_auto_resize(0, len(headers))

            logger.info(f"✅ {len(followers)} seguidores exportados para '{sheet_name}'")
            logger.info(f"URL: {worksheet.spreadsheet.url}")

        except Exception as e:
            logger.error(f"❌ Erro ao exportar para sheets: {str(e)}")
            raise


def main():
    """Função principal"""
    print("=" * 60)
    print("INSTAGRAM FOLLOWERS TO GOOGLE SHEETS")
    print("=" * 60)
    print()

    # Credenciais Instagram
    ig_username = input("Seu username do Instagram: ").strip()
    ig_password = input("Sua senha do Instagram: ").strip()

    print()
    target = input("Username do perfil alvo (vazio = seu perfil): ").strip()
    if not target:
        target = None

    # Nome da planilha
    print()
    sheet_name = input("Nome da planilha no Google Sheets: ").strip()
    if not sheet_name:
        sheet_name = f"Instagram Followers - {target or ig_username}"

    print("\n" + "=" * 60)
    print("BAIXANDO SEGUIDORES DO INSTAGRAM")
    print("=" * 60)

    # Download do Instagram
    downloader = InstagramFollowersDownloader(ig_username, ig_password)

    if not downloader.login():
        print("❌ Erro no login do Instagram")
        return

    followers = downloader.get_followers(target)

    if not followers:
        print("❌ Nenhum seguidor encontrado")
        return

    print("\n" + "=" * 60)
    print("EXPORTANDO PARA GOOGLE SHEETS")
    print("=" * 60)

    # Exportar para Sheets
    sheets_exporter = InstagramToSheets()
    sheets_exporter.authenticate()
    sheets_exporter.export_followers(followers, sheet_name)

    print("\n" + "=" * 60)
    print("✅ PROCESSO CONCLUÍDO!")
    print(f"Total de seguidores: {len(followers)}")
    print("=" * 60)


if __name__ == "__main__":
    main()
