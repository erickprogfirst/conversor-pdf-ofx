import fitz  
import pytesseract
from PIL import Image
import io
import re

pytesseract.pytesseract.tesseract_cmd = r'C:\Users\contabil07\AppData\Local\Programs\Tesseract-OCR\tesseract.exe'

def limpar_historico_inter(texto):
    """Filtro químico exclusivo para o Banco Inter"""
    
    # 1. Limpa cabeçalhos e rodapés específicos do Inter
    lixo_ocr = [
        r'\binter\b', r'\bPandora Gestao\b', r'\bCNPJ\b', r'\bInstituição\b',
        r'\bAgência\b', r'\bConta\b', r'\bPeríodo\b', r'\bSaldo total\b',
        r'\bSaldo disponivel\b', r'\bSaldo bloqueado\b', r'\bValor\b', 
        r'\bSaldo por transação\b', r'\bFale com a gente\b', r'\bSAC\b', 
        r'\bOuvidoria\b', r'\bopção\b'
    ]
    for padrao in lixo_ocr:
        texto = re.sub(padrao, '', texto, flags=re.IGNORECASE)
        
    # 2. Desintegra o dinheiro da transação e o saldo (R$ XXX,XX R$ XXX,XX)
    texto = re.sub(r'(?:\s|^)[-=]?\s*(?:R\$|RS|R\s\$)?\s*[-=]?\s*\d{1,3}(?:\.\d{3})*,\d{2}(?!\d).*$', '', texto, flags=re.IGNORECASE)
    
    # 3. Remove a frase de cabeçalho do dia (ex: "2 de Maio de 2026 Saldo do dia:")
    texto = re.sub(r'\b\d{1,2}\s+de\s+[A-Za-zçÇ]+\s+de\s+\d{4}.*$', '', texto, flags=re.IGNORECASE)

    # 4. Limpa aspas e caracteres inúteis
    texto = texto.replace('"', '').replace("'", '').replace('(', '').replace(')', '').replace('*', '').replace('|', ' ')
    
    return " ".join(texto.split())

def extrair_dados_inter(caminho_pdf):
    print("\n" + "="*50)
    print(" FASE 3: MÁQUINA DE ESTADOS BANCO INTER ")
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
    
    # Tradutor de Meses do Inter
    meses_tradutor = {
        "JANEIRO": "01", "FEVEREIRO": "02", "MARÇO": "03", "MARCO": "03",
        "ABRIL": "04", "MAIO": "05", "JUNHO": "06", "JULHO": "07",
        "AGOSTO": "08", "SETEMBRO": "09", "OUTUBRO": "10", "NOVEMBRO": "11", "DEZEMBRO": "12"
    }

    # Radar que procura o bloco "2 de Maio de 2026"
    padrao_data_extensa = re.compile(r'(\d{1,2})\s+DE\s+([A-ZÇ]+)\s+DE\s+(\d{4})', re.IGNORECASE)
    
    # O Inter sempre usa R$ ou -R$ nas transações
    padrao_valor = re.compile(r'([-=]?)\s*(?:R\$|RS|R\s\$)\s*([-=]?)\s*(\d{1,3}(?:\.\d{3})*,\d{2})', re.IGNORECASE)

    gatilhos_fechar_porta = ["FALE COM A GENTE", "SAC:", "OUVIDORIA:", "SALDO TOTAL", "SALDO DISPONIVEL", "VALOR SALDO POR TRANSAÇÃO"]
    
    data_memoria = None

    for linha in linhas:
        linha_original = linha.strip()
        if not linha_original:
            continue

        if any(bloqueio in linha_original.upper() for bloqueio in gatilhos_fechar_porta):
            continue 

        # 1. VERIFICA MUDANÇA DE DIA (O Inter declara o dia como um cabeçalho)
        busca_data = padrao_data_extensa.search(linha_original)
        if busca_data:
            dia = busca_data.group(1).zfill(2)
            mes_texto = busca_data.group(2).upper()
            ano = busca_data.group(3)
            
            mes_numero = meses_tradutor.get(mes_texto, "01")
            data_memoria = f"{dia}/{mes_numero}/{ano}"
            continue # Pula a linha de saldo diário e vai para as transações abaixo
            
        # 2. BUSCA AS TRANSAÇÕES
        valores_encontrados = padrao_valor.findall(linha_original)
        historico_limpo = limpar_historico_inter(linha_original)

        if valores_encontrados and data_memoria and historico_limpo:
            # O primeiro valor encontrado na linha é o da transação (o segundo, se houver, é o saldo do dia)
            sinal1, sinal2, valor_texto = valores_encontrados[0]
            
            multiplicador = -1 if ('-' in sinal1 or '=' in sinal1 or '-' in sinal2 or '=' in sinal2) else 1
            valor_limpo = float(valor_texto.replace('.', '').replace(',', '.')) * multiplicador
            
            transacoes_estruturadas.append({
                "Data": data_memoria,
                "Historico": historico_limpo[:100].strip(),
                "Valor": valor_limpo 
            })
            
        elif transacoes_estruturadas and historico_limpo and data_memoria:
            # Captura eventuais complementos que caiam para a linha de baixo
            transacoes_estruturadas[-1]["Historico"] += f" {historico_limpo}"

    # Limpeza final das strings e Anti-Duplicidade
    transacoes_finais = []
    frequencia_transacoes = {}
    
    for t in transacoes_estruturadas:
        t["Historico"] = limpar_historico_inter(t["Historico"])[:100].strip()
        if t["Valor"] != 0.0:
            assinatura = f"{t['Data']}|{t['Historico']}|{t['Valor']}"
            if assinatura in frequencia_transacoes:
                frequencia_transacoes[assinatura] += 1
                t["Historico"] = f"{t['Historico']} {frequencia_transacoes[assinatura]:02d}"
            else:
                frequencia_transacoes[assinatura] = 1
            transacoes_finais.append(t)

    print(f"✅ Encontradas {len(transacoes_finais)} transações prontas para o OFX:\n")
    for t in transacoes_finais:
        print(t)

    return transacoes_finais