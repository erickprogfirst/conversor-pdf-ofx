import datetime
import re

def gerar_ofx(transacoes, caminho_saida="extrato.ofx"):
    
    # Nova função de limpeza: Permite até 255 caracteres e mantém a formatação (pontos, traços, etc.)
    def limpar_memo(texto):
        # Remove apenas caracteres que quebram o código XML do OFX (<, >, &)
        texto_seguro = str(texto).replace('<', ' ').replace('>', ' ').replace('&', 'E')
        # Liberta o limite para 255 caracteres (o ERP vai ler a descrição completa agora)
        return texto_seguro[:255].strip()

    header = f"""OFXHEADER:100
DATA:OFXSGML
VERSION:102
SECURITY:NONE
ENCODING:UTF-8
CHARSET:NONE
COMPRESSION:NONE
OLDFILEUID:NONE
NEWFILEUID:NONE

<OFX>
<SIGNONMSGSRQV1>
<SONRQ>
<DTCLIENT>{datetime.datetime.now().strftime("%Y%m%d%H%M%S")}
<USERID>0
<LANGUAGE>POR
<FI>
<ORG>CONVERSOR</ORG>
</FI>
<APPID>QWIN
<APPVER>2500
</SONRQ>
</SIGNONMSGSRQV1>
<BANKMSGSRQV1>
<STMTTRNRS>
<TRNUID>1
<STATUS>
<CODE>0
<SEVERITY>INFO
</STATUS>
<STMTRS>
<CURDEF>BRL
<BANKACCTFROM>
<BANKID>999
<ACCTID>000000
<ACCTTYPE>CHECKING
</BANKACCTFROM>
<BANKTRANLIST>
"""

    corpo = ""
    for i, t in enumerate(transacoes):
        # Conversão de data
        data_raw = t['Data'].replace("/", "")
        data_ofx = data_raw[4:] + data_raw[2:4] + data_raw[:2]
        
        # Conversão de valor e tipo
        valor = float(t['Valor'])
        tipo = "CREDIT" if valor >= 0 else "DEBIT"
        fitid = f"{data_ofx}{i:04d}"
        
        corpo += f"""<STMTTRN>
<TRNTYPE>{tipo}
<DTPOSTED>{data_ofx}120000[-03:EST]
<TRNAMT>{valor:.2f}
<FITID>{fitid}
<MEMO>{limpar_memo(t['Historico'])}
</STMTTRN>
"""

    footer = f"""</BANKTRANLIST>
<LEDGERBAL>
<BALAMT>0.00
<DTASOF>{datetime.datetime.now().strftime("%Y%m%d")}
</LEDGERBAL>
</STMTRS>
</STMTTRNRS>
</BANKMSGSRQV1>
</OFX>"""

    with open(caminho_saida, 'w', encoding='utf-8') as f:
        f.write(header + corpo + footer)
    
    print(f"✅ Arquivo OFX estruturado gerado com descrição completa.")