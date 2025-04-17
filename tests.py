#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script para testar a aplicação web
Este script executa testes básicos para verificar se a aplicação está funcionando corretamente
"""

import os
import sys
import unittest
import tempfile
from app import create_app, db
from app.models import User, MonitorConfig, MonitorURL, CAAE

class TestApp(unittest.TestCase):
    """Testes para a aplicação web"""
    
    def setUp(self):
        """Configuração inicial para os testes"""
        self.db_fd, self.db_path = tempfile.mkstemp()
        self.app = create_app({
            'TESTING': True,
            'SQLALCHEMY_DATABASE_URI': f'sqlite:///{self.db_path}',
            'WTF_CSRF_ENABLED': False
        })
        self.client = self.app.test_client()
        self.app_context = self.app.app_context()
        self.app_context.push()
        db.create_all()
        
        # Criar usuário de teste
        from werkzeug.security import generate_password_hash
        user = User(
            name='Teste',
            email='teste@example.com',
            password_hash=generate_password_hash('senha123')
        )
        db.session.add(user)
        db.session.commit()
    
    def tearDown(self):
        """Limpeza após os testes"""
        db.session.remove()
        db.drop_all()
        self.app_context.pop()
        os.close(self.db_fd)
        os.unlink(self.db_path)
    
    def test_pagina_inicial(self):
        """Testa se a página inicial está acessível"""
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Monitor Plataforma Brasil', response.data)
    
    def test_login(self):
        """Testa o processo de login"""
        # Tenta login com credenciais corretas
        response = self.client.post('/auth/login', data={
            'email': 'teste@example.com',
            'password': 'senha123',
            'remember_me': False
        }, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Dashboard', response.data)
        
        # Tenta login com credenciais incorretas
        response = self.client.post('/auth/login', data={
            'email': 'teste@example.com',
            'password': 'senha_errada',
            'remember_me': False
        }, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Email ou senha inv', response.data)  # "inválidos" com acento
    
    def test_acesso_protegido(self):
        """Testa acesso a páginas protegidas"""
        # Tenta acessar página protegida sem login
        response = self.client.get('/monitor/', follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Login', response.data)
        
        # Faz login
        self.client.post('/auth/login', data={
            'email': 'teste@example.com',
            'password': 'senha123',
            'remember_me': False
        })
        
        # Tenta acessar página protegida com login
        response = self.client.get('/monitor/')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Configura', response.data)  # "Configuração" com acento
    
    def test_configuracao(self):
        """Testa a configuração do monitor"""
        # Faz login
        self.client.post('/auth/login', data={
            'email': 'teste@example.com',
            'password': 'senha123',
            'remember_me': False
        })
        
        # Adiciona configuração
        response = self.client.post('/monitor/config', data={
            'email_destinatario': 'gabriel.calazans@ini.fiocruz.br',
            'email_remetente': 'teste@gmail.com',
            'email_senha': 'senha_email',
            'smtp_servidor': 'smtp.gmail.com',
            'smtp_porta': 587,
            'horario_verificacao_1': '09:00',
            'horario_verificacao_2': '13:00',
            'horario_verificacao_3': '17:00',
            'ativo': True
        }, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'sucesso', response.data)
        
        # Verifica se a configuração foi salva
        config = MonitorConfig.query.first()
        self.assertIsNotNone(config)
        self.assertEqual(config.email_destinatario, 'gabriel.calazans@ini.fiocruz.br')
    
    def test_url(self):
        """Testa o gerenciamento de URLs"""
        # Faz login
        self.client.post('/auth/login', data={
            'email': 'teste@example.com',
            'password': 'senha123',
            'remember_me': False
        })
        
        # Adiciona URL
        response = self.client.post('/monitor/url/add', data={
            'nome': 'Página Principal',
            'url': 'https://plataformabrasil.saude.gov.br/login.jsf',
            'ativo': True
        }, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'sucesso', response.data)
        
        # Verifica se a URL foi salva
        url = MonitorURL.query.first()
        self.assertIsNotNone(url)
        self.assertEqual(url.nome, 'Página Principal')
    
    def test_caae(self):
        """Testa o gerenciamento de CAAEs"""
        # Faz login
        self.client.post('/auth/login', data={
            'email': 'teste@example.com',
            'password': 'senha123',
            'remember_me': False
        })
        
        # Adiciona CAAE
        response = self.client.post('/monitor/caae/add', data={
            'numero': '12345678.9.0000.1234',
            'titulo': 'Estudo de Teste',
            'pesquisador': 'Pesquisador Teste',
            'instituicao': 'Instituição Teste',
            'ativo': True
        }, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'sucesso', response.data)
        
        # Verifica se o CAAE foi salvo
        caae = CAAE.query.first()
        self.assertIsNotNone(caae)
        self.assertEqual(caae.numero, '12345678.9.0000.1234')

if __name__ == '__main__':
    unittest.main()
