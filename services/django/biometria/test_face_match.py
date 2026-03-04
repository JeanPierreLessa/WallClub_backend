"""
Script de teste para comparação facial com AWS Rekognition
Execute: docker exec wallclub-portais python /app/checkout/test_face_match.py <selfie.jpg> <documento.jpg>
"""
import sys
import os
import boto3
from botocore.exceptions import ClientError

def compare_faces(source_image_path, target_image_path):
    """
    Compara duas imagens faciais usando AWS Rekognition

    Args:
        source_image_path: Caminho para a selfie
        target_image_path: Caminho para a foto do documento
    """
    print("=" * 60)
    print("TESTE DE COMPARAÇÃO FACIAL - AWS REKOGNITION")
    print("=" * 60)

    # Verificar se arquivos existem
    if not os.path.exists(source_image_path):
        print(f"❌ Arquivo não encontrado: {source_image_path}")
        return False

    if not os.path.exists(target_image_path):
        print(f"❌ Arquivo não encontrado: {target_image_path}")
        return False

    print(f"\n📸 Selfie: {source_image_path}")
    print(f"📄 Documento: {target_image_path}")

    # Criar cliente Rekognition
    try:
        aws_region = os.getenv('AWS_REGION', 'us-east-1')
        rekognition = boto3.client('rekognition', region_name=aws_region)
        print(f"\n✅ Cliente Rekognition criado (região: {aws_region})")
    except Exception as e:
        print(f"\n❌ Erro ao criar cliente: {e}")
        return False

    # Ler imagens
    try:
        with open(source_image_path, 'rb') as source_file:
            source_bytes = source_file.read()

        with open(target_image_path, 'rb') as target_file:
            target_bytes = target_file.read()

        print("✅ Imagens carregadas")
    except Exception as e:
        print(f"❌ Erro ao ler imagens: {e}")
        return False

    # Comparar faces
    print("\n🔍 Comparando faces...")
    try:
        response = rekognition.compare_faces(
            SourceImage={'Bytes': source_bytes},
            TargetImage={'Bytes': target_bytes},
            SimilarityThreshold=70  # Threshold mínimo de 70%
        )

        print("\n" + "=" * 60)
        print("RESULTADO DA COMPARAÇÃO")
        print("=" * 60)

        if not response['FaceMatches']:
            print("\n❌ NENHUMA CORRESPONDÊNCIA ENCONTRADA")
            print("   As faces não são suficientemente similares (< 70%)")

            # Verificar se há faces não correspondentes
            if response.get('UnmatchedFaces'):
                print(f"\n   Faces detectadas mas não correspondentes: {len(response['UnmatchedFaces'])}")

            return False

        # Pegar o melhor match
        best_match = response['FaceMatches'][0]
        similarity = best_match['Similarity']
        face = best_match['Face']

        print(f"\n✅ CORRESPONDÊNCIA ENCONTRADA!")
        print(f"\n📊 Score de Similaridade: {similarity:.2f}%")
        print(f"📍 Confiança da detecção: {face['Confidence']:.2f}%")

        # Interpretar resultado
        print("\n📋 Interpretação:")
        if similarity >= 95:
            print("   🟢 MUITO ALTA - Mesma pessoa (alta confiança)")
        elif similarity >= 90:
            print("   🟢 ALTA - Provavelmente mesma pessoa")
        elif similarity >= 80:
            print("   🟡 MÉDIA - Possível mesma pessoa (revisar)")
        else:
            print("   🟠 BAIXA - Incerto (threshold mínimo)")

        # Informações adicionais da face
        print(f"\n📐 Posição da face no documento:")
        bbox = face['BoundingBox']
        print(f"   Left: {bbox['Left']:.2%}, Top: {bbox['Top']:.2%}")
        print(f"   Width: {bbox['Width']:.2%}, Height: {bbox['Height']:.2%}")

        # Qualidade da face
        if 'Quality' in face:
            quality = face['Quality']
            print(f"\n🎨 Qualidade da face:")
            print(f"   Brilho: {quality.get('Brightness', 0):.2f}")
            print(f"   Nitidez: {quality.get('Sharpness', 0):.2f}")

        print("\n" + "=" * 60)
        return True

    except ClientError as e:
        error_code = e.response['Error']['Code']
        error_message = e.response['Error']['Message']

        print(f"\n❌ ERRO AWS: {error_code}")
        print(f"   {error_message}")

        if error_code == 'InvalidImageFormatException':
            print("\n💡 Dica: Use imagens JPG ou PNG")
        elif error_code == 'ImageTooLargeException':
            print("\n💡 Dica: Reduza o tamanho da imagem (max 15MB)")
        elif error_code == 'InvalidS3ObjectException':
            print("\n💡 Dica: Verifique se as imagens são válidas")

        return False

    except Exception as e:
        print(f"\n❌ Erro inesperado: {e}")
        return False

if __name__ == '__main__':
    if len(sys.argv) != 3:
        print("Uso: python test_face_match.py <selfie.jpg> <documento.jpg>")
        print("\nExemplo:")
        print("  docker exec wallclub-portais python /app/checkout/test_face_match.py /tmp/selfie.jpg /tmp/doc.jpg")
        sys.exit(1)

    source = sys.argv[1]
    target = sys.argv[2]

    success = compare_faces(source, target)
    sys.exit(0 if success else 1)
