#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script de inicialização do banco de dados
Este script cria o banco de dados e as tabelas necessárias para a aplicação
"""

import os
import sys
from datetime import datetime
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from werkzeug.security import generate_password_hash

# Configuração inicial do Flask
app = Flask(__name__)
app.config['SECRET_KEY'] = 'dev_key_change_in_production'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///plataforma_brasil.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Inicialização das extensões
db = SQLAlchemy(app)
login_manager = LoginManager(app)

# Definição dos modelos
class User(db.Model):
    """Modelo de usuário para autenticação"""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<User {self.email}>'

class MonitorConfig(db.Model):
    """Configurações do monitor de atualizações"""
    id = db.Column(db.Integer, primary_key=True)
    email_destinatario = db.Column(db.String(100), nullable=False)
    email_remetente = db.Column(db.String(100), nullable=True)
    email_senha = db.Column(db.String(100), nullable=True)
    smtp_servidor = db.Column(db.String(100), default='smtp.gmail.com')
    smtp_porta = db.Column(db.Integer, default=587)
    horario_verificacao_1 = db.Column(db.String(5), default='09:00')
    horario_verificacao_2 = db.Column(db.String(5), default='13:00')
    horario_verificacao_3 = db.Column(db.String(5), default='17:00')
    ativo = db.Column(db.Boolean, default=True)
    ultima_atualizacao = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<MonitorConfig {self.id}>'

class MonitorURL(db.Model):
    """URLs monitoradas pelo sistema"""
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    url = db.Column(db.String(255), nullable=False)
    ativo = db.Column(db.Boolean, default=True)
    ultimo_hash = db.Column(db.String(64), nullable=True)
    ultima_verificacao = db.Column(db.DateTime, nullable=True)
    
    def __repr__(self):
        return f'<MonitorURL {self.nome}>'

class MonitorLog(db.Model):
    """Registros de verificações e atualizações"""
    id = db.Column(db.Integer, primary_key=True)
    url_id = db.Column(db.Integer, db.ForeignKey('monitor_url.id'), nullable=True)
    url = db.relationship('MonitorURL', backref='logs')
    tipo = db.Column(db.String(20), nullable=False)  # 'verificacao', 'atualizacao', 'erro'
    mensagem = db.Column(db.Text, nullable=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<MonitorLog {self.tipo} {self.timestamp}>'

# Criar as tabelas no banco de dados
with app.app_context():
    db.create_all()
    
    # Verificar se já existe um usuário administrador
    if User.query.count() == 0:
        print("Criando usuário administrador padrão...")
        
        # Criar usuário administrador
        admin = User(
            name="Administrador",
            email="admin@example.com",
            password_hash=generate_password_hash("admin123")
        )
        db.session.add(admin)
        
        # Criar configuração inicial
        config = MonitorConfig(
            email_destinatario="gabriel.calazans@ini.fiocruz.br",
            email_remetente="",
            email_senha="",
            smtp_servidor="smtp.gmail.com",
            smtp_porta=587,
            horario_verificacao_1="09:00",
            horario_verificacao_2="13:00",
            horario_verificacao_3="17:00",
            ativo=True,
            ultima_atualizacao=datetime.utcnow()
        )
        db.session.add(config)
        
        # Criar URLs iniciais para monitoramento
        urls = [
            MonitorURL(
                nome="Página Principal",
                url="https://plataformabrasil.saude.gov.br/login.jsf",
                ativo=True
            ),
            MonitorURL(
                nome="Manuais",
                url="https://plataformabrasil.saude.gov.br/visao/publico/indexPublico.jsf",
                ativo=True
            )
        ]
        for url in urls:
            db.session.add(url)
        
        # Criar log inicial
        log = MonitorLog(
            tipo="configuracao",
            mensagem="Sistema inicializado com configurações padrão"
        )
        db.session.add(log)
        
        # Salvar alterações no banco de dados
        db.session.commit()
        
        print("Banco de dados inicializado com sucesso!")
    else:
        print("O banco de dados já está inicializado.")
