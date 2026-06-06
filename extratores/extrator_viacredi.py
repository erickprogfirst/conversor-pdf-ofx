import fitz  
import pytesseract
from PIL import Image
import io
import re

pytesseract.pytesseract.tesseract_cmd = r'C:\Users\contabil07\AppData\Local\Programs\Tesseract-OCR\tesseract.exe'

def limpar_historico_viacredi(texto):
    """Filtro químico do Viacredi com corretor ortográfico de OCR"""
    
    lixo_ocr = [
        r'\bAILOS\b', r'\bSISTEMA DE COOPERATIVAS\b', r'\bEXTRATO\b', 
        r'\bSALDO ANTERIOR\b', r'\bTOTAL\b', r'\bSAC\b', r'\bOUVIDORIA\b', 
        r'\bCRÉDITO\b', r'\bDÉBITO\b'
    ]
    for padrao in lixo_ocr:
        texto = re.sub(padrao, '', texto, flags=re.IGNORECASE)
        
    # CORREÇÃO 1: Tolerância a espaços injetados nos valores (ex: 548, 00)
    texto = re.sub(r'(?:\s|^)[-=]?\s*\d{1,3}(?:\s*\.\s*\d{3})*\s*,\s*\d{2}(?!\d).*$', '', texto, flags=re.IGNORECASE)
    
    texto = re.sub(r'\b\d{1,2}/\d{2}/\d{4}\b', '', texto)
    texto = re.sub(r'\b\d+(?:\s*\.\s*\d+)+\b', '', texto)
    
    # CORREÇÃO 2: Corretor Ortográfico de OCR
    texto = re.sub(r'\b10F\b', 'IOF', texto, flags=re.IGNORECASE)
    texto = re.sub(r'\b3UROS\b', 'JUROS', texto, flags=re.IGNORECASE)

    texto = re.sub(r'[-_—–|@]', ' ', texto)
    texto = texto.replace('(', '').replace(')', '').replace('*', '')
    texto = re.sub(r'^[^\w\s]+|[^\w\s]+$', '', texto.strip())
    
    return " ".join(texto.split())

def extrair_dados_viacredi(caminho_pdf):
    print("\n" + "="*50)
    print(" FASE 3: MÁQUINA DE ESTADOS VIACREDI (CORRETOR DE SINAL ATIVADO) ")
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
    
    # CORREÇÃO 1: Radar flexível que aceita "548, 00" ou "28, 28"
    padrao_valor = re.compile(r'(?:^|\s)([-=]?)\s*(\d{1,3}(?:\s*\.\s*\d{3})*\s*,\s*\d{2})(?!\d)', re.IGNORECASE)

    gatilhos_fechar_porta = [
        "OS DADOS ACIMA", "OUVIDORIA", "SAC 0800", "SALDO ANTERIOR", "TOTAL", 
        "PERÍODO", "PERIODO", "NOME:", "COOPERATIVA:", "EMITIDO EM", 
        "DATA", "DESCRIÇÃO", "DOCUMENTO", "CRÉDITO", "DÉBITO", "SALDO (",
        "AILOS", "SISTEMA DE COOPERATIVAS", "EXTRATO"
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
                "Historico": limpar_historico_viacredi(linha_original),
                "Valor": 0.0 
            })
            
            valores_encontrados = padrao_valor.findall(linha_original)
            if valores_encontrados:
                if len(valores_encontrados) >= 2:
                    sinal, valor_texto = valores_encontrados[-2]
                else:
                    sinal, valor_texto = valores_encontrados[0]
                    
                multiplicador = -1 if ('-' in sinal or '=' in sinal or '-' in valor_texto or '=' in valor_texto) else 1
                
                # CORREÇÃO 3: O Scanner de Sinal Inteligente
                # Se o OCR perdeu o sinal de menos, o contexto salva a matemática.
                palavras_debito = ['DEBITO', 'PG.P/', 'TR.INTERNET', 'TR. INTERNET', 'IOF', 'JUROS', 'LIQ.COB', 'DB.', 'DEB.', 'TARIFA', 'SAQ.', 'PAGADOR', 'BAIXA BOLETO', 'CONSORCIO']
                if multiplicador == 1:
                    if any(p in linha_original.upper() for p in palavras_debito):
                        multiplicador = -1
                
                # Limpa os espaços acidentais antes de transformar em número
                valor_limpo = re.sub(r'[-=\s]', '', valor_texto).replace('.', '').replace(',', '.')
                transacoes_estruturadas[-1]["Valor"] = float(valor_limpo) * multiplicador
                
        elif porta_aberta and transacoes_estruturadas:
            texto_complemento = limpar_historico_viacredi(linha_original)
            if texto_complemento:
                transacoes_estruturadas[-1]["Historico"] += f" {texto_complemento}"
                
            if transacoes_estruturadas[-1]["Valor"] == 0.0:
                valores_encontrados = padrao_valor.findall(linha_original)
                if valores_encontrados:
                    if len(valores_encontrados) >= 2:
                        sinal, valor_texto = valores_encontrados[-2]
                    else:
                        sinal, valor_texto = valores_encontrados[0]
                        
                    multiplicador = -1 if ('-' in sinal or '=' in sinal or '-' in valor_texto or '=' in valor_texto) else 1
                    
                    palavras_debito = ['DEBITO', 'PG.P/', 'TR.INTERNET', 'TR. INTERNET', 'IOF', 'JUROS', 'LIQ.COB', 'DB.', 'DEB.', 'TARIFA', 'SAQ.', 'PAGADOR', 'BAIXA BOLETO', 'CONSORCIO']
                    if multiplicador == 1:
                        if any(p in linha_original.upper() for p in palavras_debito):
                            multiplicador = -1
                            
                    valor_limpo = re.sub(r'[-=\s]', '', valor_texto).replace('.', '').replace(',', '.')
                    transacoes_estruturadas[-1]["Valor"] = float(valor_limpo) * multiplicador

    for t in transacoes_estruturadas:
        t["Historico"] = limpar_historico_viacredi(t["Historico"])[:100].strip()

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