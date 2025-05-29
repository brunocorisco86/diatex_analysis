import streamlit as st
import pandas as pd
import numpy as np
import sqlite3
import matplotlib.pyplot as plt
import seaborn as sns
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import re
import os
import tempfile
from scipy import stats
import datetime
from datetime import timedelta

# Configuração da página
st.set_page_config(
    page_title="Análise DIATEX",
    page_icon="🐔",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Função para carregar os dados do banco SQLite
@st.cache_data
def carregar_dados(caminho_db):
    # Conectar ao banco de dados
    conn = sqlite3.connect(caminho_db)
    
    # Carregar dados da tabela medicoes com join na tabela tratamentos
    query = """
    SELECT 
        m.Fecha, m.Hora, m.NH3, m.Temperatura, m.Humedad, 
        m.Nome_Arquivo, m.lote_composto, m.idade_lote, m.n_cama, m.teste,
        t.produtor, t.linhagem
    FROM medicoes m
    LEFT JOIN tratamentos t ON m.lote_composto = t.lote_composto AND m.teste = t.teste
    """
    df = pd.read_sql_query(query, conn)
    
    # Fechar conexão
    conn.close()
    
    # Converter colunas de data e hora
    df['Fecha'] = pd.to_datetime(df['Fecha'])
    df['data_hora'] = pd.to_datetime(df['Fecha'].astype(str) + ' ' + df['Hora'])
    
    # Criar coluna de semana de vida
    df['semana_vida'] = (df['idade_lote'] // 7) + 1
    
    # Criar coluna de aviário (extrair do nome do arquivo)
    df['aviario'] = df['Nome_Arquivo'].str.extract(r'(\d+)').astype(str)
    
    return df

# Função para criar gráficos comparativos
def criar_grafico_comparativo(df, variavel, filtro_lote=None, filtro_aviario=None, 
                             filtro_idade_min=None, filtro_idade_max=None, 
                             filtro_semana_min=None, filtro_semana_max=None, 
                             filtro_produtor=None, filtro_linhagem=None,
                             agrupar_por='dia'):
    # Aplicar filtros
    dados = df.copy()
    
    if filtro_lote:
        dados = dados[dados['lote_composto'] == filtro_lote]
    
    if filtro_aviario:
        dados = dados[dados['aviario'] == filtro_aviario]
    
    if filtro_idade_min is not None and filtro_idade_max is not None:
        dados = dados[(dados['idade_lote'] >= filtro_idade_min) & (dados['idade_lote'] <= filtro_idade_max)]
    
    if filtro_semana_min is not None and filtro_semana_max is not None:
        dados = dados[(dados['semana_vida'] >= filtro_semana_min) & (dados['semana_vida'] <= filtro_semana_max)]
    
    if filtro_produtor:
        dados = dados[dados['produtor'] == filtro_produtor]
    
    if filtro_linhagem:
        dados = dados[dados['linhagem'] == filtro_linhagem]
    
    # Definir agrupamento
    if agrupar_por == 'dia':
        dados['grupo'] = dados['Fecha'].dt.date
    elif agrupar_por == 'semana':
        dados['grupo'] = dados['semana_vida']
    else:  # hora
        dados['grupo'] = dados['data_hora'].dt.floor('H')
    
    # Agrupar dados
    dados_agrupados = dados.groupby(['grupo', 'teste'])[variavel].mean().reset_index()
    
    # Criar gráfico com Plotly
    fig = px.line(
        dados_agrupados, 
        x='grupo', 
        y=variavel, 
        color='teste',
        markers=True,
        title=f'Comparativo de {variavel} entre tratamentos',
        labels={'grupo': 'Período', variavel: variavel, 'teste': 'Tratamento'},
        color_discrete_map={'DIATEX': '#1f77b4', 'TESTEMUNHA': '#ff7f0e'}
    )
    
    # Adicionar estatísticas no título
    media_diatex = dados[dados['teste'] == 'DIATEX'][variavel].mean()
    media_testemunha = dados[dados['teste'] == 'TESTEMUNHA'][variavel].mean()
    
    fig.update_layout(
        title=f'Comparativo de {variavel} entre tratamentos<br><sup>Média DIATEX: {media_diatex:.2f} | Média TESTEMUNHA: {media_testemunha:.2f}</sup>',
        xaxis_title='Período',
        yaxis_title=variavel,
        legend_title='Tratamento',
        hovermode='x unified'
    )
    
    return fig

# Função para realizar teste T
def realizar_teste_t(df, variavel, filtro_lote=None, filtro_aviario=None, 
                    filtro_idade_min=None, filtro_idade_max=None, 
                    filtro_semana_min=None, filtro_semana_max=None,
                    filtro_produtor=None, filtro_linhagem=None):
    # Aplicar filtros
    dados = df.copy()
    
    if filtro_lote:
        dados = dados[dados['lote_composto'] == filtro_lote]
    
    if filtro_aviario:
        dados = dados[dados['aviario'] == filtro_aviario]
    
    if filtro_idade_min is not None and filtro_idade_max is not None:
        dados = dados[(dados['idade_lote'] >= filtro_idade_min) & (dados['idade_lote'] <= filtro_idade_max)]
    
    if filtro_semana_min is not None and filtro_semana_max is not None:
        dados = dados[(dados['semana_vida'] >= filtro_semana_min) & (dados['semana_vida'] <= filtro_semana_max)]
    
    if filtro_produtor:
        dados = dados[dados['produtor'] == filtro_produtor]
    
    if filtro_linhagem:
        dados = dados[dados['linhagem'] == filtro_linhagem]
    
    # Separar dados por tratamento
    diatex = dados[dados['teste'] == 'DIATEX'][variavel].dropna()
    testemunha = dados[dados['teste'] == 'TESTEMUNHA'][variavel].dropna()
    
    # Verificar se há dados suficientes
    if len(diatex) < 2 or len(testemunha) < 2:
        return {
            'estatistica': None,
            'p_valor': None,
            'significativo': None,
            'interpretacao': 'Dados insuficientes para análise'
        }
    
    # Realizar teste T
    estatistica, p_valor = stats.ttest_ind(diatex, testemunha, equal_var=False)
    
    # Interpretar resultado
    significativo = p_valor < 0.05
    
    if significativo:
        if diatex.mean() > testemunha.mean():
            interpretacao = f"Há diferença significativa (p={p_valor:.4f}). DIATEX apresenta valores de {variavel} MAIORES que TESTEMUNHA."
        else:
            interpretacao = f"Há diferença significativa (p={p_valor:.4f}). DIATEX apresenta valores de {variavel} MENORES que TESTEMUNHA."
    else:
        interpretacao = f"Não há diferença significativa (p={p_valor:.4f}) entre os tratamentos para {variavel}."
    
    return {
        'estatistica': estatistica,
        'p_valor': p_valor,
        'significativo': significativo,
        'interpretacao': interpretacao
    }

# Função para criar matriz de correlação
def criar_matriz_correlacao(df, filtro_lote=None, filtro_aviario=None, 
                           filtro_idade_min=None, filtro_idade_max=None, 
                           filtro_semana_min=None, filtro_semana_max=None,
                           filtro_produtor=None, filtro_linhagem=None,
                           tratamento=None):
    # Aplicar filtros
    dados = df.copy()
    
    if filtro_lote:
        dados = dados[dados['lote_composto'] == filtro_lote]
    
    if filtro_aviario:
        dados = dados[dados['aviario'] == filtro_aviario]
    
    if filtro_idade_min is not None and filtro_idade_max is not None:
        dados = dados[(dados['idade_lote'] >= filtro_idade_min) & (dados['idade_lote'] <= filtro_idade_max)]
    
    if filtro_semana_min is not None and filtro_semana_max is not None:
        dados = dados[(dados['semana_vida'] >= filtro_semana_min) & (dados['semana_vida'] <= filtro_semana_max)]
    
    if filtro_produtor:
        dados = dados[dados['produtor'] == filtro_produtor]
    
    if filtro_linhagem:
        dados = dados[dados['linhagem'] == filtro_linhagem]
    
    if tratamento:
        dados = dados[dados['teste'] == tratamento]
    
    # Calcular correlação
    corr = dados[['NH3', 'Temperatura', 'Humedad', 'idade_lote']].corr()
    
    # Criar gráfico com Plotly
    fig = px.imshow(
        corr,
        text_auto=True,
        color_continuous_scale='RdBu_r',
        title=f'Matriz de Correlação {tratamento if tratamento else "Geral"}',
        zmin=-1, zmax=1
    )
    
    return fig

# Título principal
st.title('Análise de Dados - Experimento DIATEX')
st.markdown("""
Este aplicativo analisa dados do experimento DIATEX, que testa um produto para redução da volatilização 
de amônia durante a criação de frangos de corte. Compare os resultados entre aviários com DIATEX e TESTEMUNHA.
""")

# Caminho para o banco de dados local no repositório
caminho_db = "database/TESTE_DIATEX.db"

# Verificar se o arquivo existe
if not os.path.exists(caminho_db):
    st.error(f"Arquivo de banco de dados não encontrado em {caminho_db}.")
    st.info("Verifique se o arquivo está na pasta 'database' do repositório.")
    st.stop()

# Exibir informação sobre o arquivo carregado
st.info(f"Arquivo carregado: {os.path.basename(caminho_db)}")

# Carregar dados
with st.spinner('Carregando dados...'):
    df = carregar_dados(caminho_db)

# Sidebar para filtros
st.sidebar.title('Filtros')

# Filtro de produtor
produtores = ['Todos'] + sorted(df['produtor'].dropna().unique().tolist())
filtro_produtor = st.sidebar.selectbox('Produtor', produtores)
if filtro_produtor == 'Todos':
    filtro_produtor = None

# Filtro de linhagem
linhagens = ['Todas'] + sorted(df['linhagem'].dropna().unique().tolist())
filtro_linhagem = st.sidebar.selectbox('Linhagem', linhagens)
if filtro_linhagem == 'Todas':
    filtro_linhagem = None

# Filtro de lote
lotes = ['Todos'] + sorted(df['lote_composto'].unique().tolist())
filtro_lote = st.sidebar.selectbox('Lote', lotes)
if filtro_lote == 'Todos':
    filtro_lote = None

# Filtro de aviário
aviarios = ['Todos'] + sorted(df['aviario'].unique().tolist())
filtro_aviario = st.sidebar.selectbox('Aviário', aviarios)
if filtro_aviario == 'Todos':
    filtro_aviario = None

# Filtro de período
min_data = df['Fecha'].min().date()
max_data = df['Fecha'].max().date()
filtro_periodo = st.sidebar.date_input(
    'Período',
    value=(min_data, max_data),
    min_value=min_data,
    max_value=max_data
)

# Aplicar filtro de período
if len(filtro_periodo) == 2:
    df_filtrado = df[(df['Fecha'].dt.date >= filtro_periodo[0]) & 
                     (df['Fecha'].dt.date <= filtro_periodo[1])]
else:
    df_filtrado = df

# Filtro de idade com slider
min_idade = int(df['idade_lote'].min())
max_idade = int(df['idade_lote'].max())
st.sidebar.subheader('Idade (dias)')
filtro_idade_range = st.sidebar.slider(
    'Selecione o intervalo de idade',
    min_value=min_idade,
    max_value=max_idade,
    value=(min_idade, max_idade)
)
# Verificar se o slider está no intervalo completo
if filtro_idade_range == (min_idade, max_idade):
    filtro_idade_min, filtro_idade_max = None, None
else:
    filtro_idade_min, filtro_idade_max = filtro_idade_range

# Filtro de semana de vida com slider
min_semana = int(df['semana_vida'].min())
max_semana = int(df['semana_vida'].max())
st.sidebar.subheader('Semana de vida')
filtro_semana_range = st.sidebar.slider(
    'Selecione o intervalo de semanas',
    min_value=min_semana,
    max_value=max_semana,
    value=(min_semana, max_semana)
)
# Verificar se o slider está no intervalo completo
if filtro_semana_range == (min_semana, max_semana):
    filtro_semana_min, filtro_semana_max = None, None
else:
    filtro_semana_min, filtro_semana_max = filtro_semana_range

# Filtro de tratamento para análises específicas
tratamentos = ['Todos', 'DIATEX', 'TESTEMUNHA']
filtro_tratamento = st.sidebar.selectbox('Tratamento (para análises específicas)', tratamentos)
if filtro_tratamento == 'Todos':
    filtro_tratamento = None

# Opção de agrupamento
opcoes_agrupamento = ['dia', 'semana', 'hora']
agrupamento = st.sidebar.radio('Agrupar por', opcoes_agrupamento)

# Exibir estatísticas gerais
st.header('Estatísticas Gerais')

# Aplicar todos os filtros
dados_filtrados = df_filtrado.copy()

if filtro_lote:
    dados_filtrados = dados_filtrados[dados_filtrados['lote_composto'] == filtro_lote]

if filtro_aviario:
    dados_filtrados = dados_filtrados[dados_filtrados['aviario'] == filtro_aviario]

if filtro_idade_min is not None and filtro_idade_max is not None:
    dados_filtrados = dados_filtrados[(dados_filtrados['idade_lote'] >= filtro_idade_min) & 
                                     (dados_filtrados['idade_lote'] <= filtro_idade_max)]

if filtro_semana_min is not None and filtro_semana_max is not None:
    dados_filtrados = dados_filtrados[(dados_filtrados['semana_vida'] >= filtro_semana_min) & 
                                     (dados_filtrados['semana_vida'] <= filtro_semana_max)]

if filtro_produtor:
    dados_filtrados = dados_filtrados[dados_filtrados['produtor'] == filtro_produtor]

if filtro_linhagem:
    dados_filtrados = dados_filtrados[dados_filtrados['linhagem'] == filtro_linhagem]

# Exibir contagem de registros
col1, col2, col3 = st.columns(3)
with col1:
    st.metric("Total de Registros", f"{len(dados_filtrados):,}")
with col2:
    registros_diatex = len(dados_filtrados[dados_filtrados['teste'] == 'DIATEX'])
    st.metric("Registros DIATEX", f"{registros_diatex:,}")
with col3:
    registros_testemunha = len(dados_filtrados[dados_filtrados['teste'] == 'TESTEMUNHA'])
    st.metric("Registros TESTEMUNHA", f"{registros_testemunha:,}")

# Exibir estatísticas descritivas
st.subheader('Estatísticas Descritivas por Tratamento')
estatisticas = dados_filtrados.groupby('teste')[['NH3', 'Temperatura', 'Humedad']].describe()
st.dataframe(estatisticas)

# Gráficos comparativos
st.header('Gráficos Comparativos')

# Abas para diferentes variáveis
tab1, tab2, tab3 = st.tabs(["Amônia (NH3)", "Temperatura", "Umidade"])

with tab1:
    st.plotly_chart(
        criar_grafico_comparativo(
            dados_filtrados, 'NH3', 
            filtro_lote, filtro_aviario, 
            filtro_idade_min, filtro_idade_max, 
            filtro_semana_min, filtro_semana_max,
            filtro_produtor, filtro_linhagem,
            agrupar_por=agrupamento
        ),
        use_container_width=True
    )
    
    # Teste T para NH3
    resultado_teste_t = realizar_teste_t(
        dados_filtrados, 'NH3', 
        filtro_lote, filtro_aviario, 
        filtro_idade_min, filtro_idade_max, 
        filtro_semana_min, filtro_semana_max,
        filtro_produtor, filtro_linhagem
    )
    
    st.subheader('Análise Estatística - Teste T')
    st.write(resultado_teste_t['interpretacao'])
    
    if resultado_teste_t['p_valor'] is not None:
        # Criar gráfico de boxplot para visualizar a distribuição
        fig_box = px.box(
            dados_filtrados, 
            x='teste', 
            y='NH3',
            color='teste',
            title='Distribuição de NH3 por Tratamento',
            color_discrete_map={'DIATEX': '#1f77b4', 'TESTEMUNHA': '#ff7f0e'}
        )
        st.plotly_chart(fig_box, use_container_width=True)

with tab2:
    st.plotly_chart(
        criar_grafico_comparativo(
            dados_filtrados, 'Temperatura', 
            filtro_lote, filtro_aviario, 
            filtro_idade_min, filtro_idade_max, 
            filtro_semana_min, filtro_semana_max,
            filtro_produtor, filtro_linhagem,
            agrupar_por=agrupamento
        ),
        use_container_width=True
    )
    
    # Teste T para Temperatura
    resultado_teste_t = realizar_teste_t(
        dados_filtrados, 'Temperatura', 
        filtro_lote, filtro_aviario, 
        filtro_idade_min, filtro_idade_max, 
        filtro_semana_min, filtro_semana_max,
        filtro_produtor, filtro_linhagem
    )
    
    st.subheader('Análise Estatística - Teste T')
    st.write(resultado_teste_t['interpretacao'])
    
    if resultado_teste_t['p_valor'] is not None:
        # Criar gráfico de boxplot para visualizar a distribuição
        fig_box = px.box(
            dados_filtrados, 
            x='teste', 
            y='Temperatura',
            color='teste',
            title='Distribuição de Temperatura por Tratamento',
            color_discrete_map={'DIATEX': '#1f77b4', 'TESTEMUNHA': '#ff7f0e'}
        )
        st.plotly_chart(fig_box, use_container_width=True)

with tab3:
    st.plotly_chart(
        criar_grafico_comparativo(
            dados_filtrados, 'Humedad', 
            filtro_lote, filtro_aviario, 
            filtro_idade_min, filtro_idade_max, 
            filtro_semana_min, filtro_semana_max,
            filtro_produtor, filtro_linhagem,
            agrupar_por=agrupamento
        ),
        use_container_width=True
    )
    
    # Teste T para Umidade
    resultado_teste_t = realizar_teste_t(
        dados_filtrados, 'Humedad', 
        filtro_lote, filtro_aviario, 
        filtro_idade_min, filtro_idade_max, 
        filtro_semana_min, filtro_semana_max,
        filtro_produtor, filtro_linhagem
    )
    
    st.subheader('Análise Estatística - Teste T')
    st.write(resultado_teste_t['interpretacao'])
    
    if resultado_teste_t['p_valor'] is not None:
        # Criar gráfico de boxplot para visualizar a distribuição
        fig_box = px.box(
            dados_filtrados, 
            x='teste', 
            y='Humedad',
            color='teste',
            title='Distribuição de Umidade por Tratamento',
            color_discrete_map={'DIATEX': '#1f77b4', 'TESTEMUNHA': '#ff7f0e'}
        )
        st.plotly_chart(fig_box, use_container_width=True)

# Análises exploratórias adicionais
st.header('Análises Exploratórias Adicionais')

# Matriz de correlação
st.subheader('Matriz de Correlação')
col1, col2 = st.columns(2)

with col1:
    st.plotly_chart(
        criar_matriz_correlacao(
            dados_filtrados, 
            filtro_lote, filtro_aviario, 
            filtro_idade_min, filtro_idade_max, 
            filtro_semana_min, filtro_semana_max,
            filtro_produtor, filtro_linhagem,
            tratamento='DIATEX'
        ),
        use_container_width=True
    )

with col2:
    st.plotly_chart(
        criar_matriz_correlacao(
            dados_filtrados, 
            filtro_lote, filtro_aviario, 
            filtro_idade_min, filtro_idade_max, 
            filtro_semana_min, filtro_semana_max,
            filtro_produtor, filtro_linhagem,
            tratamento='TESTEMUNHA'
        ),
        use_container_width=True
    )

# Análise por idade/semana
st.subheader('Análise por Idade/Semana')

# Escolher visualização por idade ou semana
visualizacao = st.radio('Visualizar por:', ['Idade (dias)', 'Semana de vida'])

if visualizacao == 'Idade (dias)':
    # Aplicar filtros aos dados
    dados_filtrados_idade = dados_filtrados.copy()
    
    # Agrupar por idade
    dados_por_idade = dados_filtrados_idade.groupby(['idade_lote', 'teste'])[['NH3', 'Temperatura', 'Humedad']].mean().reset_index()
    
    # Criar gráficos
    fig = make_subplots(
        rows=3, cols=1,
        subplot_titles=('NH3 por Idade', 'Temperatura por Idade', 'Umidade por Idade'),
        shared_xaxes=True,
        vertical_spacing=0.1
    )
    
    # NH3
    for tratamento in ['DIATEX', 'TESTEMUNHA']:
        dados_trat = dados_por_idade[dados_por_idade['teste'] == tratamento]
        fig.add_trace(
            go.Scatter(
                x=dados_trat['idade_lote'], 
                y=dados_trat['NH3'],
                mode='lines+markers',
                name=f'{tratamento} - NH3',
                line=dict(color='#1f77b4' if tratamento == 'DIATEX' else '#ff7f0e')
            ),
            row=1, col=1
        )
    
    # Temperatura
    for tratamento in ['DIATEX', 'TESTEMUNHA']:
        dados_trat = dados_por_idade[dados_por_idade['teste'] == tratamento]
        fig.add_trace(
            go.Scatter(
                x=dados_trat['idade_lote'], 
                y=dados_trat['Temperatura'],
                mode='lines+markers',
                name=f'{tratamento} - Temperatura',
                line=dict(color='#1f77b4' if tratamento == 'DIATEX' else '#ff7f0e')
            ),
            row=2, col=1
        )
    
    # Umidade
    for tratamento in ['DIATEX', 'TESTEMUNHA']:
        dados_trat = dados_por_idade[dados_por_idade['teste'] == tratamento]
        fig.add_trace(
            go.Scatter(
                x=dados_trat['idade_lote'], 
                y=dados_trat['Humedad'],
                mode='lines+markers',
                name=f'{tratamento} - Umidade',
                line=dict(color='#1f77b4' if tratamento == 'DIATEX' else '#ff7f0e')
            ),
            row=3, col=1
        )
    
    fig.update_layout(
        height=800,
        title_text='Variáveis por Idade das Aves',
        showlegend=True,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        )
    )
    
    fig.update_xaxes(title_text='Idade (dias)', row=3, col=1)
    fig.update_yaxes(title_text='NH3', row=1, col=1)
    fig.update_yaxes(title_text='Temperatura', row=2, col=1)
    fig.update_yaxes(title_text='Umidade', row=3, col=1)
    
    st.plotly_chart(fig, use_container_width=True)
    
else:  # Semana de vida
    # Aplicar filtros aos dados
    dados_filtrados_semana = dados_filtrados.copy()
    
    # Agrupar por semana
    dados_por_semana = dados_filtrados_semana.groupby(['semana_vida', 'teste'])[['NH3', 'Temperatura', 'Humedad']].mean().reset_index()
    
    # Criar gráficos
    fig = make_subplots(
        rows=3, cols=1,
        subplot_titles=('NH3 por Semana', 'Temperatura por Semana', 'Umidade por Semana'),
        shared_xaxes=True,
        vertical_spacing=0.1
    )
    
    # NH3
    for tratamento in ['DIATEX', 'TESTEMUNHA']:
        dados_trat = dados_por_semana[dados_por_semana['teste'] == tratamento]
        fig.add_trace(
            go.Scatter(
                x=dados_trat['semana_vida'], 
                y=dados_trat['NH3'],
                mode='lines+markers',
                name=f'{tratamento} - NH3',
                line=dict(color='#1f77b4' if tratamento == 'DIATEX' else '#ff7f0e')
            ),
            row=1, col=1
        )
    
    # Temperatura
    for tratamento in ['DIATEX', 'TESTEMUNHA']:
        dados_trat = dados_por_semana[dados_por_semana['teste'] == tratamento]
        fig.add_trace(
            go.Scatter(
                x=dados_trat['semana_vida'], 
                y=dados_trat['Temperatura'],
                mode='lines+markers',
                name=f'{tratamento} - Temperatura',
                line=dict(color='#1f77b4' if tratamento == 'DIATEX' else '#ff7f0e')
            ),
            row=2, col=1
        )
    
    # Umidade
    for tratamento in ['DIATEX', 'TESTEMUNHA']:
        dados_trat = dados_por_semana[dados_por_semana['teste'] == tratamento]
        fig.add_trace(
            go.Scatter(
                x=dados_trat['semana_vida'], 
                y=dados_trat['Humedad'],
                mode='lines+markers',
                name=f'{tratamento} - Umidade',
                line=dict(color='#1f77b4' if tratamento == 'DIATEX' else '#ff7f0e')
            ),
            row=3, col=1
        )
    
    fig.update_layout(
        height=800,
        title_text='Variáveis por Semana de Vida das Aves',
        showlegend=True,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        )
    )
    
    fig.update_xaxes(title_text='Semana de vida', row=3, col=1)
    fig.update_yaxes(title_text='NH3', row=1, col=1)
    fig.update_yaxes(title_text='Temperatura', row=2, col=1)
    fig.update_yaxes(title_text='Umidade', row=3, col=1)
    
    st.plotly_chart(fig, use_container_width=True)

# Conclusões
st.header('Conclusões')

# Calcular médias por tratamento
medias_nh3 = dados_filtrados.groupby('teste')['NH3'].mean()
medias_temp = dados_filtrados.groupby('teste')['Temperatura'].mean()
medias_umid = dados_filtrados.groupby('teste')['Humedad'].mean()

# Calcular diferenças percentuais
if 'DIATEX' in medias_nh3 and 'TESTEMUNHA' in medias_nh3:
    diff_nh3 = ((medias_nh3['DIATEX'] - medias_nh3['TESTEMUNHA']) / medias_nh3['TESTEMUNHA']) * 100
    diff_temp = ((medias_temp['DIATEX'] - medias_temp['TESTEMUNHA']) / medias_temp['TESTEMUNHA']) * 100
    diff_umid = ((medias_umid['DIATEX'] - medias_umid['TESTEMUNHA']) / medias_umid['TESTEMUNHA']) * 100
    
    # Resultados dos testes T
    resultado_nh3 = realizar_teste_t(
        dados_filtrados, 'NH3', 
        filtro_lote, filtro_aviario, 
        filtro_idade_min, filtro_idade_max, 
        filtro_semana_min, filtro_semana_max,
        filtro_produtor, filtro_linhagem
    )
    resultado_temp = realizar_teste_t(
        dados_filtrados, 'Temperatura', 
        filtro_lote, filtro_aviario, 
        filtro_idade_min, filtro_idade_max, 
        filtro_semana_min, filtro_semana_max,
        filtro_produtor, filtro_linhagem
    )
    resultado_umid = realizar_teste_t(
        dados_filtrados, 'Humedad', 
        filtro_lote, filtro_aviario, 
        filtro_idade_min, filtro_idade_max, 
        filtro_semana_min, filtro_semana_max,
        filtro_produtor, filtro_linhagem
    )
    
    # Exibir conclusões
    st.markdown(f"""
    ### Resumo das Análises
    
    Com base nos dados analisados e nos filtros aplicados, podemos concluir:
    
    1. **Amônia (NH3)**:
       - Média DIATEX: {medias_nh3['DIATEX']:.2f} ppm
       - Média TESTEMUNHA: {medias_nh3['TESTEMUNHA']:.2f} ppm
       - Diferença: {diff_nh3:.2f}% ({medias_nh3['DIATEX'] - medias_nh3['TESTEMUNHA']:.2f} ppm)
       - {resultado_nh3['interpretacao']}
    
    2. **Temperatura**:
       - Média DIATEX: {medias_temp['DIATEX']:.2f} °C
       - Média TESTEMUNHA: {medias_temp['TESTEMUNHA']:.2f} °C
       - Diferença: {diff_temp:.2f}% ({medias_temp['DIATEX'] - medias_temp['TESTEMUNHA']:.2f} °C)
       - {resultado_temp['interpretacao']}
    
    3. **Umidade**:
       - Média DIATEX: {medias_umid['DIATEX']:.2f}%
       - Média TESTEMUNHA: {medias_umid['TESTEMUNHA']:.2f}%
       - Diferença: {diff_umid:.2f}% ({medias_umid['DIATEX'] - medias_umid['TESTEMUNHA']:.2f}%)
       - {resultado_umid['interpretacao']}
    
    ### Recomendação
    
    """)
    
    # Recomendação baseada nos resultados
    if resultado_nh3['significativo'] and medias_nh3['DIATEX'] < medias_nh3['TESTEMUNHA']:
        st.success("""
        **O produto DIATEX demonstra eficácia na redução dos níveis de amônia.**
        
        Com base na análise estatística, há evidência significativa de que o DIATEX reduz a volatilização 
        de amônia nos aviários. Recomenda-se a adoção do produto para melhorar as condições ambientais 
        na criação de frangos de corte.
        """)
    elif resultado_nh3['significativo'] and medias_nh3['DIATEX'] > medias_nh3['TESTEMUNHA']:
        st.error("""
        **O produto DIATEX não demonstra eficácia na redução dos níveis de amônia.**
        
        Com base na análise estatística, há evidência significativa de que o DIATEX está associado a 
        níveis mais altos de amônia em comparação com o grupo testemunha. Não se recomenda a adoção 
        do produto com base nos dados analisados.
        """)
    else:
        st.warning("""
        **Os resultados são inconclusivos quanto à eficácia do DIATEX na redução dos níveis de amônia.**
        
        Com base na análise estatística, não há diferença significativa nos níveis de amônia entre 
        os tratamentos DIATEX e TESTEMUNHA. Recomenda-se a realização de mais testes para obter 
        resultados mais conclusivos.
        """)

# Rodapé

# Ajustar para GMT-3
agora_gmt3 = datetime.datetime.now() - timedelta(hours=3)
st.markdown("---")
st.markdown(f"""
<div style="text-align: center; color: gray; font-size: 0.8em;">
    Análise de Dados DIATEX | Dados atualizados em: {agora_gmt3.strftime('%d/%m/%Y %H:%M')} (GMT-3)
</div>
""", unsafe_allow_html=True)

# Informações sobre a versão Cloud
st.sidebar.markdown("---")
st.sidebar.info("""
**Versão Cloud**
Esta é a versão para Streamlit Community Cloud que acessa os dados diretamente do repositório.
""")
