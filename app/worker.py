#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Worker para execução de tarefas agendadas
Este arquivo implementa um worker para executar verificações periódicas
"""

import os
import time
import logging
import schedule
import datetime
from app import create_app, db
from app.models import MonitorConfig, MonitorURL, MonitorLog, CAAE, CAAELog
from app.caae_scraper import executar_verificacao_caae, enviar_notificacao_atualizacoes

# Configuração de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("worker.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def verificar_atualizacoes_urls():
    """Verifica atualizações nas URLs monitoradas"""
    logger.info("Iniciando verificação de URLs")
    
    app = create_app()
    with app.app_context():
        config = MonitorConfig.query.first()
        
        if not config or not config.ativo:
            logger.info("Monitoramento desativado ou não configurado")
            return
        
        urls = MonitorURL.query.filter_by(ativo=True).all()
        if not urls:
            logger.info("Não há URLs configuradas para monitoramento")
            return
        
        import requests
        from bs4 import BeautifulSoup
        import hashlib
        
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
                    mensagem=f'Verificação automática realizada'
                )
                db.session.add(log)
                
                # Verificar se é a primeira verificação
                if not url_obj.ultimo_hash:
                    url_obj.ultimo_hash = hash_atual
                    url_obj.ultima_verificacao = datetime.datetime.utcnow()
                    db.session.commit()
                    continue
                
                # Comparar com hash anterior
                if hash_atual != url_obj.ultimo_hash:
                    # Registrar atualização no log
                    log = MonitorLog(
                        url=url_obj,
                        tipo='atualizacao',
                        mensagem=f'Atualização detectada em verificação automática'
                    )
                    db.session.add(log)
                    
                    atualizacoes.append(url_obj.nome)
                    
                    # Atualizar hash
                    url_obj.ultimo_hash = hash_atual
                
                url_obj.ultima_verificacao = datetime.datetime.utcnow()
                db.session.commit()
                
            except Exception as e:
                # Registrar erro no log
                log = MonitorLog(
                    url=url_obj,
                    tipo='erro',
                    mensagem=f'Erro na verificação automática: {str(e)}'
                )
                db.session.add(log)
                db.session.commit()
        
        if atualizacoes and config.email_remetente and config.email_senha:
            try:
                from email.mime.text import MIMEText
                from email.mime.multipart import MIMEMultipart
                import smtplib
                
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
                    datetime.datetime.now().strftime('%d/%m/%Y %H:%M:%S')
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
                
                logger.info(f"Email de notificação enviado para {config.email_destinatario}")
            except Exception as e:
                # Registrar erro no log
                log = MonitorLog(
                    tipo='erro',
                    mensagem=f'Erro ao enviar email de notificação: {str(e)}'
                )
                db.session.add(log)
                db.session.commit()
                logger.error(f"Erro ao enviar email: {str(e)}")
        
        logger.info(f"Verificação de URLs concluída. {len(atualizacoes)} atualizações encontradas.")

def verificar_atualizacoes_caae():
    """Verifica atualizações nos CAAEs monitorados"""
    logger.info("Iniciando verificação de CAAEs")
    
    app = create_app()
    with app.app_context():
        config = MonitorConfig.query.first()
        
        if not config or not config.ativo:
            logger.info("Monitoramento desativado ou não configurado")
            return
        
        caae_count = CAAE.query.filter_by(ativo=True).count()
        if caae_count == 0:
            logger.info("Não há CAAEs configurados para monitoramento")
            return
        
        # Verificar se há credenciais configuradas
        if not hasattr(config, 'login_plataforma') or not hasattr(config, 'senha_plataforma'):
            logger.error("Credenciais da Plataforma Brasil não configuradas")
            return
        
        # Executar verificação
        try:
            atualizacoes = executar_verificacao_caae(
                config.login_plataforma,
                config.senha_plataforma,
                headless=True
            )
            
            # Enviar notificação se houver atualizações
            if atualizacoes > 0:
                enviar_notificacao_atualizacoes(
                    config.email_remetente,
                    config.email_senha,
                    config.email_destinatario,
                    config.smtp_servidor,
                    config.smtp_porta
                )
            
            logger.info(f"Verificação de CAAEs concluída. {atualizacoes} atualizações encontradas.")
        except Exception as e:
            logger.error(f"Erro durante verificação de CAAEs: {str(e)}")

def agendar_verificacoes():
    """Agenda as verificações com base nas configurações"""
    app = create_app()
    with app.app_context():
        config = MonitorConfig.query.first()
        
        if not config:
            logger.warning("Configurações não encontradas. Usando horários padrão.")
            horario1 = "09:00"
            horario2 = "13:00"
            horario3 = "17:00"
        else:
            horario1 = config.horario_verificacao_1
            horario2 = config.horario_verificacao_2
            horario3 = config.horario_verificacao_3
        
        # Agendar verificações de URLs
        schedule.every().day.at(horario1).do(verificar_atualizacoes_urls)
        schedule.every().day.at(horario2).do(verificar_atualizacoes_urls)
        schedule.every().day.at(horario3).do(verificar_atualizacoes_urls)
        
        # Agendar verificações de CAAEs (uma vez por dia)
        schedule.every().day.at(horario2).do(verificar_atualizacoes_caae)
        
        logger.info(f"Verificações agendadas para {horario1}, {horario2} e {horario3}")

if __name__ == "__main__":
    logger.info("Iniciando worker de monitoramento")
    
    # Agendar verificações
    agendar_verificacoes()
    
    # Executar loop principal
    while True:
        schedule.run_pending()
        time.sleep(60)  # Verificar a cada minuto
