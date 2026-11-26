from django.urls import path
from . import views

urlpatterns = [
    # ==========================================================================
    # ROTAS DE ACESSO E SESSÃO
    # ==========================================================================
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('', views.dashboard, name='dashboard'),

    # ==========================================================================
    # GESTÃO DE CLIENTES
    # ==========================================================================
    path('clientes/', views.listar_clientes, name='listar_clientes'),
    path('clientes/inativar/<int:id>/', views.inativar_cliente, name='inativar_cliente'),
    path('clientes/ativar/<int:id>/', views.ativar_cliente, name='ativar_cliente'),

    # ==========================================================================
    # GESTÃO DE EQUIPAMENTOS
    # ==========================================================================
    path('equipamentos/', views.listar_equipamentos, name='listar_equipamentos'),
    path('equipamentos/inativar/<int:id>/', views.inativar_equipamento, name='inativar_equipamento'),
    path('equipamentos/ativar/<int:id>/', views.ativar_equipamento, name='ativar_equipamento'),

    # ==========================================================================
    # GESTÃO DE EQUIPE TÉCNICA
    # ==========================================================================
    path('tecnicos/', views.listar_tecnicos, name='listar_tecnicos'),
    path('tecnicos/inativar/<int:id>/', views.inativar_tecnico, name='inativar_tecnico'),
    path('tecnicos/ativar/<int:id>/', views.ativar_tecnico, name='ativar_tecnico'),

    # ==========================================================================
    # CADASTROS DE APOIO (MARCAS E FORMAS DE PAGAMENTO)
    # ==========================================================================
    path('apoio/', views.cadastros_apoio, name='cadastros_apoio'),
    path('apoio/marca/inativar/<int:id>/', views.inativar_marca, name='inativar_marca'),
    path('apoio/marca/ativar/<int:id>/', views.ativar_marca, name='ativar_marca'),
    path('apoio/forma/inativar/<int:id>/', views.inativar_forma_pgto, name='inativar_forma_pgto'),
    path('apoio/forma/ativar/<int:id>/', views.ativar_forma_pgto, name='ativar_forma_pgto'),

    # ==========================================================================
    # GESTÃO DE ORDENS DE SERVIÇO
    # ==========================================================================
    path('ordens/', views.listar_ordens, name='listar_ordens'),
    path('ordens/inativar/<int:id>/', views.inativar_ordem, name='inativar_ordem'),
    path('ordens/ativar/<int:id>/', views.ativar_ordem, name='ativar_ordem'),

    # ==========================================================================
    # GESTÃO FINANCEIRA (FLUXO DE CAIXA E RECEBIMENTOS)
    # ==========================================================================
    path('financeiro/', views.financeiro, name='financeiro'),
    path('financeiro/baixar/<int:id>/', views.baixar_pagamento_os, name='baixar_pagamento_os'),
]