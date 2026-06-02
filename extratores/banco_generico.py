import fitz  
import pytesseract
from PIL import Image
import io
import re

pytesseract.pytesseract.tesseract_cmd = r'C:\Users\contabil07\AppData\Local\Programs\Tesseract-OCR\tesseract.exe'

def extrair_dados_brutos(caminho_pdf):
    print("\n" + "="*50)
    print(" FASE 3: ESTRUTURAÇÃO DE DADOS ")
    print("="*50 + "\n")
    
    texto_completo = ""
    
    try:
        # 1. EXTRAÇÃO (OCR)
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

    # 2. TRANSFORMAÇÃO E FATIAMENTO
    linhas = texto_completo.split('\n')
    transacoes_estruturadas = []
    data_memoria = None # Aqui o Python vai lembrar a última data que viu
    
    # Regex para achar datas no formato DD/MM/AAAA
    padrao_data = re.compile(r'(\d{2}/\d{2}/\d{4})')
    # Regex para achar o valor financeiro (pega o sinal de menos se houver, os números e a vírgula)
    padrao_valor = re.compile(r'(?:R\$|RS)\s*(-?\s*[\d\.]*,\d{2})', re.IGNORECASE)

    for linha in linhas:
        linha_limpa = linha.strip()
        if not linha_limpa or "SALDO DIA" in linha_limpa.upper() or "SALDO ANTERIOR" in linha_limpa.upper():
            continue

        # Tenta achar uma data na linha atual. Se achar, atualiza a memória.
        busca_data = padrao_data.search(linha_limpa)
        if busca_data:
            data_memoria = busca_data.group(1)

        # Verifica se é uma linha financeira
        valores_encontrados = padrao_valor.findall(linha_limpa)
        
        if valores_encontrados:
            # Pega sempre o primeiro valor da linha (a transação) e ignora o segundo (o saldo final)
            valor_texto = valores_encontrados[0]
            
            # Limpeza matemática: tira os espaços, tira os pontos de milhar e troca a vírgula por ponto
            valor_limpo = valor_texto.replace(" ", "").replace(".", "").replace(",", ".")
            valor_float = float(valor_limpo)
            
            # O histórico é a linha inteira, mas depois limparemos isso melhor
            historico = linha_limpa
            
            # Cria o pacote de dados estruturado
            transacao = {
                "Data": data_memoria,
                "Historico": historico[:40] + "...", # Corta o texto para não poluir a tela
                "Valor": valor_float
            }
            
            transacoes_estruturadas.append(transacao)

    # 3. EXIBIÇÃO DO RESULTADO ESTRUTURADO
    print(f"Encontradas {len(transacoes_estruturadas)} transações prontas para o OFX:\n")
    for t in transacoes_estruturadas:
        print(t)
        
    print("\n" + "="*50 + "\n")
    
    # Retorna os dados limpos para a próxima fase (Gerador de OFX)
    return transacoes_estruturadas