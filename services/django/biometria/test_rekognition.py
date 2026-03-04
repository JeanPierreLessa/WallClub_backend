"""
Script de teste para validar conexão com AWS Rekognition
Execute: python manage.py shell < checkout/test_rekognition.py
"""
import os
import boto3
from botocore.exceptions import ClientError, NoCredentialsError

def test_rekognition_connection():
    """Testa conexão básica com AWS Rekognition"""

    print("=" * 60)
    print("TESTE DE CONEXÃO AWS REKOGNITION")
    print("=" * 60)

    # Verificar variáveis de ambiente
    print("\n1. Verificando variáveis de ambiente...")
    aws_key = os.getenv('AWS_ACCESS_KEY_ID')
    aws_secret = os.getenv('AWS_SECRET_ACCESS_KEY')
    aws_region = os.getenv('AWS_REGION', 'us-east-1')

    if not aws_key:
        print("❌ AWS_ACCESS_KEY_ID não configurado")
        return False
    else:
        print(f"✅ AWS_ACCESS_KEY_ID: {aws_key[:10]}...")

    if not aws_secret:
        print("❌ AWS_SECRET_ACCESS_KEY não configurado")
        return False
    else:
        print(f"✅ AWS_SECRET_ACCESS_KEY: {'*' * 20}")

    print(f"✅ AWS_REGION: {aws_region}")

    # Criar cliente Rekognition
    print("\n2. Criando cliente Rekognition...")
    try:
        rekognition = boto3.client(
            'rekognition',
            aws_access_key_id=aws_key,
            aws_secret_access_key=aws_secret,
            region_name=aws_region
        )
        print("✅ Cliente Rekognition criado com sucesso")
    except Exception as e:
        print(f"❌ Erro ao criar cliente: {e}")
        return False

    # Testar permissões (vai dar erro de imagem mas confirma acesso)
    print("\n3. Testando permissões...")
    try:
        # Tentar detectar faces em imagem inexistente
        # Se der erro de acesso, não tem permissão
        # Se der erro de imagem, tem permissão!
        rekognition.detect_faces(
            Image={'S3Object': {'Bucket': 'test-bucket', 'Name': 'test.jpg'}},
            Attributes=['DEFAULT']
        )
    except ClientError as e:
        error_code = e.response['Error']['Code']

        if error_code == 'AccessDeniedException':
            print("❌ SEM PERMISSÃO - Usuário IAM não tem acesso ao Rekognition")
            print(f"   Erro: {e}")
            return False
        elif error_code in ['InvalidS3ObjectException', 'InvalidParameterException', 'NoSuchBucket']:
            print("✅ PERMISSÕES OK - Rekognition está acessível")
            print(f"   (Erro esperado de imagem: {error_code})")
            return True
        else:
            print(f"⚠️  Erro inesperado: {error_code}")
            print(f"   {e}")
            return False
    except NoCredentialsError:
        print("❌ Credenciais AWS não encontradas")
        return False
    except Exception as e:
        print(f"❌ Erro inesperado: {e}")
        return False

    print("\n" + "=" * 60)
    print("TESTE CONCLUÍDO COM SUCESSO! ✅")
    print("=" * 60)
    return True

if __name__ == '__main__':
    success = test_rekognition_connection()
    exit(0 if success else 1)
