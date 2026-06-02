import os
from core.roteador import identificar_e_rotear

# Caminho do seu arquivo de teste (Cuidado com letras maiúsculas e minúsculas!)
ARQUIVO_TESTE = "pdfs_teste/extrato_exemplo.pdf"

def main():
    # Verifica se você realmente colocou o PDF na pasta certa
    if not os.path.exists(ARQUIVO_TESTE):
        print(f"ERRO: O arquivo '{ARQUIVO_TESTE}' não foi encontrado!")
        print("1. Verifique se a pasta 'pdfs_teste' existe.")
        print("2. Verifique se o seu PDF está lá dentro com o nome 'extrato_exemplo.pdf'.")
        return
        
    # Se achou o arquivo, chama o roteador!
    identificar_e_rotear(ARQUIVO_TESTE)

if __name__ == "__main__":
    main()