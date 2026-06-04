import fitz  
import pytesseract
from PIL import Image
import io
import re

pytesseract.pytesseract.tesseract_cmd = r'C:\Users\contabil07\AppData\Local\Programs\Tesseract-OCR\tesseract.exe'

def limpar_historico_safra(texto):
    """Filtro químico expandido para aniquilar estilhaços do rodapé e traços de tabela"""
    
    lixo_ocr = [
        r'\bCENTRAL DE SUPORTE\b', r'\bSAC E DEFICIENTES\b', r'\bOUVIDORIA\b', 
        r'\bBanco Safra\b', r'58\.160\.789/0001-28', r'\bLANÇAMENTOS REALIZADOS\b',
        r'\bPágina\b', r'\bAtendimento\b', r'\bferiados\b', r'\bCapital e Grande SP\b', 
        r'\bDemais localidades\b', r'\bData\b', r'\bLançamento\b', r'\bComplemento\b', 
        r'\bNº Documento\b', r'\bValor\b', r'0800\s*\d+', r'0300\s*\d+',
        r'\bpersonalizado\b', r'\bexceto\b', r'de 2ª a 6ª', r'de 2º', r'2ª', r'6ª',
        r'24h por dia', r'7 dias por semana', r'\bsemana\b', r'9h às', r'\b18h\b', r'\b19h\b',
        r'\bCNPJ\b', r'\bAG:\b', r'\bCONTA:\b'
    ]
    for padrao in lixo_ocr:
        texto = re.sub(padrao, '', texto, flags=re.IGNORECASE)
        
    texto = re.sub(r'(?:\s|^)[-=]?\s*\d{1,3}(?:\.\d{3})*,\d{2}(?!\d).*$', '', texto, flags=re.IGNORECASE)
    texto = re.sub(r'^\s*\d{2}/\d{2}\b', '', texto)
    
    # A MÁGICA ANTI-TRAÇOS: Destrói hífens, underlines, travessões e barras da tabela
    texto = re.sub(r'[-_—–|]', ' ', texto)
    
    texto = texto.replace('(', '').replace(')', '').replace('*', '')
    
    # A GUILHOTINA DE PONTUAÇÃO: Arranca qualquer símbolo perdido no início ou fim da frase
    texto = re.sub(r'^[^\w\s]+|[^\w\s]+$', '', texto.strip())
    
    return " ".join(texto.split())

def extrair_dados_safra(caminho_pdf):
    print("\n" + "="*50)
    print(" FASE 3: MÁQUINA DE ESTADOS SAFRA (ANTI-TRAÇOS ATIVADO) ")
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
    
    padrao_data_transacao = re.compile(r'^\s*(\d{2}/\d{2})\b')
    padrao_valor = re.compile(r'(?:^|\s)([-=]?)\s*(\d{1,3}(?:\.\d{3})*,\d{2})(?!\d)', re.IGNORECASE)
    padrao_ano_cabecalho = re.compile(r'Período de \d{2}/\d{2}/(\d{4})', re.IGNORECASE)

    # 1. RESGATE DO ANO NO CABEÇALHO
    ano_extrato = "2026" 
    for linha in linhas:
        busca_ano = padrao_ano_cabecalho.search(linha)
        if busca_ano:
            ano_extrato = busca_ano.group(1)
            break

    # A LISTA DE BLOQUEIO ABSOLUTO
    gatilhos_fechar_porta = [
        "CENTRAL DE SUPORTE", "OUVIDORIA", "SAC", "PÁGINA", "BANCO SAFRA", 
        "EXTRATO DE MOVIMENTAÇÃO", "SALDO CONTA CORRENTE", "SALDO + LIMITE", 
        "LANÇAMENTOS REALIZADOS", "CNPJ", "AG:", "CONTA:", "VALOR (R$)", 
        "COMPLEMENTO", "Nº DOCUMENTO", "DOCUMENTO VALOR", "SALDO BLOQUEADO", "LIMITE DISPONÍVEL"
    ]

    porta_aberta = False

    for linha in linhas:
        linha_original = linha.strip()
        if not linha_original:
            continue

        if any(bloqueio in linha_original.upper() for bloqueio in gatilhos_fechar_porta):
            porta_aberta = False
            continue 
        
        if len(re.findall(r'R\$', linha_original, re.IGNORECASE)) >= 2:
            porta_aberta = False
            continue

        busca_data = padrao_data_transacao.search(linha_original)

        if busca_data:
            porta_aberta = True
            dia_mes = busca_data.group(1)
            data_memoria = f"{dia_mes}/{ano_extrato}"
            
            transacoes_estruturadas.append({
                "Data": data_memoria,
                "Historico": limpar_historico_safra(linha_original),
                "Valor": 0.0 
            })
            
            valores_encontrados = padrao_valor.findall(linha_original)
            if valores_encontrados:
                sinal, valor_texto = valores_encontrados[-1] 
                multiplicador = -1 if ('-' in sinal or '-' in valor_texto) else 1
                valor_limpo = re.sub(r'[-=]', '', valor_texto).replace('.', '').replace(',', '.')
                transacoes_estruturadas[-1]["Valor"] = float(valor_limpo) * multiplicador
                
        elif porta_aberta and transacoes_estruturadas:
            texto_complemento = limpar_historico_safra(linha_original)
            if texto_complemento:
                transacoes_estruturadas[-1]["Historico"] += f" {texto_complemento}"
                
            if transacoes_estruturadas[-1]["Valor"] == 0.0:
                valores_encontrados = padrao_valor.findall(linha_original)
                if valores_encontrados:
                    sinal, valor_texto = valores_encontrados[-1]
                    multiplicador = -1 if ('-' in sinal or '-' in valor_texto) else 1
                    valor_limpo = re.sub(r'[-=]', '', valor_texto).replace('.', '').replace(',', '.')
                    transacoes_estruturadas[-1]["Valor"] = float(valor_limpo) * multiplicador

    for t in transacoes_estruturadas:
        t["Historico"] = limpar_historico_safra(t["Historico"])[:100].strip()

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