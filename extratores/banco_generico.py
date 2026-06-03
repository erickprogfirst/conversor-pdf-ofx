import fitz  
import pytesseract
from PIL import Image
import io
import re

pytesseract.pytesseract.tesseract_cmd = r'C:\Users\contabil07\AppData\Local\Programs\Tesseract-OCR\tesseract.exe'

def limpar_historico(texto):
    """Filtro químico com blindagem contra estilhaços de datas"""
    
    # 1. Erros de cabeçalho e símbolos
    lixo_ocr = [r'\bCEREN\b', r'\bGATS\b', r'\bAIXA\b', r'\bCNPJ\b', r'\bDATA\b', r'\bEE\b', r'\bEPEE\b', r'\bCNPI\b']
    for padrao in lixo_ocr:
        texto = re.sub(padrao, '', texto, flags=re.IGNORECASE)
        
    texto = texto.replace('£', '').replace('¢', '')
    texto = re.sub(r'(?i)\b(ren|even|inate)\b', '', texto)
    
    # 2. Desintegra o dinheiro e saldos residuais no final da linha
    texto = re.sub(r'[-=]?\s*(R\$|RS|R\s\$).*$', '', texto, flags=re.IGNORECASE)

    # 3. MÁQUINA DO TEMPO: Remove blocos inteiros de datas para não deixar números órfãos (15, 21, 22)
    texto = re.sub(r'\b\d{2}/\d{2}(?:/\d{4})?(?:\s+\d{2}:\d{2})?\b', '', texto)
    texto = re.sub(r'\b\d{1,3}\s+\d{2}:\d{2}\b', '', texto) # Remove erro de OCR (ex: "104 10:52")
    texto = re.sub(r'\b\d{2}:\d{2}\b', '', texto)
    
    # 4. LIMPEZA CIRÚRGICA DOS ESTILHAÇOS QUE VOCÊ SUBLINHOU
    # Remove /2026 ou /04 isolados (com espaço ANTES para proteger o CNPJ "0001-05")
    texto = re.sub(r'\s+/\d{2,4}\b', '', texto)
    # Remove o "104" ou "04" grudado apenas na palavra SALARIO
    texto = re.sub(r'\b\d{1,3}\s+(SALARIO)\b', r'\1', texto, flags=re.IGNORECASE)
    # Remove barras soltas antes do SALARIO
    texto = re.sub(r'/\s+(SALARIO)\b', r'\1', texto, flags=re.IGNORECASE)
    
    # 5. Hashes gigantes (PIX) e códigos internos
    texto = re.sub(r'[A-Z0-9]{25,}', '', texto)
    texto = re.sub(r'\b\d{6,}\b', '', texto)
    
    # 6. Caracteres que sujam o ERP
    texto = texto.replace('(', '').replace(')', '').replace('*', '').replace('-', ' ')
    
    return " ".join(texto.split())

def extrair_dados_brutos(caminho_pdf):
    print("\n" + "="*50)
    print(" FASE 3: MÁQUINA DE ESTADOS (ANTI-ESTILHAÇOS ATIVADO) ")
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
    padrao_valor = re.compile(r'([-=]?)\s*(?:R\$|RS)\s*([-=]?)\s*([\d\.]*,\d{2})', re.IGNORECASE)

    gatilhos_nova = ["PIX RECEBIDO", "ENVIO TRANSF INTERNET", "DEPOSITO DINH LOTERICO", "MENSALIDADE CESTA SERVICO", "TARIFA RENOVACAO CADASTRO", "SEGURADORA"]
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
                texto_antes = re.sub(r'[-=]?\s*(?:R\$|RS).*$', '', linha_original, flags=re.IGNORECASE).strip()
                texto_antes_limpo = limpar_historico(texto_antes)
                if texto_antes_limpo:
                    transacoes_estruturadas[-1]["Historico"] += f" {texto_antes_limpo}"
                
        elif not gatilho_encontrado and not ignorar_captura and transacoes_estruturadas:
            texto_complemento = limpar_historico(linha_original)
            if texto_complemento:
                transacoes_estruturadas[-1]["Historico"] += f" {texto_complemento}"

    # O Pente-fino final
    for t in transacoes_estruturadas:
        t["Historico"] = limpar_historico(t["Historico"])[:100].strip()

    return [t for t in transacoes_estruturadas if t["Valor"] != 0.0]