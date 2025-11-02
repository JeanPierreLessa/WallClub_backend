"""
Configuração de Connection Pooling para Django
Otimização de performance para conexões de banco de dados
"""

# Configuração para Connection Pooling (Item 5)
DATABASE_POOL_CONFIG = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'OPTIONS': {
            'init_command': "SET sql_mode='STRICT_TRANS_TABLES'",
            'charset': 'utf8mb4',
            # Connection Pooling Settings
            'autocommit': True,
            'connect_timeout': 10,
            'read_timeout': 10,
            'write_timeout': 10,
            # Pool de conexões
            'max_connections': 100,
            'max_overflow': 20,
            'pool_recycle': 3600,  # 1 hora
            'pool_pre_ping': True,
            'pool_reset_on_return': 'commit',
        },
        # Configurações específicas do Django
        'CONN_MAX_AGE': 3600,  # Reutilizar conexões por 1 hora
        'CONN_HEALTH_CHECKS': True,
        'ATOMIC_REQUESTS': True,  # Garante consistência transacional
    }
}

# Cache Configuration para Redis (se disponível)
CACHE_CONFIG = {
    'default': {
        'BACKEND': 'django.core.cache.backends.redis.RedisCache',
        'LOCATION': 'redis://wallclub-redis:6379/1',  # Usa hostname ao invés de IP
        'TIMEOUT': 300,  # 5 minutos default
        'KEY_PREFIX': 'wallclub',
        'VERSION': 1,
    }
}

# Fallback para cache local se Redis não estiver disponível
CACHE_FALLBACK = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'wallclub-cache',
        'TIMEOUT': 300,
        'OPTIONS': {
            'MAX_ENTRIES': 1000,
            'CULL_FREQUENCY': 3,
        }
    }
}
