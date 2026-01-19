#!/usr/bin/env python3
"""
Teste de qualidade de mensagens personalizadas.
Compara geração de hooks para perfis ricos.
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'implementation'))

from message_generator import MessageGenerator, generate_message

# Perfil do Dr. Yuri (dados reais do screenshot)
dr_yuri_profile = {
    'username': 'dr_yuri_bassotto',
    'full_name': 'Yuri Bassotto Faria Lima',
    'bio': '''Cirurgião Plástico | Fundador da @plasticacenterbr @plasticafast @farialimaclinic
📍 USA | República Dominicana | México
🔹 Mamas | Lipoaspiração | Abdominoplastia
🔹 Especialista em procedimentos corporais''',
    'is_verified': True,
    'follower_count': 5778,
    'following_count': 1200,
    'is_business_account': True
}

# Score data simulado
dr_yuri_score = {
    'total_score': 85,
    'priority': 'HOT',
    'detected_profession': 'médico',
    'detected_interests': ['estética', 'saúde'],
    'detected_location': 'São Paulo'
}

# Perfil comum (para comparação)
dr_comum_profile = {
    'username': 'dr_comum',
    'full_name': 'Dr. João Silva',
    'bio': 'Médico | Consultório em SP',
    'is_verified': False,
    'follower_count': 500
}

dr_comum_score = {
    'total_score': 55,
    'priority': 'WARM',
    'detected_profession': 'médico',
    'detected_interests': ['saúde'],
    'detected_location': 'São Paulo'
}

def test_messages():
    generator = MessageGenerator()

    print("=" * 60)
    print("TESTE DE PERSONALIZAÇÃO DE MENSAGENS")
    print("=" * 60)

    # Teste 1: Dr. Yuri (perfil rico)
    print("\n" + "=" * 60)
    print("PERFIL RICO: Dr. Yuri Bassotto")
    print("=" * 60)
    print(f"Bio: {dr_yuri_profile['bio'][:100]}...")
    print(f"Verificado: {dr_yuri_profile['is_verified']}")
    print(f"Followers: {dr_yuri_profile['follower_count']}")

    print("\n--- Gerando 5 mensagens ---\n")
    for i in range(5):
        msg = generator.generate(dr_yuri_profile, dr_yuri_score)
        print(f"[{i+1}] Nível: {msg.personalization_level}")
        print(f"    Hooks: {msg.hooks_used}")
        print(f"    Confiança: {msg.confidence}")
        print(f"\n{msg.message}")
        print("-" * 40)

    # Teste 2: Dr. Comum (perfil básico)
    print("\n" + "=" * 60)
    print("PERFIL BÁSICO: Dr. João Silva")
    print("=" * 60)
    print(f"Bio: {dr_comum_profile['bio']}")
    print(f"Verificado: {dr_comum_profile.get('is_verified', False)}")
    print(f"Followers: {dr_comum_profile.get('follower_count', 0)}")

    print("\n--- Gerando 3 mensagens ---\n")
    for i in range(3):
        msg = generator.generate(dr_comum_profile, dr_comum_score)
        print(f"[{i+1}] Nível: {msg.personalization_level}")
        print(f"\n{msg.message}")
        print("-" * 40)

    # Teste 3: Modo Híbrido (spintax)
    print("\n" + "=" * 60)
    print("MODO HÍBRIDO (Spintax) - Dr. Yuri")
    print("=" * 60)

    print("\n--- 3 variações com spintax ---\n")
    for i in range(3):
        msg = generator.generate_hybrid(dr_yuri_profile, dr_yuri_score)
        print(f"[{i+1}] Template: {msg.template_used}")
        print(f"\n{msg.message}")
        print("-" * 40)

if __name__ == "__main__":
    test_messages()
