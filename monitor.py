from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
import hashlib
import requests
from bs4 import BeautifulSoup
from datetime import datetime
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from . import db
from .models import MonitorConfig, MonitorURL, MonitorLog
from .forms import MonitorConfigForm, MonitorURLForm, TestEmailForm, RunMonitorForm

monitor = Blueprint('monitor', __name__)

@monitor.route('/')
@login_required
def index():
    """Página principal do monitor"""
    config = MonitorConfig.query.first()
    urls = MonitorURL.query.all()
    logs = MonitorLog.query.order_by(MonitorLog.timestamp.desc()).limit(20).all()
    
    config_form = MonitorConfigForm(obj=config)
    url_form = MonitorURLForm()
    test_email_form = TestEmailForm()
    run_monitor_form = RunMonitorForm()
    
    return render_template('monitor/index.html', 
                          config=config,
                          urls=urls,
                          logs=logs,
                          config_form=config_form,
                          url_form=url_form,
                          test_email_form=test_email_form,
                          run_monitor_form=run_monitor_form,
                          title='Configuração do Monitor')

@monitor.route('/config', methods=['POST'])
@login_required
def update_config():
    """Atualizar configurações do monitor"""
    form = MonitorConfigForm()
    if form.validate_on_submit():
        config = MonitorConfig.query.first()
        if not config:
            config = MonitorConfig()
            db.session.add(config)
        
        config.email_destinatario = form.email_destinatario.data
        config.email_remetente = form.email_remetente.data
        
        # Só atualiza a senha se uma nova for fornecida
        if form.email_senha.data:
            config.email_senha = form.email_senha.data
            
        config.smtp_servidor = form.smtp_servidor.data
        config.smtp_porta = form.smtp_porta.data
        config.horario_verificacao_1 = form.horario_verificacao_1.data
        config.horario_verificacao_2 = form.horario_verificacao_2.data
        config.horario_verificacao_3 = form.horario_verificacao_3.data
        config.ativo = form.ativo.data
        config.ultima_atualizacao = datetime.utcnow()
        
        db.session.commit()
        flash('Configurações atualizadas com sucesso!', 'success')
    else:
        for field, errors in form.errors.items():
            for error in errors:
                flash(f'Erro no campo {getattr(form, field).label.text}: {error}', 'danger')
    
    return redirect(url_for('monitor.index'))

@monitor.route('/url/add', methods=['POST'])
@login_required
def add_url():
    """Adicionar nova URL para monitoramento"""
    form = MonitorURLForm()
    if form.validate_on_submit():
        url = MonitorURL(
            nome=form.nome.data,
            url=form.url.data,
            ativo=form.ativo.data
        )
        db.session.add(url)
        
        # Registrar no log
        log = MonitorLog(
            url=url,
            tipo='configuracao',
            mensagem=f'URL adicionada para monitoramento: {url.nome}'
        )
        db.session.add(log)
        
        db.session.commit()
        flash('URL adicionada com sucesso!', 'success')
    else:
        for field, errors in form.errors.items():
            for error in errors:
                flash(f'Erro no campo {getattr(form, field).label.text}: {error}', 'danger')
    
    return redirect(url_for('monitor.index'))

@monitor.route('/url/<int:url_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_url(url_id):
    """Editar URL monitorada"""
    url = MonitorURL.query.get_or_404(url_id)
    form = MonitorURLForm(obj=url)
    
    if request.method == 'POST' and form.validate_on_submit():
        url.nome = form.nome.data
        url.url = form.url.data
        url.ativo = form.ativo.data
        
        # Registrar no log
        log = MonitorLog(
            url=url,
            tipo='configuracao',
            mensagem=f'URL editada: {url.nome}'
        )
        db.session.add(log)
        
        db.session.commit()
        flash('URL atualizada com sucesso!', 'success')
        return redirect(url_for('monitor.index'))
    
    return render_template('monitor/edit_url.html', form=form, url=url, title='Editar URL')

@monitor.route('/url/<int:url_id>/delete', methods=['POST'])
@login_required
def delete_url(url_id):
    """Excluir URL monitorada"""
    url = MonitorURL.query.get_or_404(url_id)
    nome = url.nome
    
    # Registrar no log
    log = MonitorLog(
        tipo='configuracao',
        mensagem=f'URL removida: {nome}'
    )
    db.session.add(log)
    
    db.session.delete(url)
    db.session.commit()
    
    flash(f'URL "{nome}" removida com sucesso!', 'success')
    return redirect(url_for('monitor.index'))

@monitor.route('/test-email', methods=['POST'])
@login_required
def test_email():
    """Testar envio de email com as configurações atuais"""
    config = MonitorConfig.query.first()
    if not config:
        flash('Configure as informações de email primeiro!', 'danger')
        return redirect(url_for('monitor.index'))
    
    if not config.email_remetente or not config.email_senha:
        flash('Configure o email remetente e senha para enviar emails!', 'danger')
        return redirect(url_for('monitor.index'))
    
    try:
        msg = MIMEMultipart()
        msg['From'] = config.email_remetente
        msg['To'] = config.email_destinatario
        msg['Subject'] = 'Teste de Email - Monitor Plataforma Brasil'
        
        body = """
        Este é um email de teste do Monitor de Atualizações da Plataforma Brasil.
        
        Se você está recebendo este email, significa que as configurações de email estão corretas.
        
        Data e hora do teste: {0}
        """.format(datetime.now().strftime('%d/%m/%Y %H:%M:%S'))
        
        msg.attach(MIMEText(body, 'plain'))
        
        server = smtplib.SMTP(config.smtp_servidor, config.smtp_porta)
        server.starttls()
        server.login(config.email_remetente, config.email_senha)
        server.send_message(msg)
        server.quit()
        
        # Registrar no log
        log = MonitorLog(
            tipo='email',
            mensagem=f'Email de teste enviado para {config.email_destinatario}'
        )
        db.session.add(log)
        db.session.commit()
        
        flash('Email de teste enviado com sucesso!', 'success')
    except Exception as e:
        flash(f'Erro ao enviar email: {str(e)}', 'danger')
        
        # Registrar erro no log
        log = MonitorLog(
            tipo='erro',
            mensagem=f'Erro ao enviar email de teste: {str(e)}'
        )
        db.session.add(log)
        db.session.commit()
    
    return redirect(url_for('monitor.index'))

@monitor.route('/run', methods=['POST'])
@login_required
def run_monitor():
    """Executar verificação manual"""
    urls = MonitorURL.query.filter_by(ativo=True).all()
    if not urls:
        flash('Não há URLs configuradas para monitoramento!', 'warning')
        return redirect(url_for('monitor.index'))
    
    atualizacoes = []
    
    for url_obj in urls:
        try:
            # Obter conteúdo da página
            response = requests.get(url_obj.url, timeout=30)
            response.raise_for_status()
            html = response.text
            
            # Extrair conteúdo relevante
            soup = BeautifulSoup(html, 'html.parser')
            for script in soup(["script", "style", "meta", "link"]):
                script.extract()
            
            content = soup.get_text()
            
            # Calcular hash
            hash_atual = hashlib.sha256(content.encode('utf-8')).hexdigest()
            
            # Registrar verificação no log
            log = MonitorLog(
                url=url_obj,
                tipo='verificacao',
                mensagem=f'Verificação manual realizada'
            )
            db.session.add(log)
            
            # Verificar se é a primeira verificação
            if not url_obj.ultimo_hash:
                url_obj.ultimo_hash = hash_atual
                url_obj.ultima_verificacao = datetime.utcnow()
                db.session.commit()
                continue
            
            # Comparar com hash anterior
            if hash_atual != url_obj.ultimo_hash:
                # Registrar atualização no log
                log = MonitorLog(
                    url=url_obj,
                    tipo='atualizacao',
                    mensagem=f'Atualização detectada em verificação manual'
                )
                db.session.add(log)
                
                atualizacoes.append(url_obj.nome)
                
                # Atualizar hash
                url_obj.ultimo_hash = hash_atual
            
            url_obj.ultima_verificacao = datetime.utcnow()
            db.session.commit()
            
        except Exception as e:
            # Registrar erro no log
            log = MonitorLog(
                url=url_obj,
                tipo='erro',
                mensagem=f'Erro na verificação manual: {str(e)}'
            )
            db.session.add(log)
            db.session.commit()
    
    if atualizacoes:
        flash(f'Atualizações detectadas em: {", ".join(atualizacoes)}', 'success')
        
        # Enviar email de notificação
        config = MonitorConfig.query.first()
        if config and config.email_remetente and config.email_senha:
            try:
                msg = MIMEMultipart()
                msg['From'] = config.email_remetente
                msg['To'] = config.email_destinatario
                msg['Subject'] = 'Alerta: Atualizações na Plataforma Brasil'
                
                body = """
                Atualizações detectadas na Plataforma Brasil:
                
                {0}
                
                Data e hora da verificação: {1}
                
                Acesse a Plataforma Brasil para verificar as mudanças: https://plataformabrasil.saude.gov.br/login.jsf
                """.format(
                    "\n".join([f"- {nome}" for nome in atualizacoes]),
                    datetime.now().strftime('%d/%m/%Y %H:%M:%S')
                )
                
                msg.attach(MIMEText(body, 'plain'))
                
                server = smtplib.SMTP(config.smtp_servidor, config.smtp_porta)
                server.starttls()
                server.login(config.email_remetente, config.email_senha)
                server.send_message(msg)
                server.quit()
                
                # Registrar no log
                log = MonitorLog(
                    tipo='email',
                    mensagem=f'Email de notificação enviado para {config.email_destinatario}'
                )
                db.session.add(log)
                db.session.commit()
                
                flash('Email de notificação enviado!', 'success')
            except Exception as e:
                flash(f'Erro ao enviar email de notificação: {str(e)}', 'danger')
                
                # Registrar erro no log
                log = MonitorLog(
                    tipo='erro',
                    mensagem=f'Erro ao enviar email de notificação: {str(e)}'
                )
                db.session.add(log)
                db.session.commit()
    else:
        flash('Nenhuma atualização detectada.', 'info')
    
    return redirect(url_for('monitor.index'))

@monitor.route('/logs')
@login_required
def view_logs():
    """Visualizar todos os logs"""
    page = request.args.get('page', 1, type=int)
    logs = MonitorLog.query.order_by(MonitorLog.timestamp.desc()).paginate(
        page=page, per_page=50, error_out=False)
    
    return render_template('monitor/logs.html', logs=logs, title='Logs do Monitor')
