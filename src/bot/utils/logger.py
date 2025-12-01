import logging
import sys
import traceback
from datetime import datetime
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Optional

class BotLogger:
    """
    Sistema de logging aprimorado para o bot Discord RAG
    """
    
    def __init__(self, name: str = "RAG_Bot", log_file: str = "logs/bot.log"):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.DEBUG)
        
        # Evita adicionar handlers múltiplas vezes
        if self.logger.handlers:
            return
            
        # Garante que o diretório existe
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)

        # Formatação detalhada com contexto
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(funcName)s - %(message)s'
        )
        
        # Handler para arquivo com rotação
        file_handler = RotatingFileHandler(
            log_file, 
            maxBytes=5*1024*1024,  # 5MB
            backupCount=5
        )
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(formatter)
        self.logger.addHandler(file_handler)
        
        # Handler para console
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(formatter)
        self.logger.addHandler(console_handler)
    
    def debug(self, message: str, **context):
        """Log de debug com contexto opcional"""
        self._log_with_context(logging.DEBUG, message, **context)
    
    def info(self, message: str, **context):
        """Log de informação com contexto opcional"""
        self._log_with_context(logging.INFO, message, **context)
    
    def warning(self, message: str, **context):
        """Log de aviso com contexto opcional"""
        self._log_with_context(logging.WARNING, message, **context)
    
    def error(self, message: str, **context):
        """Log de erro com contexto opcional"""
        self._log_with_context(logging.ERROR, message, **context)
    
    def critical(self, message: str, **context):
        """Log crítico com contexto opcional"""
        self._log_with_context(logging.CRITICAL, message, **context)
    
    def log_command(self, user_id: str, command: str, success: bool, duration: Optional[float] = None, **context):
        """Log específico para comandos do bot"""
        status = "SUCCESS" if success else "FAILED"
        duration_str = f" [Duration: {duration:.2f}s]" if duration is not None else ""
        message = f"COMMAND - User: {user_id}, Command: {command}, Status: {status}{duration_str}"
        self._log_with_context(logging.INFO, message, **context)
    
    def log_error_with_traceback(self, message: str, exception: Exception, **context):
        """Log de erro com traceback completo"""
        tb_str = traceback.format_exception(exception)
        context['traceback'] = ''.join(tb_str)
        self._log_with_context(logging.ERROR, message, **context)
    
    def log_pipeline_step(self, step: str, user_id: str, duration: Optional[float] = None, **context):
        """Log específico para etapas do pipeline RAG"""
        duration_str = f" [Duration: {duration:.2f}s]" if duration is not None else ""
        message = f"PIPELINE - User: {user_id}, Step: {step}{duration_str}"
        self._log_with_context(logging.INFO, message, **context)
    
    def _log_with_context(self, level: int, message: str, **context):
        """Método auxiliar para log com contexto estruturado"""
        if context:
            # Adiciona contexto estruturado à mensagem
            context_str = ", ".join([f"{k}={v}" for k, v in context.items()])
            full_message = f"{message} | Context: {{{context_str}}}"
        else:
            full_message = message
        self.logger.log(level, full_message)

# Instância global do logger
logger = BotLogger()
