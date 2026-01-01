#!/usr/bin/env python3
"""
Instagram Followers Analytics
Analisa dados de seguidores baixados do Instagram
"""

import json
import pandas as pd
from typing import Dict, List
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class FollowersAnalytics:
    """Análise de dados de seguidores do Instagram"""

    def __init__(self, followers_file: str):
        """
        Inicializa analytics

        Args:
            followers_file: Caminho para arquivo JSON de seguidores
        """
        self.followers_file = followers_file
        self.followers = []
        self.df = None

    def load_data(self):
        """Carrega dados de seguidores"""
        try:
            with open(self.followers_file, 'r', encoding='utf-8') as f:
                self.followers = json.load(f)

            # Converter para DataFrame para análise
            self.df = pd.DataFrame(self.followers)
            logger.info(f"✅ {len(self.followers)} seguidores carregados")
        except FileNotFoundError:
            logger.error(f"❌ Arquivo {self.followers_file} não encontrado")
        except Exception as e:
            logger.error(f"❌ Erro ao carregar dados: {str(e)}")

    def get_summary_stats(self) -> Dict:
        """Retorna estatísticas resumidas"""
        if self.df is None or self.df.empty:
            return {}

        stats = {
            'total_followers': len(self.df),
            'verified_accounts': len(self.df[self.df['is_verified'] == True]),
            'private_accounts': len(self.df[self.df['is_private'] == True]),
            'business_accounts': len(self.df[self.df['is_business_account'] == True]),
            'avg_followers': int(self.df['followers_count'].mean()),
            'avg_following': int(self.df['following_count'].mean()),
            'avg_posts': int(self.df['posts_count'].mean()),
            'with_external_url': len(self.df[self.df['external_url'].notna()]),
            'with_biography': len(self.df[self.df['biography'].notna()])
        }

        return stats

    def get_top_followers(self, n: int = 10) -> pd.DataFrame:
        """
        Retorna top N seguidores por número de seguidores

        Args:
            n: Número de seguidores a retornar

        Returns:
            DataFrame com top seguidores
        """
        if self.df is None or self.df.empty:
            return pd.DataFrame()

        top = self.df.nlargest(n, 'followers_count')[
            ['username', 'full_name', 'followers_count', 'posts_count', 'is_verified']
        ]

        return top

    def get_engagement_potential(self) -> pd.DataFrame:
        """
        Calcula potencial de engajamento
        (Seguidores com alto número de seguidores mas baixo following)
        """
        if self.df is None or self.df.empty:
            return pd.DataFrame()

        # Calcular ratio seguidores/seguindo
        self.df['follower_ratio'] = self.df['followers_count'] / (self.df['following_count'] + 1)

        # Filtrar contas com bom potencial
        # - Mínimo 1000 seguidores
        # - Ratio > 2 (seguem menos do que são seguidos)
        # - Não privadas
        high_potential = self.df[
            (self.df['followers_count'] >= 1000) &
            (self.df['follower_ratio'] > 2) &
            (self.df['is_private'] == False)
        ].nlargest(20, 'follower_ratio')[
            ['username', 'full_name', 'followers_count', 'following_count', 'follower_ratio']
        ]

        return high_potential

    def analyze_by_category(self) -> Dict:
        """Analisa seguidores por categoria/tipo"""
        if self.df is None or self.df.empty:
            return {}

        categories = {
            'micro_influencers': len(self.df[
                (self.df['followers_count'] >= 1000) &
                (self.df['followers_count'] < 10000)
            ]),
            'macro_influencers': len(self.df[
                (self.df['followers_count'] >= 10000) &
                (self.df['followers_count'] < 100000)
            ]),
            'mega_influencers': len(self.df[self.df['followers_count'] >= 100000]),
            'regular_users': len(self.df[self.df['followers_count'] < 1000]),
            'active_posters': len(self.df[self.df['posts_count'] >= 100]),
            'low_activity': len(self.df[self.df['posts_count'] < 10])
        }

        return categories

    def find_potential_leads(self, keywords: List[str]) -> pd.DataFrame:
        """
        Encontra potenciais leads baseado em palavras-chave na bio

        Args:
            keywords: Lista de palavras-chave para buscar

        Returns:
            DataFrame com potenciais leads
        """
        if self.df is None or self.df.empty:
            return pd.DataFrame()

        # Filtrar seguidores com biografia
        with_bio = self.df[self.df['biography'].notna()].copy()

        # Buscar por palavras-chave
        pattern = '|'.join(keywords)
        matches = with_bio[
            with_bio['biography'].str.contains(pattern, case=False, na=False)
        ][['username', 'full_name', 'biography', 'followers_count', 'external_url']]

        return matches

    def export_analysis_report(self, output_file: str = 'followers_analysis.json'):
        """
        Exporta relatório completo de análise

        Args:
            output_file: Nome do arquivo de saída
        """
        report = {
            'summary': self.get_summary_stats(),
            'top_followers': self.get_top_followers().to_dict('records'),
            'high_engagement_potential': self.get_engagement_potential().to_dict('records'),
            'categories': self.analyze_by_category()
        }

        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)

        logger.info(f"✅ Relatório exportado para {output_file}")

    def print_report(self):
        """Imprime relatório formatado no console"""
        print("\n" + "=" * 60)
        print("ANÁLISE DE SEGUIDORES DO INSTAGRAM")
        print("=" * 60)

        # Estatísticas gerais
        stats = self.get_summary_stats()
        print("\n📊 ESTATÍSTICAS GERAIS:")
        print(f"  Total de seguidores: {stats['total_followers']}")
        print(f"  Contas verificadas: {stats['verified_accounts']}")
        print(f"  Contas privadas: {stats['private_accounts']}")
        print(f"  Contas business: {stats['business_accounts']}")
        print(f"  Com link externo: {stats['with_external_url']}")
        print(f"\n  Média de seguidores: {stats['avg_followers']}")
        print(f"  Média de seguindo: {stats['avg_following']}")
        print(f"  Média de posts: {stats['avg_posts']}")

        # Top seguidores
        print("\n🏆 TOP 10 SEGUIDORES:")
        top = self.get_top_followers()
        for idx, row in top.iterrows():
            verified = "✓" if row['is_verified'] else " "
            print(f"  {verified} @{row['username']}: {row['followers_count']} seguidores")

        # Categorias
        print("\n📁 SEGUIDORES POR CATEGORIA:")
        cats = self.analyze_by_category()
        print(f"  Micro-influencers (1k-10k): {cats['micro_influencers']}")
        print(f"  Macro-influencers (10k-100k): {cats['macro_influencers']}")
        print(f"  Mega-influencers (100k+): {cats['mega_influencers']}")
        print(f"  Usuários regulares (<1k): {cats['regular_users']}")
        print(f"  Postadores ativos (100+ posts): {cats['active_posters']}")

        # Alto potencial de engajamento
        print("\n💎 ALTO POTENCIAL DE ENGAJAMENTO (Top 5):")
        potential = self.get_engagement_potential()
        for idx, row in potential.head(5).iterrows():
            print(f"  @{row['username']}: {row['followers_count']} seguidores, ratio {row['follower_ratio']:.1f}")

        print("\n" + "=" * 60)


def main():
    """Função principal"""
    import sys

    if len(sys.argv) < 2:
        print("Uso: python3 analyze_instagram_followers.py <arquivo_json>")
        print("\nExemplo:")
        print("  python3 analyze_instagram_followers.py instagram_followers_20251231.json")
        return

    followers_file = sys.argv[1]

    # Criar analytics
    analytics = FollowersAnalytics(followers_file)

    # Carregar dados
    analytics.load_data()

    if analytics.df is None or analytics.df.empty:
        print("❌ Nenhum dado para analisar")
        return

    # Imprimir relatório
    analytics.print_report()

    # Exportar relatório JSON
    analytics.export_analysis_report()

    # Exemplo: buscar leads
    print("\n" + "=" * 60)
    print("BUSCA DE LEADS POR PALAVRAS-CHAVE")
    print("=" * 60)

    keywords = input("\nDigite palavras-chave separadas por vírgula (ex: desenvolvedor,python,tech): ")
    if keywords.strip():
        keyword_list = [k.strip() for k in keywords.split(',')]
        leads = analytics.find_potential_leads(keyword_list)

        if not leads.empty:
            print(f"\n✅ {len(leads)} potenciais leads encontrados:")
            for idx, row in leads.head(10).iterrows():
                print(f"\n  @{row['username']}")
                print(f"  Nome: {row['full_name']}")
                print(f"  Bio: {row['biography'][:100]}...")
                if pd.notna(row['external_url']):
                    print(f"  Link: {row['external_url']}")
        else:
            print("❌ Nenhum lead encontrado com essas palavras-chave")


if __name__ == "__main__":
    main()
