from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from . import db
from .models import MonitorConfig, MonitorLog

main = Blueprint('main', __name__)

@main.route('/')
def index():
    """Página inicial do site"""
    if current_user.is_authenticated:
        # Se o usuário estiver logado, mostrar estatísticas básicas
        config = MonitorConfig.query.first()
        recent_logs = MonitorLog.query.order_by(MonitorLog.timestamp.desc()).limit(5).all()
        return render_template('main/dashboard.html', 
                              config=config, 
                              recent_logs=recent_logs,
                              title='Dashboard')
    else:
        # Se não estiver logado, mostrar página de apresentação
        return render_template('main/landing.html', title='Monitor Plataforma Brasil')

@main.route('/about')
def about():
    """Página sobre o projeto"""
    return render_template('main/about.html', title='Sobre o Projeto')

@main.route('/help')
def help():
    """Página de ajuda"""
    return render_template('main/help.html', title='Ajuda')
