# Simulador de Investimentos com Análise Fundamentalista da Bolsa de Valores Brasileira

Este projeto é um simulador interativo de investimentos focado na análise fundamentalista do mercado de ações brasileiro (B3). Desenvolvido com propósito educacional, o aplicativo permite que estudantes e investidores iniciantes pratiquem a seleção de ações e montagem de carteiras utilizando dados reais, porém em um ambiente seguro (sem risco financeiro real). A aplicação foi implementada em Python com o framework Streamlit, oferecendo uma interface simples para filtrar empresas por indicadores, simular cenários históricos e comparar resultados de estratégias de investimento. O foco está em ilustrar conceitos de análise fundamentalista de forma prática, convertendo métricas financeiras complexas em visualizações e insights acessíveis para fins pedagógicos.

## Funcionalidades principais

Filtro de ações por indicadores – Permite selecionar empresas com base em múltiplos fundamentalistas (ex.: P/L, ROE) e critérios personalizados do usuário. Os filtros facilitam a identificação de ações subavaliadas ou com características desejadas.

Montagem de carteira virtual – O usuário pode criar uma carteira simulada adicionando as ações filtradas. Há uma barra lateral para gerenciar os ativos selecionados (quantidade, peso, etc.), proporcionando um ambiente de experimentação sem riscos.

Simulação de investimentos históricos – Com a carteira definida, é possível simular aportes ao longo do tempo e ver como a carteira teria se comportado em determinado período no passado. A aplicação calcula retornos acumulados (com e sem dividendos), evolução do valor investido e outras métricas de desempenho de forma automatizada.

Análise comparativa de estratégias – Todas as simulações realizadas ficam registradas e podem ser comparadas entre si. O usuário consegue visualizar, lado a lado, resultados de diferentes estratégias (por exemplo, investir em anos distintos ou com composições de carteira diferentes) para entender o impacto do timing e da diversificação na rentabilidade final.

(Obs: Todos os resultados são exibidos por meio de gráficos e tabelas interativos, permitindo uma visualização clara da evolução dos indicadores e da carteira ao longo do tempo.)

## Extração e estruturação dos dados

A base de dados utilizada pelo simulador foi construída a partir de informações públicas da Bolsa de Valores Brasileira, com foco em dados trimestrais de 2010 a 2025. Para obter esses dados de forma automatizada e confiável, foi utilizada a API brapi.dev – um provedor que agrega dados fundamentalistas e históricos de ações brasileiras. O universo de ações (tickers) foi extraído do site Fundamentus, garantindo abrangência do mercado nacional. A partir da API, foram coletados dados financeiros de cada empresa (balanços patrimoniais, demonstrativos de resultados, fluxos de caixa, indicadores financeiros, etc.) e armazenados de forma padronizada.

Para garantir a qualidade e consistência, implementou-se um pipeline de engenharia de dados em camadas. Os principais passos desse pipeline incluem:

Coleta automatizada – Scripts Python realizaram requisições aos vários endpoints da API (módulos trimestrais como balanceSheetHistoryQuarterly, incomeStatementHistoryQuarterly, etc.) para cada empresa, cobrindo o período desejado. Os retornos brutos (em JSON) de cada empresa e módulo foram salvos integralmente como arquivos de log, preservando os dados originais para auditoria e reprocessamento futuro.

Tratamento e padronização – Os dados coletados passaram por limpeza e normalização: remoção de duplicatas, correção de formatos e nomes de campos (usando um dicionário de termos), e padronização de tipos (números, datas, textos). Campos ausentes foram mantidos nulos quando necessário, evitando introduzir valores artificiais. Todas as etapas importantes geram mensagens de log para facilitar o rastreio de eventuais problemas.

Integração em base única – As diversas tabelas retornadas pela API foram integradas em uma visão unificada por trimestre. Usando a chave composta Ticker + Data (data de atualização trimestral), as informações de diferentes módulos foram combinadas em um único registro por empresa em cada trimestre. Essa consolidação resultou em uma base de dados trimestral completa e consistente, facilitando consultas e cálculo de indicadores.

Camadas de dados e exportação – A arquitetura separou claramente os dados em camadas: bruta (arquivos JSON originais por ticker), tratada por módulo (arquivos CSV intermediários padronizados) e unificada (base final consolidada). Ao final do processo, obteve-se um arquivo CSV unificado contendo todos os fundamentos calculados para cada empresa/trimestre, pronto para uso no simulador. Essa organização em camadas torna o processo reprodutível e auditável, pois qualquer valor apresentado no simulador pode ser rastreado até sua fonte original na API.

## Indicadores fundamentalistas

No simulador, são calculados e apresentados os principais indicadores fundamentalistas usados na análise de empresas. Esses indicadores servem tanto como filtros na seleção de ações quanto como métricas de desempenho na análise. Os principais incluem:

P/L (Preço/Lucro) – Relação entre o preço da ação e o lucro por ação (indicador de valuation, mostra quantos anos o lucro paga o preço da ação).

P/VPA (Preço/Valor Patrimonial) – Compara o preço da ação com seu valor patrimonial líquido por ação (indica se a ação está avaliada acima ou abaixo do patrimônio contábil).

EV/EBIT e EV/EBITDA – Enterprise Value sobre EBIT (ou EBITDA) que mensura o valor da firma em relação ao lucro operacional, útil para comparar empresas com diferentes estruturas de capital.

ROE e ROA – Return on Equity (Retorno sobre Patrimônio) e Return on Assets (Retorno sobre Ativos), indicando respectivamente a rentabilidade do patrimônio dos acionistas e dos ativos totais da empresa.

Margens – Margem Líquida, Margem EBITDA, Margem Bruta, entre outras, mostrando a porcentagem da receita que se converte em lucro em diferentes etapas (indicadores de eficiência operacional).

Alavancagem – Métricas de endividamento, como Dívida/Patrimônio (relação entre dívida e capital próprio) e outros índices que avaliam a estrutura de capital e riscos financeiros.

Dividend Yield e métricas de dividendos – Retorno percentual em dividendos (dividendos/ preço da ação) e outros indicadores como payout (quanto do lucro é distribuído).

Crescimento – Taxas de crescimento de receita, lucro ou outros itens ao longo do tempo, indicando tendência de expansão do negócio.

Esses indicadores foram escolhidos por serem amplamente utilizados na análise fundamentalista clássica e por fornecerem um panorama abrangente da saúde financeira e valorização de uma empresa. No simulador, o usuário pode aplicar limites mínimos/máximos a esses indicadores para filtrar empresas (por exemplo, selecionar ações com P/L abaixo de 15 e ROE acima de 10%, etc.) e também visualizar a evolução histórica de cada métrica na análise detalhada de uma empresa.

## Tecnologias utilizadas

Linguagem: Python 3 – linguagem principal para desenvolvimento de todo o projeto (ETL dos dados e aplicação).

Framework web: Streamlit – utilizado para criar a interface web interativa do simulador de forma rápida e acessível.

Bibliotecas de dados: Pandas (manipulação de DataFrames e cálculo de indicadores), NumPy (operações numéricas) e outras bibliotecas do ecossistema Python científico para tratamento de dados.

API de dados financeiros: brapi.dev – fonte dos dados fundamentalistas e de preços históricos das ações brasileiras (B3) utilizada no projeto.

Fonte de ativos: Fundamentus – site utilizado para obter a lista de empresas/tickers da B3 analisadas.

Outras ferramentas: Bibliotecas de visualização de dados (como Matplotlib/Plotly para gráficos financeiros), requests (requisições HTTP para a API), e ferramentas de logging para registrar o processo de ETL.

## Como utilizar o simulador

Para executar o simulador localmente em seu computador, siga os passos abaixo:

Clonar ou baixar o projeto: Obtenha os arquivos do projeto a partir do repositório GitHub (ou pacote fornecido). Navegue até o diretório raiz do projeto.

Instalar as dependências: Certifique-se de ter o Python instalado (versão 3.x). Em seguida, instale as bibliotecas requeridas.

Isso instalará o Streamlit, Pandas e demais pacotes necessários.

Executar a aplicação Streamlit: No diretório do projeto, execute o comando:

streamlit run app.py


O Streamlit iniciará um servidor local e exibirá no terminal um URL (por padrão, http://localhost:8501). Abra esse endereço em seu navegador para acessar a interface do simulador.

Navegação na aplicação: A aplicação possui múltiplas páginas (seções), acessíveis através de um menu ou abas no próprio app (ex.: seleção de ações, análise, simulação, histórico). Utilize a barra lateral para gerenciar a carteira e alternar entre as funcionalidades.

## Estrutura de pastas: O projeto está organizado em módulos para separar a lógica de dados da interface. Abaixo está um resumo da estrutura de diretórios e arquivos principais:

📦 SimuladorFundamentalista
```
├── app.py               # Arquivo principal Streamlit (inicia a aplicação e configura páginas)
├── controller/          # Camada de controle (regras de negócio)
│   └── utils.py         # Funções utilitárias para cálculo de indicadores, carregamento de dados, etc.
├── view/                # Camada de interface (páginas da aplicação)
│   ├── lista.py         # Página 1 – Seleção de ações com filtros fundamentalistas
│   ├── analise.py       # Página 2 – Análise detalhada da empresa selecionada
│   ├── simulacao.py     # Página 3 – Simulação histórica de investimentos
│   ├── historico.py     # Página 4 – Histórico de simulações e comparações
│   └── sidebar.py       # Componente da barra lateral (gerenciamento da carteira)
└── data/                # (Opcional) Diretório com dados pré-processados (CSV unificado ou arquivos brutos)
```

---

Para usar o simulador, não é necessário modificar os arquivos – basta executar o app.py. A interface gráfica permitirá toda interação necessária. Certifique-se apenas de que os dados necessários (base consolidada CSV ou acesso à internet para a API) estejam disponíveis conforme as instruções do projeto.

## Exemplos de uso (Fluxos da Aplicação)

A seguir, descrevemos os quatro fluxos principais disponíveis na aplicação, que correspondem às páginas interativas do simulador:

1. Seleção de ações com filtros: Na página inicial, o usuário define critérios fundamentalistas para filtrar as empresas. É possível ajustar diversos filtros (por exemplo, definir um intervalo máximo para o P/L, exigir um ROE mínimo, etc.) e então gerar uma lista de ações que atendem a esses critérios. A tela exibe uma tabela de empresas filtradas com seus principais indicadores, e o usuário pode adicionar as ações desejadas à sua carteira virtual com um clique. Ex: O investidor aplica filtros como P/L < 15 e ROE > 10%, obtendo uma lista de ações que cumprem esses requisitos, e adiciona algumas delas à carteira para análise posterior.

2. Análise detalhada da empresa: Após selecionar uma ação específica, o usuário pode navegar para a página de análise aprofundada desse ativo. Nessa seção, o simulador mostra todos os indicadores fundamentalistas da empresa escolhida de forma gráfica e tabular, permitindo uma inspeção minuciosa. É possível observar a evolução histórica trimestral dos indicadores (P/L, margens, dívida, crescimento, etc.) e também comparar esses valores com médias do setor ou concorrentes. Ex: O investidor seleciona a empresa Sanepar (SAPR4) para análise detalhada. A aplicação exibe gráficos de tendência do ROE, margens de lucro e endividamento ao longo dos anos, bem como compara o P/L da Sanepar com o de outras empresas do setor de saneamento. Isso ajuda a verificar se a empresa mantém fundamentos consistentes e como ela se posiciona em relação aos pares.

3. Simulação de investimento histórica: Com a carteira configurada (ações escolhidas e quantidades definidas), o usuário parte para a página de simulação histórica. Aqui, é possível configurar um cenário de investimento passado, escolhendo o período de início e fim da simulação e o valor a ser investido. Ao iniciar a simulação, o sistema processa os dados históricos dos preços e dividendos das ações na carteira e apresenta um resumo dos resultados obtidos. São exibidos indicadores como retorno acumulado da carteira, valor final atingido, total de dividendos recebidos no período, volatilidade, entre outros. Gráficos ilustram a evolução temporal do patrimônio e a contribuição de cada ação para o resultado. Ex: O usuário simula um investimento de R$10.000,00 no período de 2018 a 2022, dividido em partes iguais entre duas ações selecionadas. O simulador então mostra que, ao final de 2022, a carteira teria um retorno acumulado de, digamos, +25%, com um valor final de ~R$12.500, incluindo R$500 em dividendos. É possível visualizar a curva de crescimento do investimento e notar, por exemplo, em quais momentos a carteira teve picos ou quedas, relacionando esses movimentos aos fundamentos das empresas.

4. Comparação de estratégias (Histórico de simulações): Cada vez que uma simulação é executada, seus resultados são salvos na página de Histórico. Nesta seção, o usuário pode revisar e comparar múltiplas simulações anteriores lado a lado. A interface exibe uma tabela com as simulações registradas, incluindo métricas-chave de cada uma (período, retorno obtido, dividendos, etc.), e permite selecionar duas ou mais para gerar comparativos gráficos. Isso ajuda a avaliar qual estratégia performou melhor sob diferentes condições. Ex: Suponha que o investidor tenha rodado duas simulações: uma estratégia de Buy & Hold iniciada em 2020 e outra iniciada em 2021 com a mesma carteira. No histórico, ele pode selecionar essas duas simulações e o sistema exibirá comparativos – como uma curva de rentabilidade de cada estratégia e valores finais de patrimônio. Descobre-se, por exemplo, que o aporte feito em 2020 resultou em retorno total superior ao aporte de 2021, evidenciando o impacto do timing de entrada no mercado. Além disso, o usuário pode exportar os resultados consolidados para análise externa ou excluir simulações que não deseja mais guardar, mantendo o histórico organizado.

Cada fluxo acima representa uma etapa da análise fundamentalista interativa, permitindo ao usuário aprender fazendo. Desde a seleção criteriosa de ações até a avaliação de resultados de investimento, o simulador guia o usuário por todas as fases, fornecendo feedback imediato e visual. Isso reforça conceitos teóricos com experimentação prática, tornando o processo de aprendizado mais eficaz e intuitivo.

## Limitações e sugestões futuras

Como todo projeto acadêmico, este simulador possui algumas limitações atuais e abre oportunidades para evoluções no futuro:

Dependência de fonte de dados externa: A aplicação depende da API do brapi.dev como fonte única de dados. Alterações no formato (schema) da API ou indisponibilidade do serviço podem impactar o funcionamento do simulador. Uma melhoria futura seria integrar fontes de dados alternativas ou redundantes para aumentar a robustez.

Ausência de previsão automatizada: O simulador não possui modelos de Machine Learning ou previsão de preços integrado na versão atual. Toda a análise é retrospectiva (histórica) e baseada em dados reais passados. Para trabalhos futuros, seria interessante incorporar algoritmos de aprendizado de máquina para projetar tendências ou pontuações de empresas, embora isso deva ser feito com cautela dado o foco educacional (evitando complexidade excessiva para o usuário).

Comparação com benchmarks: Atualmente, os resultados das simulações são apresentados em valores absolutos. Uma sugestão de melhoria é incluir a comparação de desempenho da carteira com índices de referência do mercado, como o Ibovespa (principal índice de ações brasileiro) e o CDI (taxa de juros de referência). Isso permitiria ao usuário contextualizar os retornos obtidos frente ao mercado geral ou frente a investimentos de renda fixa, enriquecendo a análise.

Expansão da base de dados e funcionalidades: Futuramente, o projeto pode ser expandido para incluir novos ativos (por exemplo, FIIs – Fundos Imobiliários, referenciando o IFIX) e métricas adicionais. Também é possível adicionar módulos educacionais, como explicações teóricas para cada indicador ou quiz interativos para testar o conhecimento do usuário. Conforme apontado no TCC, integrar indicadores macroeconômicos (inflação, PIB, etc.) e permitir ajustes de cenário poderia tornar o simulador ainda mais completo.

Em suma, o Simulador de Investimentos com Análise Fundamentalista já cumpre seu papel de demonstrar a viabilidade de unir engenharia de dados, finanças e educação, porém possui espaço para evoluir. As melhorias sugeridas – como integrar benchmarks de mercado e recursos de previsão – podem tornar a ferramenta mais rica e próxima de um auxílio concreto à tomada de decisão financeira. Mesmo assim, na forma atual, o projeto entrega uma plataforma acessível e acadêmica que ajuda a compreender na prática os fundamentos das análises financeiras, atingindo os objetivos propostos no contexto do TCC.
