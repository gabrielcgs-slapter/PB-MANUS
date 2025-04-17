from flask_login import UserMixin
from datetime import datetime
from . import db

class User(UserMixin, db.Model):
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

class CAAE(db.Model):
    """Estudos monitorados por CAAE"""
    id = db.Column(db.Integer, primary_key=True)
    numero = db.Column(db.String(20), nullable=False, unique=True)
    titulo = db.Column(db.String(255), nullable=True)
    pesquisador = db.Column(db.String(100), nullable=True)
    instituicao = db.Column(db.String(100), nullable=True)
    status = db.Column(db.String(50), nullable=True)
    ultima_atualizacao = db.Column(db.DateTime, nullable=True)
    ativo = db.Column(db.Boolean, default=True)
    
    def __repr__(self):
        return f'<CAAE {self.numero}>'

class CAAELog(db.Model):
    """Registros de verificações e atualizações de CAAEs"""
    id = db.Column(db.Integer, primary_key=True)
    caae_id = db.Column(db.Integer, db.ForeignKey('caae.id'), nullable=True)
    caae = db.relationship('CAAE', backref='logs')
    tipo = db.Column(db.String(20), nullable=False)  # 'verificacao', 'atualizacao', 'erro'
    status_anterior = db.Column(db.String(50), nullable=True)
    status_atual = db.Column(db.String(50), nullable=True)
    mensagem = db.Column(db.Text, nullable=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<CAAELog {self.tipo} {self.timestamp}>'
