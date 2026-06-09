import fitz
import pytesseract
from PIL import Image
import io
import re

pytesseract.pytesseract.tesseract_cmd = r'C:\Users\contabil07\AppData\Local\Programs\Tesseract-OCR\tesseract.exe'

def extrair_float(valor_str, tipo_str):
    """Limpa a string financeira e aplica o sinal correto baseado no tipo."""
    v_limpo = re.sub(r'[^\d,-]', '', valor_str).replace(',', '.')
    try:
        v = float(v_limpo)
        if "SA" in tipo_str.upper():
            return -abs(v)
        else:
            return abs(v)
    except:
        return 0.0

def extrair_dados_stone(caminho_pdf):
    transacoes = []
    texto_completo = ""
    
    try:
        doc = fitz.open(caminho_pdf)
        for num_pag in range(len(doc)):
            pix = doc.load_page(num_pag).get_pixmap(matrix=fitz.Matrix(2.0, 2.0))
            img = Image.open(io.BytesIO(pix.tobytes("png")))
            texto_completo += pytesseract.image_to_string(img, config=r'--psm 6') + "\n"
    except Exception as e:
        print(f"Erro ao ler PDF: {e}")
        return []

    linhas = texto_completo.split('\n')
    transacao_atual = None
    
    # Adicionado "PERIODO" sem acento para bloquear o lixo que apareceu no seu print
    gatilhos_ignorar = [
        "EXTRATO", "PÁGINA", "PAGINA", "EMITIDO", "DATA", "TIPO", 
        "DESCRIÇÃO", "VALOR", "SALDO", "CONTRAPARTE", "STONE", "NOME", 
        "PERÍODO", "PERIODO", "DOCUMENTO", "AGÊNCIA", "INSTITUIÇÃO"
    ]

    # Regex para apanhar o padrão de dinheiro (ex: - R$ 6.500,00 ou 10,00)
    padrao_valor = r'([-]?\s*(?:R\$|RS)?\s*\d{1,3}(?:\.\d{3})*,\d{2})'

    for linha in linhas:
        linha = linha.strip()
        if not linha or any(g in linha.upper() for g in gatilhos_ignorar):
            continue
            
        # 1. Verifica se a linha INICIA uma transação (Data + Tipo + Resto)
        match_inicio = re.search(r'^(\d{2}/\d{2}/\d{2,4})\s+(Entrada|Sa[ií]da)\s+(.*)', linha, re.IGNORECASE)
        
        if match_inicio:
            # Guarda a transação anterior
            if transacao_atual and transacao_atual["Valor"] is not None:
                transacoes.append(transacao_atual)
                
            data_str = match_inicio.group(1)
            tipo_str = match_inicio.group(2)
            resto = match_inicio.group(3)
            
            partes = data_str.split('/')
            ano = f"20{partes[2]}" if len(partes[2]) == 2 else partes[2]
            data_final = f"{partes[0]}/{partes[1]}/{ano}"
            
            transacao_atual = {
                "Data": data_final,
                "Historico": "",
                "Valor": None,
                "Tipo": tipo_str
            }
            
            # Verifica se o valor já está nesta primeira linha
            match_v = re.search(padrao_valor, resto, re.IGNORECASE)
            if match_v:
                valor_raw = match_v.group(1)
                transacao_atual["Valor"] = extrair_float(valor_raw, tipo_str)
                # O histórico é tudo o que vem antes do valor
                transacao_atual["Historico"] = resto[:match_v.start()].strip()
            else:
                # Se não tem valor, toda a linha faz parte do histórico
                transacao_atual["Historico"] = resto.strip()
                
        elif transacao_atual:
            # 2. CONTINUAÇÃO da transação (A linha não começou com data)
            match_v = re.search(padrao_valor, linha, re.IGNORECASE)
            
            if transacao_atual["Valor"] is None and match_v:
                # Encontrou o valor que estava a faltar na linha de baixo (ex: o - R$ 6.500,00 ao lado do LTDA)
                valor_raw = match_v.group(1)
                transacao_atual["Valor"] = extrair_float(valor_raw, transacao_atual["Tipo"])
                # Pega no texto que estiver antes deste valor
                desc_extra = linha[:match_v.start()].strip()
                if desc_extra:
                    transacao_atual["Historico"] += " " + desc_extra
            else:
                # Se já temos o valor, ignoramos qualquer outro número financeiro (ex: o Saldo) e guardamos só texto
                linha_limpa = re.sub(padrao_valor, '', linha, flags=re.IGNORECASE).strip()
                if linha_limpa:
                    transacao_atual["Historico"] += " " + linha_limpa

    # Adiciona a última transação processada
    if transacao_atual and transacao_atual["Valor"] is not None:
        transacoes.append(transacao_atual)

    # 3. Limpeza final dos históricos (junta os bocados e limpa erros do OCR)
    for t in transacoes:
        hist = re.sub(r'[-_—–|@]', ' ', t["Historico"])
        hist = hist.replace("5 Maquininha", "Pix Maquininha").replace("5, Maquininha", "Pix Maquininha")
        t["Historico"] = " ".join(hist.split())
        t.pop("Tipo", None) # Remove a chave temporária

    return transacoes