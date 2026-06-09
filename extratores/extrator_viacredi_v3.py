import fitz
import re

def extrair_dados_viacredi_v3(caminho_pdf):
    print("\n--- INICIANDO EXTRATOR VIACREDI V3 (LEITURA DIGITAL POR COORDENADAS) ---")
    transacoes = []
    
    try:
        doc = fitz.open(caminho_pdf)
        
        for num_pag in range(len(doc)):
            pagina = doc.load_page(num_pag)
            # Extrai cada palavra e as suas coordenadas exatas na página
            palavras = pagina.get_text("words")
            
            # Agrupar as palavras pela altura (eixo Y) para reconstruir as linhas perfeitamente
            linhas_y = {}
            for p in palavras:
                # p[1] é a posição Y da palavra. 
                # Arredondamos para garantir que palavras na mesma linha fiquem juntas
                y0 = round(p[1] / 3) * 3 
                if y0 not in linhas_y:
                    linhas_y[y0] = []
                linhas_y[y0].append(p)
                
            # Ler a página de cima para baixo
            y_ordenados = sorted(linhas_y.keys())
            
            for y in y_ordenados:
                # Ordena as palavras da linha da esquerda para a direita (coordenada X)
                palavras_linha = sorted(linhas_y[y], key=lambda w: w[0])
                
                # Junta as palavras recriando a linha original com espaços normais
                linha = " ".join([w[4] for w in palavras_linha])
                
                # A MÁSCARA: Procura Data no início
                match_data = re.search(r'^(\d{2}/\d{2}/\d{2,4})\s+(.+)', linha)
                
                if match_data:
                    data_str = match_data.group(1)
                    resto = match_data.group(2)
                    
                    # Procura exatamente um Valor formatado seguido de C ou D (ex: 6.179,00 C)
                    # O saldo no final é automaticamente ignorado
                    match_valor = re.search(r'(\d{1,3}(?:\.\d{3})*,\d{2})\s+([CDcd])\b', resto)
                    
                    if match_valor:
                        valor_str = match_valor.group(1)
                        tipo_cd = match_valor.group(2).upper()
                        
                        # O Histórico é tudo o que estiver antes desse valor financeiro
                        historico_raw = resto[:match_valor.start()].strip()
                        
                        # Remove o "DOCUMENTO" que fica colado no final do histórico
                        historico_limpo = re.sub(r'\s+[\d\.\-/]+$', '', historico_raw).strip()
                        # Remove os tracinhos residuais (ex: "CR. INTERNET -")
                        historico_limpo = re.sub(r'\s+[-_—–|]$', '', historico_limpo).strip()
                        
                        # Tratamento matemático
                        v_limpo = valor_str.replace('.', '').replace(',', '.')
                        try:
                            valor_float = float(v_limpo)
                        except:
                            continue
                            
                        # D = Débito (negativo), C = Crédito (positivo)
                        if tipo_cd == 'D':
                            valor_float = -abs(valor_float)
                        else:
                            valor_float = abs(valor_float)
                            
                        # Formatação de Data para YYYY
                        partes = data_str.split('/')
                        ano = f"20{partes[2]}" if len(partes[2]) == 2 else partes[2]
                        data_final = f"{partes[0]}/{partes[1]}/{ano}"
                        
                        transacoes.append({
                            "Data": data_final,
                            "Historico": historico_limpo,
                            "Valor": valor_float
                        })
                        
    except Exception as e:
        print(f"Erro na extração digital: {e}")
        
    print(f"✅ Extrator finalizou: {len(transacoes)} transações mapeadas com perfeição.")
    return transacoes