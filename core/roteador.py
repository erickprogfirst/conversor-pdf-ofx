import os
from extratores.extrator_sicoob import extrair_dados_sicoob
from extratores.extrator_santander import extrair_dados_santander
from extratores.extrator_viacredi_v3 import extrair_dados_viacredi_v3
from extratores.extrator_base import extrair_texto_primeira_pagina
from extratores.extrator_caixa import extrair_dados_caixa 
from extratores.extrator_viacredi import extrair_dados_viacredi 
from extratores.extrator_viacredi_v2 import extrair_dados_viacredi_v2
from extratores.extrator_safra import extrair_dados_safra
from extratores.extrator_inter import extrair_dados_inter
from extratores.extrator_pagbank import extrair_dados_pagbank 
from extratores.extrator_stone import extrair_dados_stone # <--- Novo Import
from core.gerador_ofx import gerar_ofx

def identificar_e_rotear(caminho_pdf):
    print(f"\nAnalisando o arquivo: {caminho_pdf}")
    
    texto_cabecalho_completo = extrair_texto_primeira_pagina(caminho_pdf)
    
    if not texto_cabecalho_completo:
        print("❌ Não foi possível ler o texto do PDF. Arquivo ignorado.")
        return
        
    texto_upper = texto_cabecalho_completo[:1000].upper()
    transacoes_limpas = []

    # =======================================================
    # A MESA DE ROTEAMENTO BLINDADA
    # =======================================================
    
    if "VIACREDI" in texto_upper or "AILOS" in texto_upper:
        if "VALOR EM R$" in texto_upper or "LANÇAMENTOS" in texto_upper:
            print("🏦 Banco Identificado: VIACREDI (LAYOUT 2 - CONTA CORRENTE)")
            transacoes_limpas = extrair_dados_viacredi_v2(caminho_pdf)
        else:
            # Se não for o Layout 2, usa automaticamente a nova V3 (Leitura Digital)
            print("🏦 Banco Identificado: VIACREDI (V3 - LEITURA DIGITAL)")
            transacoes_limpas = extrair_dados_viacredi_v3(caminho_pdf)

    elif "SICOOB" in texto_upper:
        print("🏦 Banco Identificado: SICOOB (LEITURA DIGITAL)")
        transacoes_limpas = extrair_dados_sicoob(caminho_pdf)
                
    elif "VIACREDI" in texto_upper:
        print("🏦 Banco Identificado: VIACREDI (V3 - LEITURA DIGITAL)")
        # AQUI ESTAVA O ERRO: Tem de chamar a função que tem o "_v3" no fim!
        transacoes_limpas = extrair_dados_viacredi_v3(caminho_pdf)

    elif "BANCO SAFRA" in texto_upper or " SAFRA " in texto_upper: 
        print("🏦 Banco Identificado: BANCO SAFRA")
        transacoes_limpas = extrair_dados_safra(caminho_pdf)
        
    elif "CAIXA ECON" in texto_upper or "CEF" in texto_upper:
        print("🏦 Banco Identificado: CAIXA ECONÔMICA FEDERAL")
        transacoes_limpas = extrair_dados_caixa(caminho_pdf)
        
    elif "PAGBANK" in texto_upper or "PAGSEGURO" in texto_upper:
        print("🏦 Banco Identificado: PAGBANK (PAGSEGURO)")
        transacoes_limpas = extrair_dados_pagbank(caminho_pdf)
        
    elif "BANCO INTER" in texto_upper or " INSTITUIÇÃO: BANCO INTER " in texto_upper or " INTER " in texto_upper: 
        print("🏦 Banco Identificado: BANCO INTER")
        transacoes_limpas = extrair_dados_inter(caminho_pdf)

    elif "SANTANDER" in texto_upper or "CONTAMAX" in texto_upper or "INTERNET BANKING EMPRESARIAL" in texto_upper:
        print("🏦 Banco Identificado: SANTANDER")
        transacoes_limpas = extrair_dados_santander(caminho_pdf)   

    # A Nova Regra da Stone
    elif "STONE" in texto_upper:
        print("🏦 Banco Identificado: STONE")
        transacoes_limpas = extrair_dados_stone(caminho_pdf)
        
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