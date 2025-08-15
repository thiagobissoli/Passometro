import redis
import json
import pickle
from datetime import timedelta
from functools import wraps
from flask import current_app
import hashlib

class CacheManager:
    """Gerenciador de cache Redis para o sistema Passômetro"""
    
    def __init__(self, app=None):
        self.redis_client = None
        if app is not None:
            self.init_app(app)
    
    def init_app(self, app):
        """Inicializa o cache com a aplicação Flask"""
        self.redis_client = redis.Redis(
            host=app.config.get('REDIS_HOST', 'localhost'),
            port=app.config.get('REDIS_PORT', 6379),
            db=app.config.get('REDIS_DB', 0),
            decode_responses=True
        )
        
        # Testar conexão
        try:
            self.redis_client.ping()
            app.logger.info("Cache Redis conectado com sucesso")
        except redis.ConnectionError:
            app.logger.warning("Cache Redis não disponível - usando cache em memória")
            self.redis_client = None
    
    def get(self, key, default=None):
        """Obtém um valor do cache"""
        if not self.redis_client:
            return default
        
        try:
            value = self.redis_client.get(key)
            if value:
                return json.loads(value)
            return default
        except Exception:
            return default
    
    def set(self, key, value, timeout=None):
        """Define um valor no cache"""
        if not self.redis_client:
            return False
        
        try:
            serialized = json.dumps(value, default=str)
            if timeout:
                return self.redis_client.setex(key, timeout, serialized)
            else:
                return self.redis_client.set(key, serialized)
        except Exception:
            return False
    
    def delete(self, key):
        """Remove uma chave do cache"""
        if not self.redis_client:
            return False
        
        try:
            return self.redis_client.delete(key)
        except Exception:
            return False
    
    def clear_pattern(self, pattern):
        """Remove todas as chaves que correspondem ao padrão"""
        if not self.redis_client:
            return False
        
        try:
            keys = self.redis_client.keys(pattern)
            if keys:
                return self.redis_client.delete(*keys)
            return True
        except Exception:
            return False
    
    def get_or_set(self, key, callback, timeout=None):
        """Obtém do cache ou executa callback e armazena"""
        value = self.get(key)
        if value is not None:
            return value
        
        value = callback()
        self.set(key, value, timeout)
        return value
    
    def invalidate_user_cache(self, user_id):
        """Invalida cache relacionado a um usuário específico"""
        patterns = [
            f"user:{user_id}:*",
            f"dashboard:{user_id}:*",
            f"notifications:{user_id}:*"
        ]
        for pattern in patterns:
            self.clear_pattern(pattern)

# Instância global do cache
cache = CacheManager()

def cached(timeout=300, key_prefix='cache'):
    """Decorator para cachear resultados de funções"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Gerar chave única baseada na função e argumentos
            key_parts = [key_prefix, func.__name__]
            key_parts.extend([str(arg) for arg in args])
            key_parts.extend([f"{k}:{v}" for k, v in sorted(kwargs.items())])
            
            cache_key = hashlib.md5(':'.join(key_parts).encode()).hexdigest()
            
            # Tentar obter do cache
            result = cache.get(cache_key)
            if result is not None:
                return result
            
            # Executar função e cachear resultado
            result = func(*args, **kwargs)
            cache.set(cache_key, result, timeout)
            return result
        return wrapper
    return decorator

def invalidate_cache_pattern(pattern):
    """Decorator para invalidar cache após operações"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            result = func(*args, **kwargs)
            cache.clear_pattern(pattern)
            return result
        return wrapper
    return decorator

# Funções de cache específicas para o sistema
class DashboardCache:
    """Cache específico para dados do dashboard"""
    
    @staticmethod
    def get_dashboard_data(user_id, is_gestor, posto_id=None):
        """Obtém dados do dashboard com cache"""
        cache_key = f"dashboard:{user_id}:{is_gestor}:{posto_id}"
        return cache.get(cache_key)
    
    @staticmethod
    def set_dashboard_data(user_id, is_gestor, posto_id, data, timeout=300):
        """Armazena dados do dashboard no cache"""
        cache_key = f"dashboard:{user_id}:{is_gestor}:{posto_id}"
        cache.set(cache_key, data, timeout)
    
    @staticmethod
    def invalidate_user_dashboard(user_id):
        """Invalida cache do dashboard de um usuário"""
        cache.clear_pattern(f"dashboard:{user_id}:*")

class NotificationCache:
    """Cache específico para notificações"""
    
    @staticmethod
    def get_user_notifications(user_id, limit=10):
        """Obtém notificações do usuário com cache"""
        cache_key = f"notifications:{user_id}:{limit}"
        return cache.get(cache_key)
    
    @staticmethod
    def set_user_notifications(user_id, limit, data, timeout=60):
        """Armazena notificações no cache"""
        cache_key = f"notifications:{user_id}:{limit}"
        cache.set(cache_key, data, timeout)
    
    @staticmethod
    def invalidate_user_notifications(user_id):
        """Invalida cache de notificações de um usuário"""
        cache.clear_pattern(f"notifications:{user_id}:*")

class ReportCache:
    """Cache específico para relatórios"""
    
    @staticmethod
    def get_report_data(report_type, filters, timeout=1800):  # 30 minutos
        """Obtém dados de relatório com cache"""
        cache_key = f"report:{report_type}:{hash(str(filters))}"
        return cache.get(cache_key)
    
    @staticmethod
    def set_report_data(report_type, filters, data, timeout=1800):
        """Armazena dados de relatório no cache"""
        cache_key = f"report:{report_type}:{hash(str(filters))}"
        cache.set(cache_key, data, timeout)
    
    @staticmethod
    def invalidate_reports():
        """Invalida todos os caches de relatórios"""
        cache.clear_pattern("report:*") 