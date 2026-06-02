import pdfplumber

def extrair_texto_primeira_pagina(caminho_pdf):
    """Abre o PDF e retorna todo o texto da primeira página."""
    try:
        with pdfplumber.open(caminho_pdf) as pdf:
            # Pega a página 0 (primeira página) e extrai o texto
            return pdf.pages[0].extract_text()
    except Exception as e:
        print(f"Erro ao tentar abrir o PDF: {e}")
        return None