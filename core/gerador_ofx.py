import datetime

def gerar_ofx(transacoes, caminho_saida="extrato_convertido.ofx"):
    """Recebe as transações limpas e monta o arquivo OFX oficial."""
    print("\n" + "="*50)
    print(" INICIANDO GERAÇÃO DO ARQUIVO OFX ")
    print("="*50 + "\n")
    
    if not transacoes:
        print("❌ Nenhuma transação para converter.")
        return False

    # Cabeçalho padrão obrigatório de arquivos OFX
    ofx_texto = """OFXHEADER:100
DATA:OFXSGML
VERSION:102
SECURITY:NONE
ENCODING:USASCII
CHARSET:1252
COMPRESSION:NONE
OLDFILEUID:NONE
NEWFILEUID:NONE

<OFX>
  <SIGNONMSGSRSV1>
    <SONRS>
      <STATUS>
        <CODE>0</CODE>
        <SEVERITY>INFO</SEVERITY>
      </STATUS>
      <DTSERVER>20260602120000[-3:BRT]</DTSERVER>
      <LANGUAGE>POR</LANGUAGE>
    </SONRS>
  </SIGNONMSGSRSV1>
  <BANKMSGSRSV1>
    <STMTTRNRS>
      <TRNUID>1</TRNUID>
      <STATUS>
        <CODE>0</CODE>
        <SEVERITY>INFO</SEVERITY>
      </STATUS>
      <STMTRS>
        <CURDEF>BRL</CURDEF>
        <BANKACCTFROM>
          <BANKID>104</BANKID>
          <ACCTID>999999999</ACCTID>
          <ACCTTYPE>CHECKING</ACCTTYPE>
        </BANKACCTFROM>
        <BANKTRANLIST>
"""

    # Inserindo cada transação na estrutura XML do OFX
    contador = 1
    for t in transacoes:
        # Arruma a data de DD/MM/AAAA para AAAAMMDD (Padrão OFX)
        dia, mes, ano = t['Data'].split('/')
        data_ofx = f"{ano}{mes}{dia}120000[-3:BRT]"
        
        # Define se é Crédito ou Débito
        tipo_trn = "CREDIT" if t['Valor'] >= 0 else "DEBIT"
        
        # Cria as tags da transação
        ofx_texto += "          <STMTTRN>\n"
        ofx_texto += f"            <TRNTYPE>{tipo_trn}</TRNTYPE>\n"
        ofx_texto += f"            <DTPOSTED>{data_ofx}</DTPOSTED>\n"
        ofx_texto += f"            <TRNAMT>{t['Valor']:.2f}</TRNAMT>\n"
        ofx_texto += f"            <FITID>DOC{contador}</FITID>\n"
        ofx_texto += f"            <MEMO>{t['Historico']}</MEMO>\n"
        ofx_texto += "          </STMTTRN>\n"
        
        contador += 1

    # Fechamento do arquivo
    ofx_texto += """        </BANKTRANLIST>
      </STMTRS>
    </STMTTRNRS>
  </BANKMSGSRSV1>
</OFX>"""

    # Cria o arquivo fisicamente na sua pasta
    try:
        with open(caminho_saida, "w", encoding="utf-8") as arquivo:
            arquivo.write(ofx_texto)
        print(f"✅ SUCESSO ABSOLUTO! Arquivo salvo como: {caminho_saida}")
        return True
    except Exception as e:
        print(f"❌ Erro ao salvar o arquivo: {e}")
        return False