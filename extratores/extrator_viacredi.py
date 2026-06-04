import fitz  
import pytesseract
from PIL import Image
import io
import re

pytesseract.pytesseract.tesseract_cmd = r'C:\Users\contabil07\AppData\Local\Programs\Tesseract-OCR\tesseract.exe'

def limpar_historico_viacredi(texto):
    """Filtro químico exclusivo para o layout do Viacredi (Ailos)"""
    
    lixo_ocr = [r'\bAILOS\b', r'\bSISTEMA DE COOPERATIVAS\b', r'\bEXTRATO\b', r'\bSALDO ANTERIOR\b', r'\bTOTAL\b', r'\bSAC\b', r'\bOUVIDORIA\b', r'\bCRÉDITO\b', r'\bDÉBITO\b']
    for padrao in lixo_ocr:
        texto = re.sub(padrao, '', texto, flags=re.IGNORECASE)
        
    texto = re.sub(r'(?:\s|^)[-=]?\s*\d{1,3}(?:\.\d{3})*,\d{2}(?!\d).*$', '', texto, flags=re.IGNORECASE)

    # CORREÇÃO: Remove datas mesmo que o dia tenha apenas 1 dígito (ex: 2/02/2026)
    texto = re.sub(r'\b\d{1,2}/\d{2}/\d{4}\b', '', texto)

    # CORREÇÃO: Limpa números de documentos mesmo se o OCR colocar espaços no ponto (ex: 772865 .209)
    texto = re.sub(r'\b\d+(?:\s*\.\s*\d+)+\b', '', texto)
    
    # Limpa caracteres sujos (como o '@' que apareceu no cabeçalho)
    texto = texto.replace('(', '').replace(')', '').replace('*', '').replace('-', ' ').replace('@', '')
    
    return " ".join(texto.split())

def extrair_dados_viacredi(caminho_pdf):
    print("\n" + "="*50)
    print(" FASE 3: MÁQUINA DE ESTADOS VIACREDI (AILOS) ")
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
    
    # CORREÇÃO: Agora a data pode começar com 1 ou 2 dígitos (\d{1,2})
    padrao_data = re.compile(r'(\d{1,2}/\d{2}/\d{4})')
    padrao_valor = re.compile(r'(?:^|\s)([-=]?)\s*(\d{1,3}(?:\.\d{3})*,\d{2})(?!\d)', re.IGNORECASE)

    # CORREÇÃO: Adicionamos variações com e sem acento para blindar o cabeçalho
    palavras_rodape = ["OS DADOS ACIMA", "OUVIDORIA", "SAC 0800", "SALDO ANTERIOR", "TOTAL", "PERÍODO", "PERIODO", "NOME:", "COOPERATIVA:"]

    for linha in linhas:
        linha_original = linha.strip()
        if not linha_original:
            continue

        # Blindagem do cabeçalho
        if any(rodape in linha_original.upper() for rodape in palavras_rodape):
            continue 

        busca_data = padrao_data.search(linha_original)

        if busca_data:
            # Pega a data encontrada e formata. Se for "2/02/2026", o zfill(10) preenche o zero: "02/02/2026"
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
                valor_limpo = re.sub(r'[-=]', '', valor_texto).replace('.', '').replace(',', '.')
                transacoes_estruturadas[-1]["Valor"] = float(valor_limpo) * multiplicador
                
        elif transacoes_estruturadas:
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
                    valor_limpo = re.sub(r'[-=]', '', valor_texto).replace('.', '').replace(',', '.')
                    transacoes_estruturadas[-1]["Valor"] = float(valor_limpo) * multiplicador

    for t in transacoes_estruturadas:
        t["Historico"] = limpar_historico_viacredi(t["Historico"])[:100].strip()

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