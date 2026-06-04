import fitz  
import pytesseract
from PIL import Image
import io
import re

pytesseract.pytesseract.tesseract_cmd = r'C:\Users\contabil07\AppData\Local\Programs\Tesseract-OCR\tesseract.exe'

def limpar_historico(texto):
    """Filtro químico com blindagem contra estilhaços de datas e escudo Anti-CPF"""
    
    lixo_ocr = [r'\bCEREN\b', r'\bGATS\b', r'\bAIXA\b', r'\bCNPJ\b', r'\bDATA\b', r'\bEE\b', r'\bEPEE\b', r'\bCNPI\b']
    for padrao in lixo_ocr:
        texto = re.sub(padrao, '', texto, flags=re.IGNORECASE)
        
    texto = texto.replace('£', '').replace('¢', '')
    texto = re.sub(r'(?i)\b(ren|even|inate)\b', '', texto)
    
    # CORREÇÃO: O (?!\d) e o (?:\s|^) garantem que a IA não corte CPFs no meio (ex: 43,06 de 3.43,063)
    texto = re.sub(r'(?:\s|^)[-=]?\s*(?:R\$|RS|R\s\$)?\s*[-=]?\s*\d{1,3}(?:\.\d{3})*,\d{2}(?!\d).*$', '', texto, flags=re.IGNORECASE)

    texto = re.sub(r'\b\d{2}/\d{2}(?:/\d{4})?(?:\s+\d{2}:\d{2})?\b', '', texto)
    texto = re.sub(r'\b\d{1,3}\s+\d{2}:\d{2}\b', '', texto) 
    texto = re.sub(r'\b\d{2}:\d{2}\b', '', texto)
    
    texto = re.sub(r'\s+/\d{2,4}\b', '', texto)
    texto = re.sub(r'\b\d{1,3}\s+(SALARIO)\b', r'\1', texto, flags=re.IGNORECASE)
    texto = re.sub(r'/\s+(SALARIO)\b', r'\1', texto, flags=re.IGNORECASE)
    
    texto = re.sub(r'[A-Z0-9]{25,}', '', texto)
    texto = re.sub(r'\b\d{6,}\b', '', texto)
    
    texto = texto.replace('(', '').replace(')', '').replace('*', '').replace('-', ' ')
    
    return " ".join(texto.split())

def extrair_dados_caixa(caminho_pdf):
    print("\n" + "="*50)
    print(" FASE 3: MÁQUINA DE ESTADOS CAIXA ECONÔMICA (ESCUDO ANTI-CPF) ")
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
    data_memoria = None
    
    padrao_data = re.compile(r'(\d{2}/\d{2}/\d{4})')
    
    # CORREÇÃO: O Radar de dinheiro agora exige espaço antes e não permite outro número grudado depois
    padrao_valor = re.compile(r'(?:^|\s)([-=]?)\s*(?:R\$|RS|R\s\$)?\s*([-=]?)\s*(\d{1,3}(?:\.\d{3})*,\d{2})(?!\d)', re.IGNORECASE)

    gatilhos_nova = ["PIX RECEBIDO", "ENVIO TRANSF INTERNET", "DEPOSITO DINH LOTERICO", "MENSALIDADE CESTA SERVICO", "TARIFA RENOVACAO CADASTRO", "SEGURADORA", "TARIFA PIX QR CODE VENDA SAFRAPAY"]
    palavras_rodape = ["SALDO DIA", "SAC CAIXA", "OUVIDORIA", "DEFICIÊNCIA", "ALÉ CAI", "ALÉ CAIXA", "GERENCIADOR"]

    ignorar_captura = True 

    for linha in linhas:
        linha_original = linha

        busca_data = padrao_data.search(linha_original)
        if busca_data:
            data_memoria = busca_data.group(1)

        if any(rodape in linha_original.upper() for rodape in palavras_rodape):
            ignorar_captura = True
            continue 

        linha_limpa_teste = limpar_historico(linha_original)
        gatilho_encontrado = None
        for g in gatilhos_nova:
            if g in linha_limpa_teste.upper():
                gatilho_encontrado = g
                break

        if gatilho_encontrado:
            ignorar_captura = False 
            idx = linha_original.upper().find(gatilho_encontrado)
            hist_bruto = linha_original[idx:]
            
            transacoes_estruturadas.append({
                "Data": data_memoria,
                "Historico": limpar_historico(hist_bruto),
                "Valor": 0.0 
            })
            
        valores_encontrados = padrao_valor.findall(linha_original)
        if valores_encontrados and transacoes_estruturadas and not ignorar_captura:
            sinal_antes, sinal_depois, valor_texto = valores_encontrados[0]
            multiplicador = -1 if ('-' in sinal_antes or '=' in sinal_antes or '-' in sinal_depois or '=' in sinal_depois) else 1
            valor_float = float(valor_texto.replace(".", "").replace(",", ".")) * multiplicador
            
            transacoes_estruturadas[-1]["Valor"] = valor_float
            
            if not gatilho_encontrado:
                texto_antes = re.sub(r'(?:\s|^)[-=]?\s*(?:R\$|RS|R\s\$)?\s*[-=]?\s*\d{1,3}(?:\.\d{3})*,\d{2}(?!\d).*$', '', linha_original, flags=re.IGNORECASE).strip()
                texto_antes_limpo = limpar_historico(texto_antes)
                if texto_antes_limpo:
                    transacoes_estruturadas[-1]["Historico"] += f" {texto_antes_limpo}"
                
        elif not gatilho_encontrado and not ignorar_captura and transacoes_estruturadas:
            texto_complemento = limpar_historico(linha_original)
            if texto_complemento:
                transacoes_estruturadas[-1]["Historico"] += f" {texto_complemento}"

    for t in transacoes_estruturadas:
        t["Historico"] = limpar_historico(t["Historico"])[:100].strip()

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