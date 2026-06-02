from extratores.extrator_base import extrair_texto_primeira_pagina
from extratores.banco_generico import extrair_dados_brutos

def identificar_e_rotear(caminho_pdf):
    print(f"Analisando o arquivo: {caminho_pdf}")
    
    texto_cabecalho = extrair_texto_primeira_pagina(caminho_pdf)
    
    if not texto_cabecalho:
        print("Não foi possível extrair texto do PDF. Ele pode ser uma imagem digitalizada.")
        return
        
    # Por enquanto, como estamos na fase de descoberta, 
    # vamos mandar direto para o nosso leitor genérico para você ver o layout!
    print("Enviando arquivo para o leitor genérico para análise visual...\n")
    extrair_dados_brutos(caminho_pdf)