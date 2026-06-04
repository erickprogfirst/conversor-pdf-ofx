import os
from core.roteador import identificar_e_rotear

def iniciar_sistema():
    pasta_pdfs = "pdfs_teste"
    
    # Verifica se a pasta existe
    if not os.path.exists(pasta_pdfs):
        print(f"Erro: A pasta '{pasta_pdfs}' não existe.")
        return

    # Lista todos os arquivos que terminam com .pdf dentro da pasta
    arquivos = [arq for arq in os.listdir(pasta_pdfs) if arq.lower().endswith('.pdf')]

    if not arquivos:
        print(f"Nenhum arquivo PDF encontrado na pasta '{pasta_pdfs}'.")
        return

    print(f"Iniciando o processamento em lote de {len(arquivos)} arquivo(s)...\n")

    # Faz um loop para ler cada PDF encontrado
    for arquivo in arquivos:
        caminho_completo = os.path.join(pasta_pdfs, arquivo)
        identificar_e_rotear(caminho_completo)
        print("\n" + "="*50 + "\n")

if __name__ == "__main__":
    iniciar_sistema()