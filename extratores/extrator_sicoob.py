import fitz
import re

def extrair_dados_sicoob(caminho_pdf):
    print("\n--- INICIANDO EXTRATOR SICOOB (LEITURA DIGITAL) ---")
    transacoes = []
    
    try:
        doc = fitz.open(caminho_pdf)
        
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
            
            transacao_atual = None
            
            # Filtro rigoroso para o layout do Sicoob
            gatilhos_ignorar = [
                "SALDO ANTERIOR", "SALDO BLOQUEADO", "RESUMO", "SALDO EM CONTA",
                "CHEQUE ESPECIAL", "SALDO DISPONÍVEL", "OUTRAS INFORMAÇÕES",
                "ENCARGOS", "PREVISÃO", "SICOOB", "EXTRATO", "DATA DOCUMENTO",
                "SISTEMA DE COOPERATIVAS", "OUVIDORIA", "IDENTIFICADOR DO ARQUIVO",
                "VENCIMENTO", "CUSTO EFETIVO"
            ]

            for y in y_ordenados:
                palavras_linha = sorted(linhas_y[y], key=lambda w: w[0])
                linha = " ".join([w[4] for w in palavras_linha]).strip()
                
                if not linha: continue
                
                # Ignora cabeçalhos, rodapés e metadados
                if any(g in linha.upper() for g in gatilhos_ignorar):
                    continue
                    
                # Ignora expressamente a linha de saldo diário para não capturar valores falsos
                if "SALDO DO DIA" in linha.upper():
                    continue
                
                # 1. Procura a Data no formato DD/MM/AAAA
                match_data = re.search(r'^(\d{2}/\d{2}/\d{4})\s+(.+)', linha)
                
                if match_data:
                    if transacao_atual:
                        transacoes.append(transacao_atual)
                        
                    data_str = match_data.group(1)
                    resto = match_data.group(2)
                    
                    # 2. Procura o Valor que termina obrigatoriamente com C ou D
                    # Permite '0' no lugar de C caso o gerador do PDF do banco tenha falhado a fonte
                    match_valor = re.search(r'(\d{1,3}(?:\.\d{3})*,\d{2})\s*([CDcd0])\b', resto)
                    
                    if match_valor:
                        valor_str = match_valor.group(1)
                        tipo_cd = match_valor.group(2).upper()
                        
                        historico_raw = resto[:match_valor.start()].strip()
                        
                        # Tratamento matemático
                        v_limpo = valor_str.replace('.', '').replace(',', '.')
                        try:
                            valor_float = float(v_limpo)
                        except ValueError:
                            continue
                            
                        # Aplicação do Sinal: D = Débito (-), C/0 = Crédito (+)
                        if tipo_cd == 'D':
                            valor_float = -abs(valor_float)
                        else:
                            valor_float = abs(valor_float)
                            
                        transacao_atual = {
                            "Data": data_str,
                            "Historico": historico_raw,
                            "Valor": valor_float
                        }
                        
                elif transacao_atual:
                    # 3. Continuação do Histórico (ex: chaves Pix ou detalhes adicionais)
                    linha_limpa = linha.strip()
                    if linha_limpa:
                        transacao_atual["Historico"] += f" {linha_limpa}"

            if transacao_atual:
                transacoes.append(transacao_atual)
                
    except Exception as e:
        print(f"Erro na extração digital do Sicoob: {e}")
        
    # Limpeza final de formatação do Histórico
    for t in transacoes:
        # Remove números de documento puramente numéricos que ficam presos no início da descrição
        t["Historico"] = re.sub(r'^\d+\s+', '', t["Historico"])
        t["Historico"] = " ".join(t["Historico"].split())
        
    print(f"✅ Extrator Sicoob finalizou: {len(transacoes)} transações mapeadas com perfeição.")
    return transacoes