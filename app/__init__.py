#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Arquivo de inicialização da aplicação web
Este arquivo configura e inicia a aplicação Flask
"""

import os
from datetime import datetime
from flask import Flask, render_template
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_migrate import Migrate

# Inicialização das extensões
db = SQLAlchemy()
login_manager = LoginManager()
migrate = Migrate()

def create_app(test_config=None):
    # Criar e configurar a aplicação
    app = Flask(__name__, instance_relative_config=True)
    
    # Configuração padrão
    app.config.from_mapping(
        SECRET_KEY=os.environ.get('SECRET_KEY', 'dev_key_change_in_production'),
        SQLALCHEMY_DATABASE_URI=os.environ.get('DATABASE_URL', 'sqlite:///plataforma_brasil.db'),
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
    )

    if test_config is None:
        # Carregar a configuração da instância, se existir
        app.config.from_pyfile('config.py', silent=True)
    else:
        # Carregar a configuração de teste
        app.config.from_mapping(test_config)

    # Garantir que o diretório de instância existe
    try:
        os.makedirs(app.instance_path)
    except OSError:
        pass

    # Inicializar extensões com a aplicação
    db.init_app(app)
    login_manager.init_app(app)
    migrate.init_app(app, db)
    
    # Configurar login
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Por favor, faça login para acessar esta página.'
    
    # Importar modelos
    from . import models
    
    @login_manager.user_loader
    def load_user(user_id):
        return models.User.query.get(int(user_id))
    
    # Registrar blueprints
    from . import auth
    app.register_blueprint(auth.bp)
    
    from . import main
    app.register_blueprint(main.bp)
    
    from . import monitor
    app.register_blueprint(monitor.bp, url_prefix='/monitor')
    
    # Registrar filtros de template
    @app.template_filter('formatdatetime')
    def format_datetime(value, format="%d/%m/%Y %H:%M:%S"):
        if value is None:
            return ""
        return value.strftime(format)
    
    # Adicionar variáveis globais para templates
    @app.context_processor
    def inject_now():
        return {'now': datetime.utcnow()}
    
    # Página de erro 404
    @app.errorhandler(404)
    def page_not_found(e):
        return render_template('404.html'), 404
    
    # Página de erro 500
    @app.errorhandler(500)
    def internal_server_error(e):
        return render_template('500.html'), 500
    
    return app
