#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Integração do script PB3.py para monitoramento de CAAEs na Plataforma Brasil
Este módulo implementa a funcionalidade de vasculhar estudos por CAAE
"""

import os
import time
import hashlib
import logging
import datetime
import pytz
import re
import smtplib
import pandas as pd
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException, NoSuchElementException
from bs4 import BeautifulSoup
from webdriver_manager.chrome import ChromeDriverManager

from . import db
from .models import CAAE, CAAELog

# Configuração de logging
logger = logging.getLogger(__name__)

class PlataformaBrasilScraper:
    """Classe para vasculhar estudos por CAAE na Plataforma Brasil"""
    
    def __init__(self, login, senha, headless=True):
        """Inicializa o scraper com credenciais e configurações"""
        self.login = login
        self.senha = senha
        self.headless = headless
        self.driver = None
        self.wait = None
        self.timezone = pytz.timezone('Etc/GMT+3')
        
    def iniciar_navegador(self):
        """Inicializa o navegador Chrome com as configurações apropriadas"""
        options = Options()
        options.add_argument("--disable-gpu")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--blink-settings=imagesEnabled=false")
        options.add_argument("--disable-extensions")
        options.add_argument("--disable-popup-blocking")
        options.add_argument("--disable-infobars")
        
        if self.headless:
            options.add_argument("--headless")
            
        service = Service(ChromeDriverManager().install())
        
        self.driver = webdriver.Chrome(service=service, options=options)
        self.wait = WebDriverWait(self.driver, 300)
        self.driver.maximize_window()
        
        logger.info("Navegador Chrome inicializado")
        
    def fazer_login(self):
        """Realiza login na Plataforma Brasil"""
        logger.info("Abrindo Plataforma Brasil")
        self.driver.get("https://plataformabrasil.saude.gov.br/login.jsf")
        time.sleep(10)
        
        max_tentativas = 3
        tentativa = 0
        
        while tentativa < max_tentativas:
            try:
                self.wait.until(EC.element_to_be_clickable((By.XPATH,'/html/body/div[2]/div/div[3]/div/div/form[1]/input[4]')))
                self.driver.find_element(By.XPATH,'//*[@id="j_id19:email"]').clear()
                self.driver.find_element(By.XPATH,'//*[@id="j_id19:email"]').send_keys(self.login)
                self.driver.find_element(By.XPATH,'//*[@id="j_id19:senha"]').clear()
                self.driver.find_element(By.XPATH,'//*[@id="j_id19:senha"]').send_keys(self.senha)
                
                self.driver.find_element(By.XPATH, '//*[@id="j_id19"]/input[4]').click()
                time.sleep(2)
                
                try:   
                    self.driver.find_element(By.XPATH, 
                                        '//*[@id="formModalMsgUsuarioLogado:idBotaoInvalidarUsuarioLogado"]').click()
                except:
                    pass
                    
                try:
                    valid_login = self.driver.find_element(By.XPATH,"/html/body/div[2]/div/div[4]/div").text
                    if "sessão" in valid_login:
                        logger.info("Login realizado com sucesso")
                        return True
                except:
                    tentativa += 1
                    logger.warning(f"Tentativa de login {tentativa} falhou")
            except Exception as e:
                tentativa += 1
                logger.error(f"Erro ao fazer login: {str(e)}")
                
        logger.error("Falha ao fazer login após várias tentativas")
        return False
    
    def extrair_caae_validos(self):
        """Extrai todos os CAAEs válidos da página inicial"""
        logger.info("Extraindo CAAEs válidos")
        time.sleep(10)
        
        list_CAAE = []
        soup = BeautifulSoup(self.driver.page_source, 'html.parser')
        
        try:
            paginas0 = soup.find("table", class_="rich-dtascroller-table").text
            paginas0 = re.search((r'de (.*?) registro\(s\)'), paginas0).group(1)
            paginas = int((int(paginas0)-1)/10)
            
            for i in range(paginas+1):
                soup = BeautifulSoup(self.driver.page_source, 'html.parser')
                
                try:
                    time.sleep(10)
                    self.wait.until(EC.element_to_be_clickable((By.XPATH,'/html/body/div[2]/div/div[6]/div[1]/form/div[3]/div[2]/table/tfoot/tr/td/div/table/tbody/tr/td[6]'))).click()
                except:
                    pass
                
                a = []
                aa = soup.find_all("label")

                for label in aa:
                    a.append(label.text)
                
                for item in a:
                    if '5262' in item:  # Filtro específico, pode ser parametrizado
                        list_CAAE.append(item)
            
            list_CAAE = set(list_CAAE)
            list_CAAE = list(list_CAAE)
            list_CAAE = [item.replace("\n", "") if isinstance(item, str) else item for item in list_CAAE]
            logger.info(f"CAAEs válidos extraídos: {len(list_CAAE)}")
            
            return list_CAAE
        except Exception as e:
            logger.error(f"Erro ao extrair CAAEs: {str(e)}")
            return []
    
    def verificar_caae(self, caae_numero):
        """Verifica os detalhes de um CAAE específico"""
        logger.info(f"Verificando CAAE: {caae_numero}")
        
        max_retries = 3
        retry_count = 0
        
        while retry_count < max_retries:
            try:
                t1 = datetime.datetime.now(self.timezone)
                
                # Limpar campo de pesquisa e inserir CAAE
                self.driver.find_element(By.XPATH,'/html/body/div[2]/div/div[6]/div[1]/form/div[2]/div[2]/table[1]/tbody/tr/td[2]/table/tbody/tr[2]/td/input').clear()
                self.driver.find_element(By.XPATH,'/html/body/div[2]/div/div[6]/div[1]/form/div[2]/div[2]/table[1]/tbody/tr/td[2]/table/tbody/tr[2]/td/input').send_keys(caae_numero)
                self.driver.find_element(By.XPATH,'/html/body/div[2]/div/div[6]/div[1]/form/div[2]/div[2]/table[1]/tbody/tr/td[2]/table/tbody/tr[2]/td/input').send_keys('\ue006')
                
                # Tentar clicar na lupa várias vezes se necessário
                o = 0
                while o < 10:
                    try:
                        self.wait.until(EC.element_to_be_clickable((By.XPATH,'/html/body/div[2]/div/div[6]/div[1]/form/div[3]/div[2]/table/tbody/tr/td[10]/a/img'))).click()
                        break
                    except:
                        time.sleep(1)
                        o += 1
                
                time.sleep(5)
                
                # Extrair informações da página
                soup = BeautifulSoup(self.driver.page_source, 'html.parser')
                
                # Voltar ao menu
                self.wait.until(EC.element_to_be_clickable((By.XPATH,'/html/body/div[2]/div/div[3]/div[2]/form/a[2]'))).click()
                
                # Extrair nome do estudo
                nome_estudo = soup.find('td', class_="text-top").text[21:].replace('"',"")
                
                # Extrair pesquisador principal
                PI = soup.find_all("td")[6].text
                PI = PI.replace("\n", "")
                
                # Extrair histórico de trâmites
                a = soup.find(id='formDetalharProjeto:tableTramiteApreciacaoProjeto:tb')
                time.sleep(2)
                a = a.find_all('span')
                b = []
                
                for span in a:
                    b.append(span.text)
                
                # Extrair CAAE do estudo
                CAAE_estudo = soup.find_all("td")[15].text
                CAAE_estudo = CAAE_estudo.replace("\n", "")
                CAAE_estudo = CAAE_estudo.replace("CAAE: ","")
                
                # Extrair status atual
                status_atual = None
                if len(b) >= 8:
                    status_atual = b[4]  # Coluna "Perfil" do primeiro trâmite
                
                # Criar hash do conteúdo para detectar mudanças
                conteudo = f"{nome_estudo}|{PI}|{CAAE_estudo}|{status_atual}|{','.join(b[:16])}"
                hash_atual = hashlib.sha256(conteudo.encode('utf-8')).hexdigest()
                
                t2 = datetime.datetime.now(self.timezone)
                t = t2-t1
                
                logger.info(f"CAAE {CAAE_estudo} verificado em {str(t)[2:9]}")
                
                return {
                    'numero': CAAE_estudo,
                    'titulo': nome_estudo,
                    'pesquisador': PI,
                    'status': status_atual,
                    'hash': hash_atual,
                    'tramites': b[:24]  # Primeiros 3 trâmites (8 campos cada)
                }
                
            except Exception as e:
                retry_count += 1
                logger.error(f"Erro ao verificar CAAE {caae_numero}: {str(e)}. Tentativa {retry_count} de {max_retries}")
                
                try:
                    # Tentar voltar ao menu
                    self.wait.until(EC.element_to_be_clickable((By.XPATH,'/html/body/div[2]/div/div[3]/div[2]/form/a[2]'))).click()
                except:
                    pass
                    
                time.sleep(10)
        
        logger.error(f"Falha ao verificar CAAE {caae_numero} após {max_retries} tentativas")
        return None
    
    def verificar_todos_caae(self, caae_list=None):
        """Verifica todos os CAAEs da lista ou do banco de dados"""
        if not caae_list:
            # Se não for fornecida uma lista, usar CAAEs do banco de dados
            caae_list = [caae.numero for caae in CAAE.query.filter_by(ativo=True).all()]
        
        resultados = []
        atualizacoes = []
        count = 0
        
        for caae_numero in caae_list:
            resultado = self.verificar_caae(caae_numero)
            if resultado:
                resultados.append(resultado)
                
                # Verificar se o CAAE já existe no banco de dados
                caae_db = CAAE.query.filter_by(numero=resultado['numero']).first()
                
                if caae_db:
                    # Verificar se houve atualização
                    if caae_db.ultimo_hash != resultado['hash']:
                        status_anterior = caae_db.status
                        
                        # Atualizar informações
                        caae_db.titulo = resultado['titulo']
                        caae_db.pesquisador = resultado['pesquisador']
                        caae_db.status = resultado['status']
                        caae_db.ultimo_hash = resultado['hash']
                        caae_db.ultima_atualizacao = datetime.datetime.now(self.timezone)
                        
                        # Registrar atualização no log
                        log = CAAELog(
                            caae=caae_db,
                            tipo='atualizacao',
                            status_anterior=status_anterior,
                            status_atual=resultado['status'],
                            mensagem=f'Atualização detectada no CAAE {resultado["numero"]}'
                        )
                        db.session.add(log)
                        
                        atualizacoes.append(resultado)
                    else:
                        # Registrar verificação no log
                        log = CAAELog(
                            caae=caae_db,
                            tipo='verificacao',
                            mensagem=f'Verificação realizada para CAAE {resultado["numero"]}'
                        )
                        db.session.add(log)
                else:
                    # Criar novo CAAE no banco de dados
                    novo_caae = CAAE(
                        numero=resultado['numero'],
                        titulo=resultado['titulo'],
                        pesquisador=resultado['pesquisador'],
                        status=resultado['status'],
                        ultimo_hash=resultado['hash'],
                        ultima_atualizacao=datetime.datetime.now(self.timezone),
                        ativo=True
                    )
                    db.session.add(novo_caae)
                    
                    # Registrar adição no log
                    log = CAAELog(
                        caae=novo_caae,
                        tipo='configuracao',
                        status_atual=resultado['status'],
                        mensagem=f'CAAE {resultado["numero"]} adicionado ao monitoramento'
                    )
                    db.session.add(log)
                    
                    atualizacoes.append(resultado)
                
                db.session.commit()
            
            # Contador de progresso
            count += 1
            logger.info(f'Progresso: {count}/{len(caae_list)}')
        
        return resultados, atualizacoes
    
    def fechar(self):
        """Fecha o navegador"""
        if self.driver:
            self.driver.close()
            logger.info("Navegador fechado")

def executar_verificacao_caae(login, senha, headless=True):
    """Função principal para executar a verificação de CAAEs"""
    logger.info("Iniciando verificação de CAAEs")
    
    scraper = PlataformaBrasilScraper(login, senha, headless)
    
    try:
        scraper.iniciar_navegador()
        
        if scraper.fazer_login():
            # Verificar CAAEs cadastrados no banco de dados
            resultados, atualizacoes = scraper.verificar_todos_caae()
            
            logger.info(f"Verificação concluída. {len(resultados)} CAAEs verificados, {len(atualizacoes)} atualizações encontradas")
            return len(atualizacoes)
        else:
            logger.error("Não foi possível fazer login na Plataforma Brasil")
            return 0
    except Exception as e:
        logger.error(f"Erro durante a verificação de CAAEs: {str(e)}")
        return 0
    finally:
        scraper.fechar()

def enviar_notificacao_atualizacoes(email_remetente, senha_remetente, email_destinatario, smtp_servidor, smtp_porta):
    """Envia notificação por email sobre atualizações de CAAEs"""
    # Buscar atualizações recentes (últimas 24 horas)
    data_limite = datetime.datetime.now() - datetime.timedelta(hours=24)
    atualizacoes = CAAELog.query.filter(
        CAAELog.tipo == 'atualizacao',
        CAAELog.timestamp >= data_limite
    ).all()
    
    if not atualizacoes:
        logger.info("Nenhuma atualização recente para notificar")
        return False
    
    try:
        # Preparar conteúdo do email
        msg = MIMEMultipart()
        msg['From'] = email_remetente
        msg['To'] = email_destinatario
        msg['Subject'] = f'Atualizações na Plataforma Brasil - {datetime.datetime.now().strftime("%d/%m/%Y %H:%M")}'
        
        # Construir corpo do email
        corpo_email = f"""
        <meta http-equiv="Content-Type" content="text/html; charset=utf-8">
        <p>Olá,</p>
        <p>Foram detectadas atualizações nos seguintes CAAEs na Plataforma Brasil:</p>
        <table border="1" style="border-collapse: collapse; width: 100%;">
            <tr style="background-color: #f2f2f2;">
                <th style="padding: 8px; text-align: left;">CAAE</th>
                <th style="padding: 8px; text-align: left;">Título</th>
                <th style="padding: 8px; text-align: left;">Pesquisador</th>
                <th style="padding: 8px; text-align: left;">Status Anterior</th>
                <th style="padding: 8px; text-align: left;">Status Atual</th>
                <th style="padding: 8px; text-align: left;">Data/Hora</th>
            </tr>
        """
        
        for log in atualizacoes:
            corpo_email += f"""
            <tr>
                <td style="padding: 8px;">{log.caae.numero}</td>
                <td style="padding: 8px;">{log.caae.titulo}</td>
                <td style="padding: 8px;">{log.caae.pesquisador}</td>
                <td style="padding: 8px;">{log.status_anterior or '-'}</td>
                <td style="padding: 8px;">{log.status_atual or '-'}</td>
                <td style="padding: 8px;">{log.timestamp.strftime('%d/%m/%Y %H:%M')}</td>
            </tr>
            """
        
        corpo_email += """
        </table>
        <p>Para mais detalhes, acesse o sistema de monitoramento ou a Plataforma Brasil.</p>
        <p>Atenciosamente,<br>Sistema de Monitoramento da Plataforma Brasil</p>
        """
        
        msg.attach(MIMEText(corpo_email, 'html'))
        
        # Enviar email
        server = smtplib.SMTP(smtp_servidor, smtp_porta)
        server.starttls()
        server.login(email_remetente, senha_remetente)
        server.send_message(msg)
        server.quit()
        
        logger.info(f"Email de notificação enviado para {email_destinatario}")
        return True
    except Exception as e:
        logger.error(f"Erro ao enviar email de notificação: {str(e)}")
        return False
