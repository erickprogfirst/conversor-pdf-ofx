import os
from extratores.extrator_base import extrair_texto_primeira_pagina
from extratores.extrator_caixa import extrair_dados_caixa 
from extratores.extrator_viacredi import extrair_dados_viacredi 
from extratores.extrator_viacredi_v2 import extrair_dados_viacredi_v2 # <--- NOVO IMPORT
from extratores.extrator_safra import extrair_dados_safra
from extratores.extrator_inter import extrair_dados_inter
from extratores.extrator_pagbank import extrair_dados_pagbank 
from core.gerador_ofx import gerar_ofx

def identificar_e_rotear(caminho_pdf):
    print(f"\nAnalisando o arquivo: {caminho_pdf}")
    
    texto_cabecalho = extrair_texto_primeira_pagina(caminho_pdf)
    
    if not texto_cabecalho:
        print("❌ Não foi possível ler o texto do PDF. Arquivo ignorado.")
        return
        
    texto_upper = texto_cabecalho.upper()
    transacoes_limpas = []

    # =======================================================
    # A MESA DE ROTEAMENTO 
    # =======================================================
    
    if "VIACREDI" in texto_upper or "AILOS" in texto_upper: 
        # A recepcionista verifica as colunas para decidir o layout
        if "VALOR EM R$" in texto_upper or "LANÇAMENTOS" in texto_upper:
            print("🏦 Banco Identificado: VIACREDI (LAYOUT 2 - CONTA CORRENTE)")
            transacoes_limpas = extrair_dados_viacredi_v2(caminho_pdf)
        else:
            print("🏦 Banco Identificado: VIACREDI (LAYOUT 1 - PADRÃO)")
            transacoes_limpas = extrair_dados_viacredi(caminho_pdf)
        
    elif "CAIXA ECON" in texto_upper or "CEF" in texto_upper:
        print("🏦 Banco Identificado: CAIXA ECONÔMICA FEDERAL")
        transacoes_limpas = extrair_dados_caixa(caminho_pdf)
        
    elif "SAFRA" in texto_upper: 
        print("🏦 Banco Identificado: BANCO SAFRA")
        transacoes_limpas = extrair_dados_safra(caminho_pdf)
        
    elif "PAGBANK" in texto_upper or "PAGSEGURO" in texto_upper:
        print("🏦 Banco Identificado: PAGBANK (PAGSEGURO)")
        transacoes_limpas = extrair_dados_pagbank(caminho_pdf)
        
    elif "BANCO INTER" in texto_upper or " INSTITUIÇÃO: BANCO INTER " in texto_upper or " INTER " in texto_upper: 
        print("🏦 Banco Identificado: BANCO INTER")
        transacoes_limpas = extrair_dados_inter(caminho_pdf)
        
    else:
        print("⚠️ Banco não mapeado no sistema ou não identificado pelo cabeçalho.")
        return
    
    # =======================================================
    # GERAÇÃO DO ARQUIVO FINAL
    # =======================================================
    if transacoes_limpas:
        nome_arquivo_original = os.path.basename(caminho_pdf)
        nome_arquivo_ofx = nome_arquivo_original.lower().replace(".pdf", ".ofx")
        
        gerar_ofx(transacoes_limpas, caminho_saida=nome_arquivo_ofx)