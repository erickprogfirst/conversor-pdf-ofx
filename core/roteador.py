from extratores.extrator_base import extrair_texto_primeira_pagina
from extratores.banco_generico import extrair_dados_brutos
from core.gerador_ofx import gerar_ofx # <--- Importamos o gerador novo

def identificar_e_rotear(caminho_pdf):
    print(f"Analisando o arquivo: {caminho_pdf}")
    texto_cabecalho = extrair_texto_primeira_pagina(caminho_pdf)
    
    if not texto_cabecalho:
        print("Não foi possível extrair texto do PDF. Ele pode ser uma imagem digitalizada.")
        return
        
    print("Enviando arquivo para o leitor genérico para análise visual...\n")
    
    # 1. Extrai a lista de transações limpas
    transacoes_limpas = extrair_dados_brutos(caminho_pdf)
    
    # 2. Manda a lista para o gerador construir o arquivo final
    if transacoes_limpas:
        gerar_ofx(transacoes_limpas)