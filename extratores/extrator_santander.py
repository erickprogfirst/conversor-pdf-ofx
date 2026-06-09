import fitz
import re

def extrair_dados_santander(caminho_pdf):
    print("\n--- INICIANDO EXTRATOR SANTANDER (LEITURA DIGITAL) ---")
    transacoes = []
    
    # Dicionário para converter o nome do mês em número
    meses = {
        "janeiro": "01", "fevereiro": "02", "março": "03", "marco": "03", "abril": "04",
        "maio": "05", "junho": "06", "julho": "07", "agosto": "08",
        "setembro": "09", "outubro": "10", "novembro": "11", "dezembro": "12"
    }
    
    try:
        doc = fitz.open(caminho_pdf)
        data_atual = None
        
        for num_pag in range(len(doc)):
            pagina = doc.load_page(num_pag)
            palavras = pagina.get_text("words")
            
            # Agrupar as palavras pela altura (eixo Y)
            linhas_y = {}
            for p in palavras:
                y0 = round(p[1] / 3) * 3 
                if y0 not in linhas_y:
                    linhas_y[y0] = []
                linhas_y[y0].append(p)
                
            y_ordenados = sorted(linhas_y.keys())
            
            for y in y_ordenados:
                palavras_linha = sorted(linhas_y[y], key=lambda w: w[0])
                linha = " ".join([w[4] for w in palavras_linha]).strip()
                
                if not linha: continue
                
                # 1. Procura a Data (ex: Quarta, 01 de abril de 2026)
                match_data = re.search(r'^(?:Segunda|Terça|Terca|Quarta|Quinta|Sexta|Sábado|Sabado|Domingo)[,-]?\s*(\d{2})\s+de\s+([a-zA-ZçÇ]+)\s+de\s+(\d{4})', linha, re.IGNORECASE)
                
                if match_data:
                    dia = match_data.group(1)
                    mes_nome = match_data.group(2).lower()
                    ano = match_data.group(3)
                    mes_num = meses.get(mes_nome, "01")
                    # Atualiza a data que será usada nas próximas transações
                    data_atual = f"{dia}/{mes_num}/{ano}"
                    continue
                
                # 2. Procura a Transação (Descrição + DEBITO/CREDITO + R$ Valor)
                if data_atual:
                    # O Santander coloca DEBITO ou CREDITO sempre antes do valor (ex: ... DEBITO R$ 382,94)
                    match_transacao = re.search(r'(.+?)\s+(DEBITO|CREDITO)\s*(?:R\$)?\s*([\d\.,]+)', linha, re.IGNORECASE)
                    
                    if match_transacao:
                        descricao_raw = match_transacao.group(1).strip()
                        tipo_operacao = match_transacao.group(2).upper()
                        valor_raw = match_transacao.group(3)
                        
                        # Limpa o valor para formato numérico
                        v_limpo = valor_raw.replace('.', '').replace(',', '.')
                        try:
                            valor_float = float(v_limpo)
                        except ValueError:
                            continue
                            
                        # Define o sinal com base na palavra
                        if tipo_operacao == 'DEBITO':
                            valor_float = -abs(valor_float)
                        else:
                            valor_float = abs(valor_float)
                            
                        # Remove eventuais caracteres soltos no fim da descrição
                        descricao_limpa = re.sub(r'[-_—–|]$', '', descricao_raw).strip()
                        
                        transacoes.append({
                            "Data": data_atual,
                            "Historico": descricao_limpa,
                            "Valor": valor_float
                        })
                        
    except Exception as e:
        print(f"Erro na extração digital do Santander: {e}")
        
    print(f"✅ Extrator Santander finalizou: {len(transacoes)} transações mapeadas com perfeição.")
    return transacoes