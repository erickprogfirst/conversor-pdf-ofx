import fitz  
import pytesseract
from PIL import Image
import io
import re

pytesseract.pytesseract.tesseract_cmd = r'C:\Users\contabil07\AppData\Local\Programs\Tesseract-OCR\tesseract.exe'

def limpar_historico_viacredi_v2(texto):
    """Filtro químico focado no Layout 2 (Conta Corrente) do Viacredi/Ailos"""
    
    # Adicionamos os fragmentos do rodapé à lista de destruição
    lixo_ocr = [
        r'\bAILOS\b', r'\bSISTEMA DE COOPERATIVAS\b', r'\bExtrato conta corrente\b', 
        r'\bSALDO ANTERIOR\b', r'\bLançamentos\b', r'\bValor em R\$\b', r'\bSaldo em R\$\b',
        r'\bPagina\b', r'\bDocumento:\b', r'\bBalanço final\b', r'\bEntradas e saídas\b',
        r'\bViacredi\s*-\s*CNPJ\b', r'\bViacredi CNPJ\b', r'\bSAC\s*[-]?\s*0800\b', r'\bOUVIDORIA\b'
    ]
    for padrao in lixo_ocr:
        texto = re.sub(padrao, '', texto, flags=re.IGNORECASE)
        
    # A GUILHOTINA INFALÍVEL
    texto = re.sub(r'(?:\s|^)[-]?[\d.,]+\s+[-]?[\d.,]+\s*$', '', texto)
    texto = re.sub(r'(?:\s|^)[-]?[\d.,]+\s*$', '', texto)

    # Remove a data 
    texto = re.sub(r'\b\d{1,2}/\d{2}/\d{4}\b', '', texto)
    
    # Corretor de OCR e sujeiras
    texto = re.sub(r'\b10F\b', 'IOF', texto, flags=re.IGNORECASE)
    texto = re.sub(r'\b3UROS\b', 'JUROS', texto, flags=re.IGNORECASE)
    texto = re.sub(r'[-_—–|@]', ' ', texto)
    texto = texto.replace('(', '').replace(')', '').replace('*', '')
    texto = re.sub(r'^[^\w\s]+|[^\w\s]+$', '', texto.strip())
    
    return " ".join(texto.split())

def extrair_dados_viacredi_v2(caminho_pdf):
    print("\n" + "="*50)
    print(" FASE 3: MÁQUINA DE ESTADOS VIACREDI (LAYOUT 2 - ESCUDO DE RODAPÉ) ")
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
    
    padrao_data = re.compile(r'(\d{1,2}/\d{2}/\d{4})')
    padrao_valores_finais = re.compile(r'([-]?[\d.,]+)\s+([-]?[\d.,]+)\s*$')

    # Adicionamos as palavras do rodapé ao firewall para fechar a porta
    gatilhos_fechar_porta = [
        "EXTRATO CONTA CORRENTE", "SALDO INICIAL", "ENTRADAS E SAÍDAS", 
        "BALANÇO FINAL", "DATA", "LANÇAMENTOS", "VALOR EM R$", "SALDO EM R$", 
        "PAGINA", "SALDO ANTERIOR", "EMITIDO EM",
        "VIACREDI - CNPJ", "VIACREDI CNPJ", "SAC 0800", "SAC - 0800", "OUVIDORIA"
    ]

    porta_aberta = False

    for linha in linhas:
        linha_original = linha.strip()
        if not linha_original:
            continue

        if any(bloqueio in linha_original.upper() for bloqueio in gatilhos_fechar_porta):
            porta_aberta = False
            continue 

        busca_data = padrao_data.search(linha_original)

        if busca_data:
            porta_aberta = True
            data_memoria = busca_data.group(1).zfill(10)
            
            transacoes_estruturadas.append({
                "Data": data_memoria,
                "Historico": limpar_historico_viacredi_v2(linha_original),
                "Valor": 0.0 
            })
            
            busca_finais = padrao_valores_finais.search(linha_original)
            if busca_finais:
                valor_transacao_str = busca_finais.group(1)
                
                numeros_puros = re.sub(r'[^\d]', '', valor_transacao_str)
                
                if len(numeros_puros) >= 3:
                    inteiros = numeros_puros[:-2]
                    centavos = numeros_puros[-2:]
                    valor_limpo = float(f"{inteiros}.{centavos}")
                elif len(numeros_puros) > 0:
                    valor_limpo = float(numeros_puros) / 100
                else:
                    valor_limpo = 0.0
                
                multiplicador = 1
                palavras_debito = ['DEBITO', 'PG.P/', 'PG.', 'TR.INTERNET', 'TR. INTERNET', 'IOF', 'JUROS', 'LIQ.COB', 'DB.', 'DEB.', 'TARIFA', 'SAQ.', 'PAGADOR', 'BAIXA BOLETO', 'CONSORCIO']
                if any(p in linha_original.upper() for p in palavras_debito):
                    multiplicador = -1
                    
                transacoes_estruturadas[-1]["Valor"] = valor_limpo * multiplicador
                
        elif porta_aberta and transacoes_estruturadas:
            texto_complemento = limpar_historico_viacredi_v2(linha_original)
            if texto_complemento:
                transacoes_estruturadas[-1]["Historico"] += f" {texto_complemento}"
                
            if transacoes_estruturadas[-1]["Valor"] == 0.0:
                busca_finais = padrao_valores_finais.search(linha_original)
                if busca_finais:
                    valor_transacao_str = busca_finais.group(1)
                    
                    numeros_puros = re.sub(r'[^\d]', '', valor_transacao_str)
                    if len(numeros_puros) >= 3:
                        inteiros = numeros_puros[:-2]
                        centavos = numeros_puros[-2:]
                        valor_limpo = float(f"{inteiros}.{centavos}")
                    elif len(numeros_puros) > 0:
                        valor_limpo = float(numeros_puros) / 100
                    else:
                        valor_limpo = 0.0
                    
                    multiplicador = 1
                    palavras_debito = ['DEBITO', 'PG.P/', 'PG.', 'TR.INTERNET', 'TR. INTERNET', 'IOF', 'JUROS', 'LIQ.COB', 'DB.', 'DEB.', 'TARIFA', 'SAQ.', 'PAGADOR', 'BAIXA BOLETO', 'CONSORCIO']
                    if any(p in linha_original.upper() for p in palavras_debito):
                        multiplicador = -1
                        
                    transacoes_estruturadas[-1]["Valor"] = valor_limpo * multiplicador

    for t in transacoes_estruturadas:
        t["Historico"] = limpar_historico_viacredi_v2(t["Historico"])[:100].strip()

    # MÓDULO ANTI-DUPLICIDADE
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