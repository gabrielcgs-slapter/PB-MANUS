#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Arquivo principal para execução da aplicação
Este arquivo serve como ponto de entrada para a aplicação
"""

from app import create_app

app = create_app()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000)
