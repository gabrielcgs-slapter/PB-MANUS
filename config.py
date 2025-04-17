#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Arquivo de configuração para implantação
Este arquivo configura as variáveis de ambiente e parâmetros para implantação
"""

import os

# Configurações da aplicação
class Config:
    """Configuração base"""
    SECRET_KEY = os.environ.get('SECRET_KEY', 'chave_segura_para_producao')
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL', 'sqlite:///plataforma_brasil.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False

class DevelopmentConfig(Config):
    """Configuração de desenvolvimento"""
    DEBUG = True

class ProductionConfig(Config):
    """Configuração de produção"""
    DEBUG = False
    
    # Configurações de segurança para produção
    SESSION_COOKIE_SECURE = True
    REMEMBER_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    REMEMBER_COOKIE_HTTPONLY = True

# Configuração para o Gunicorn
bind = "0.0.0.0:8000"
workers = 3
timeout = 120
