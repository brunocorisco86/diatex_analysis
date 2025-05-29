# Análise de Dados do Experimento DIATEX

## Introdução

Este projeto apresenta uma análise de dados provenientes de um experimento com o produto DIATEX, da empresa SANEX. O objetivo principal é avaliar a eficácia do DIATEX na redução da cama do aviário (material utilizado para forrar o piso) e da volatilização de amônia (NH3) em ambientes de criação de frangos de corte. A análise compara dados de sensores instalados em aviários que receberam o tratamento com DIATEX com aviários de controle (TESTEMUNHA).

## Contexto do Experimento

Sensores foram instalados em aviários de características semelhantes e contemporâneos (mesmo período de criação) para coletar dados sobre as condições ambientais. Uma parte dos aviários recebeu o tratamento com o produto DIATEX, enquanto a outra serviu como grupo de controle (TESTEMUNHA), sem o tratamento. O foco da análise é comparar as métricas ambientais chave entre esses dois grupos.

## Dados

Os dados utilizados nesta análise são provenientes de um banco de dados SQLite localizado em `database/TESTE_DIATEX.db`. As principais variáveis consideradas na análise incluem:

*   **NH3:** Concentração de amônia (em ppm - partes por milhão)
*   **Temperatura:** Temperatura do ambiente (em °C - graus Celsius)
*   **Humedad:** Umidade relativa do ar (em %)
*   **idade_lote:** Idade do lote de aves (em dias)
*   **semana_vida:** Semana de vida do lote de aves

## Aplicação Streamlit (`app_cloud.py`)

A análise interativa dos dados é realizada através de uma aplicação web desenvolvida com Streamlit (`app_cloud.py`). A aplicação permite:

*   **Carregamento e Processamento de Dados:** Carrega os dados do banco de dados e realiza processamentos iniciais, como conversões de data/hora e criação de colunas derivadas (ex: `semana_vida`, `aviario`).
*   **Filtragem Interativa:** Oferece uma vasta gama de filtros para segmentar os dados, incluindo:
    *   Produtor
    *   Linhagem das aves
    *   Lote específico
    *   Aviário individual
    *   Período (intervalo de datas)
    *   Idade das aves (em dias)
    *   Semana de vida das aves
    *   Tipo de Tratamento (DIATEX ou TESTEMUNHA) para análises específicas.
*   **Visualizações Comparativas:**
    *   **Gráficos de Linha:** Comparam a evolução temporal de NH3, Temperatura e Umidade entre os tratamentos DIATEX e TESTEMUNHA.
    *   **Box Plots (Diagramas de Caixa):** Apresentam a distribuição estatística das mesmas variáveis para cada tratamento, auxiliando na visualização de diferenças.
*   **Análise de Correlação:** Gera matrizes de correlação entre NH3, Temperatura, Umidade e idade do lote, separadamente para os grupos DIATEX e TESTEMUNHA.
*   **Análise Estatística:**
    *   **Estatísticas Descritivas:** Fornece um resumo estatístico (média, desvio padrão, etc.) das variáveis chave para cada tratamento.
    *   **Testes t de Student:** Realiza testes t para amostras independentes para avaliar se as diferenças nas médias de NH3, Temperatura e Umidade entre os grupos são estatisticamente significativas.
*   **Conclusões e Recomendações:** Apresenta um resumo das médias, diferenças percentuais e os resultados dos testes t, culminando em uma recomendação sobre a eficácia do DIATEX, principalmente com foco na redução de amônia.

## Como Executar a Aplicação

Para executar a aplicação Streamlit localmente, siga os passos abaixo:

1.  **Pré-requisitos:**
    *   Python 3.x instalado.
    *   Git (para clonar o repositório, se necessário).

2.  **Clone o Repositório (se ainda não o fez):**
    ```bash
    git clone <URL_DO_REPOSITORIO_GIT> # Substitua pela URL correta do repositório
    cd <NOME_DO_DIRETORIO_DO_REPOSITORIO>
    ```

3.  **Instale as Dependências:**
    Navegue até a raiz do projeto (onde o arquivo `requirements.txt` está localizado) e execute:
    ```bash
    pip install -r requirements.txt
    ```

4.  **Execute a Aplicação Streamlit:**
    No mesmo diretório, execute:
    ```bash
    streamlit run app_cloud.py
    ```
    A aplicação deverá abrir automaticamente no seu navegador web.

## Estrutura do Repositório

*   `app_cloud.py`: Script principal da aplicação Streamlit.
*   `database/TESTE_DIATEX.db`: Banco de dados SQLite contendo os dados do experimento.
*   `requirements.txt`: Arquivo listando as dependências Python do projeto.
*   `README.md`: Este arquivo, fornecendo uma visão geral do projeto.
*   `.devcontainer/`: Pasta com configurações para desenvolvimento em containers (se aplicável).
*   `LICENSE`: Arquivo de licença do projeto.
