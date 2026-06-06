import fitz  
import pytesseract
from PIL import Image
import io
import re

pytesseract.pytesseract.tesseract_cmd = r'C:\Users\contabil07\AppData\Local\Programs\Tesseract-OCR\tesseract.exe'

def limpar_historico_pagbank(texto):
    """Filtro químico focado no layout do PagBank / PagSeguro"""
    
    # 1. Limpa cabeçalhos e lixo de repetição das quebras de página
    lixo_ocr = [
        r'\bPagBank\b', r'\bExtrato da conta\b', r'\bEmitido em\b', r'\bPeriodo\b', 
        r'\bCNPJ\b', r'\bAgência\b', r'\bConta\b', r'\bData\b', r'\bDescrição\b', 
        r'\bValor\b', r'\bSaldo do dia\b', r'\bPagSeguro Internet\b', r'\bPágina\b'
    ]
    for padrao in lixo_ocr:
        texto = re.sub(padrao, '', texto, flags=re.IGNORECASE)
        
    # 2. Desintegra o dinheiro no final da linha (com ou sem o R$)
    texto = re.sub(r'(?:\s|^)[-=]?\s*(?:R\$|RS|R\s\$)?\s*[-=]?\s*\d{1,3}(?:\.\d{3})*,\d{2}(?!\d).*$', '', texto, flags=re.IGNORECASE)
    
    # 3. Remove a data (DD/MM/AAAA) para não duplicar no histórico
    texto = re.sub(r'\b\d{2}/\d{2}/\d{4}\b', '', texto)
    
    # 4. Limpeza de traços de tabelas e pontuações perdidas
    texto = re.sub(r'[-_—–|@]', ' ', texto)
    texto = texto.replace('(', '').replace(')', '').replace('*', '')
    texto = re.sub(r'^[^\w\s]+|[^\w\s]+$', '', texto.strip())
    
    return " ".join(texto.split())

def extrair_dados_pagbank(caminho_pdf):
    print("\n" + "="*50)
    print(" FASE 3: MÁQUINA DE ESTADOS PAGBANK (PAGSEGURO) ")
    print("="*50 + "\n")
    
    texto_completo = ""
    
    try:
        doc = fitz.open(caminho_pdf)
        for numero_pagina in range(len(doc)):
            pagina = doc.load_page(numero_pagina)
            matriz = fitz.Matrix(2.0, 2.0)
            pix = pagina.get_pixmap(matrix=matriz)
            imagem = Image.open(io.BytesIO(pix.tobytes("png")))
            texto_extraido = pytesseract.image_to_string(imagem, config=r'--psm 6')
            texto_completo += texto_extraido + "\n"
    except Exception as e:
        print(f"Erro no OCR: {e}")
        return []

    linhas = texto_completo.split('\n')
    transacoes_estruturadas = []
    
    # O Pagbank usa a data clássica DD/MM/AAAA
    padrao_data = re.compile(r'(\d{2}/\d{2}/\d{4})')
    # O radar capta o valor e o seu sinal (+ ou -)
    padrao_valor = re.compile(r'(?:^|\s)([-=]?)\s*(?:R\$|RS|R\s\$)?\s*([-=]?)\s*(\d{1,3}(?:\.\d{3})*,\d{2})(?!\d)', re.IGNORECASE)

    # GATILHOS DO FIREWALL DE PÁGINA (Ignora a linha se tiver estas palavras)
    gatilhos_fechar_porta = [
        "PAGBANK", "EXTRATO DA CONTA", "EMITIDO EM", "PERIODO:", 
        "CNPJ:", "AGÊNCIA", "AGENCIA", "CONTA", "SALDO DO DIA", "PAGSEGURO"
    ]
    
    porta_aberta = False

    for linha in linhas:
        linha_original = linha.strip()
        if not linha_original:
            continue

        # 1. BLOQUEIO DE CABEÇALHO/RODAPÉ
        if any(bloqueio in linha_original.upper() for bloqueio in gatilhos_fechar_porta):
            porta_aberta = False
            continue 

        busca_data = padrao_data.search(linha_original)

        # 2. ABERTURA DE NOVA TRANSAÇÃO
        if busca_data:
            porta_aberta = True
            data_memoria = busca_data.group(1)
            
            transacoes_estruturadas.append({
                "Data": data_memoria,
                "Historico": limpar_historico_pagbank(linha_original),
                "Valor": 0.0 
            })
            
            valores_encontrados = padrao_valor.findall(linha_original)
            if valores_encontrados:
                sinal1, sinal2, valor_texto = valores_encontrados[-1]
                multiplicador = -1 if ('-' in sinal1 or '=' in sinal1 or '-' in sinal2 or '=' in sinal2) else 1
                
                valor_limpo = float(valor_texto.replace('.', '').replace(',', '.')) * multiplicador
                transacoes_estruturadas[-1]["Valor"] = valor_limpo
                
        # 3. CONTINUAÇÃO DO HISTÓRICO (Se a porta estiver aberta)
        elif porta_aberta and transacoes_estruturadas:
            texto_complemento = limpar_historico_pagbank(linha_original)
            if texto_complemento:
                transacoes_estruturadas[-1]["Historico"] += f" {texto_complemento}"
                
            if transacoes_estruturadas[-1]["Valor"] == 0.0:
                valores_encontrados = padrao_valor.findall(linha_original)
                if valores_encontrados:
                    sinal1, sinal2, valor_texto = valores_encontrados[-1]
                    multiplicador = -1 if ('-' in sinal1 or '=' in sinal1 or '-' in sinal2 or '=' in sinal2) else 1
                    
                    valor_limpo = float(valor_texto.replace('.', '').replace(',', '.')) * multiplicador
                    transacoes_estruturadas[-1]["Valor"] = valor_limpo

    # Formatação final das descrições
    for t in transacoes_estruturadas:
        t["Historico"] = limpar_historico_pagbank(t["Historico"])[:100].strip()

    # MÓDULO ANTI-DUPLICIDADE (Para o seu sistema contábil aceitar os PDFs)
    transacoes_finais = [t for t in transacoes_estruturadas if t["Valor"] != 0.0]
    frequencia_transacoes = {}
    
    for t in transacoes_finais:
        assinatura = f"{t['Data']}|{t['Historico']}|{t['Valor']}"
        if assinatura in frequencia_transacoes:
            frequencia_transacoes[assinatura] += 1
            t["Historico"] = f"{t['Historico']} {frequencia_transacoes[assinatura]:02d}"
        else:
            frequencia_transacoes[assinatura] = 1

    print(f"✅ Encontradas {len(transacoes_finais)} transações prontas para o OFX:\n")
    for t in transacoes_finais:
        print(t)

    return transacoes_finais