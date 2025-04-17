from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField, IntegerField, TimeField
from wtforms.validators import DataRequired, Email, Length, EqualTo, ValidationError, URL
from .models import User

class LoginForm(FlaskForm):
    """Formulário de login"""
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Senha', validators=[DataRequired()])
    remember_me = BooleanField('Lembrar-me')
    submit = SubmitField('Entrar')

class RegistrationForm(FlaskForm):
    """Formulário de registro"""
    name = StringField('Nome', validators=[DataRequired(), Length(min=3, max=100)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Senha', validators=[DataRequired(), Length(min=6)])
    password2 = PasswordField('Confirmar Senha', validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Registrar')
    
    def validate_email(self, email):
        user = User.query.filter_by(email=email.data).first()
        if user:
            raise ValidationError('Este email já está em uso. Por favor, use outro.')

class MonitorConfigForm(FlaskForm):
    """Formulário de configuração do monitor"""
    email_destinatario = StringField('Email para Receber Notificações', validators=[DataRequired(), Email()])
    email_remetente = StringField('Email Remetente (para enviar notificações)', validators=[Email()])
    email_senha = PasswordField('Senha do Email Remetente')
    smtp_servidor = StringField('Servidor SMTP', validators=[DataRequired()], default='smtp.gmail.com')
    smtp_porta = IntegerField('Porta SMTP', validators=[DataRequired()], default=587)
    horario_verificacao_1 = StringField('Horário de Verificação 1', validators=[DataRequired()], default='09:00')
    horario_verificacao_2 = StringField('Horário de Verificação 2', validators=[DataRequired()], default='13:00')
    horario_verificacao_3 = StringField('Horário de Verificação 3', validators=[DataRequired()], default='17:00')
    ativo = BooleanField('Monitoramento Ativo', default=True)
    submit = SubmitField('Salvar Configurações')

class MonitorURLForm(FlaskForm):
    """Formulário para adicionar/editar URLs monitoradas"""
    nome = StringField('Nome da Página', validators=[DataRequired()])
    url = StringField('URL', validators=[DataRequired(), URL()])
    ativo = BooleanField('Ativo', default=True)
    submit = SubmitField('Salvar URL')

class TestEmailForm(FlaskForm):
    """Formulário para testar envio de email"""
    submit = SubmitField('Enviar Email de Teste')

class RunMonitorForm(FlaskForm):
    """Formulário para executar verificação manual"""
    submit = SubmitField('Executar Verificação Agora')
