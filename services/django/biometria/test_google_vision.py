"""
Script de teste para Google Cloud Vision API - OCR de Documentos
Execute: docker exec wallclub-portais python /app/biometria/test_google_vision.py <documento.jpg>
"""
import sys
import os
from google.cloud import vision


def extrair_texto_documento(image_path):
    """
    Extrai texto de documento usando Google Cloud Vision

    Args:
        image_path: Caminho para imagem do documento
    """
    print("=" * 60)
    print("TESTE DE OCR - GOOGLE CLOUD VISION")
    print("=" * 60)

    # Verificar se arquivo existe
    if not os.path.exists(image_path):
        print(f"❌ Arquivo não encontrado: {image_path}")
        return False

    print(f"\n📄 Documento: {image_path}")

    # Criar cliente Vision
    try:
        client = vision.ImageAnnotatorClient()
        print("✅ Cliente Google Vision criado")
    except Exception as e:
        print(f"❌ Erro ao criar cliente: {e}")
        print("\n💡 Verifique se GOOGLE_APPLICATION_CREDENTIALS está configurado")
        return False

    # Ler imagem
    try:
        with open(image_path, 'rb') as image_file:
            content = image_file.read()

        image = vision.Image(content=content)
        print("✅ Imagem carregada")
    except Exception as e:
        print(f"❌ Erro ao ler imagem: {e}")
        return False

    # Extrair texto
    print("\n🔍 Extraindo texto do documento...")
    try:
        response = client.text_detection(image=image)
        texts = response.text_annotations

        if response.error.message:
            print(f"❌ Erro da API: {response.error.message}")
            return False

        if not texts:
            print("❌ Nenhum texto encontrado no documento")
            return False

        # Primeiro resultado é o texto completo
        texto_completo = texts[0].description

        print("\n" + "=" * 60)
        print("TEXTO EXTRAÍDO")
        print("=" * 60)
        print(texto_completo)
        print("=" * 60)

        # Tentar identificar campos comuns
        print("\n📋 CAMPOS IDENTIFICADOS:")

        linhas = texto_completo.split('\n')
        for linha in linhas:
            linha_upper = linha.upper()

            # CPF
            if 'CPF' in linha_upper:
                print(f"  CPF: {linha}")

            # RG
            if 'RG' in linha_upper or 'IDENTIDADE' in linha_upper:
                print(f"  RG: {linha}")

            # Nome
            if 'NOME' in linha_upper:
                print(f"  Nome: {linha}")

            # Data de nascimento
            if 'NASCIMENTO' in linha_upper or 'NASC' in linha_upper:
                print(f"  Nascimento: {linha}")

            # CNH
            if 'CNH' in linha_upper or 'HABILITAÇÃO' in linha_upper:
                print(f"  CNH: {linha}")

        print("\n✅ OCR concluído com sucesso!")
        return True

    except Exception as e:
        print(f"\n❌ Erro ao processar imagem: {e}")
        return False


if __name__ == '__main__':
    if len(sys.argv) != 2:
        print("Uso: python test_google_vision.py <documento.jpg>")
        print("\nExemplo:")
        print("  docker exec wallclub-portais python /app/biometria/test_google_vision.py /app/biometria/documento.jpg")
        sys.exit(1)

    image_path = sys.argv[1]
    success = extrair_texto_documento(image_path)
    sys.exit(0 if success else 1)
