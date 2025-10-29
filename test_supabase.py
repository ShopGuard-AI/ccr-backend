"""
Script para testar conexão com Supabase e verificar estrutura do banco
Execute este script para verificar se tudo está configurado corretamente
"""

from supabase_client import db

def test_connection():
    """Testa conexão com Supabase"""
    print("=" * 60)
    print("TESTE DE CONEXÃO SUPABASE")
    print("=" * 60)

    if not db.is_connected():
        print("[ERROR] ERRO: Não foi possível conectar ao Supabase")
        print("   Verifique as credenciais no arquivo .env")
        return False

    print("[OK] Conectado ao Supabase com sucesso!")
    print()

    # Testa consulta nas tabelas
    print("-" * 60)
    print("Verificando tabelas...")
    print("-" * 60)

    try:
        # Testa tabela cameras
        cameras = db.get_all_cameras()
        print(f"[OK] Tabela 'cameras': {len(cameras)} registros")

        # Testa view de estatísticas em tempo real
        stats = db.get_realtime_stats()
        print(f"[OK] View 'camera_stats_realtime': {len(stats)} registros")

        print()
        print("=" * 60)
        print("TODAS AS TABELAS ESTÃO FUNCIONANDO!")
        print("=" * 60)
        print()
        print("O sistema está pronto para uso. Você pode:")
        print("1. Adicionar câmeras pela interface web")
        print("2. Configurar áreas de estacionamento")
        print("3. Iniciar o monitoramento em tempo real")
        print()
        print("Os dados serão salvos automaticamente no Supabase:")
        print("  - Configurações de câmeras")
        print("  - Áreas de estacionamento")
        print("  - Histórico de ocupação (a cada 60 segundos)")
        print("  - Eventos do sistema")
        print()

        return True

    except Exception as e:
        print(f"[ERROR] ERRO ao acessar tabelas: {e}")
        print()
        print("AÇÃO NECESSÁRIA:")
        print("Execute o arquivo 'supabase_schema.sql' no SQL Editor do Supabase")
        print("para criar todas as tabelas necessárias.")
        print()
        print("Passos:")
        print("1. Acesse https://supabase.com/dashboard")
        print("2. Selecione seu projeto 'monitoramento-vaga-ccr'")
        print("3. Vá em 'SQL Editor' no menu lateral")
        print("4. Clique em 'New Query'")
        print("5. Cole o conteúdo do arquivo 'supabase_schema.sql'")
        print("6. Clique em 'Run' para executar")
        print("7. Execute este script novamente")
        print()
        return False


if __name__ == "__main__":
    test_connection()
