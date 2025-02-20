# Fluxo

### Endpoint

O fluxo é iniciado através de uma requisição HTTP, por um usuário externo, que informa uma lista de identificadores dos processos a serem analisados. Dentre os parâmetros da provocação, também é possível alternar o fluxo padrão para o fluxo *SISBAJUD*. 

Em sequência, através dos identificadores de processos informados, será adicionado a uma fila de processamento cada item dessa lista de identificadores, para que posteriormente, sejam avaliados. Um Universally Unique Identifier (UUID) é gerado e retornado para o usuário externo que provocou o Osiris, para que ele possa consultar as informações que foram geradas pelo sistema ou, caso não tenha terminado sua execução, o estado do andamento da requisição realizada.

### Download do processo

Quando a fila de processamento retira um identificador de processo, que foi informado pelo usuário externo, é iniciado o _Download do Processo_. O download é realizado através do Modelo Nacional de Interoperabilidade (MNI) e em seguida salvo em uma estrutura de diretórios. Se o processo baixado não for de execução fiscal, o fluxo é abortado para este processo antes mesmo de seus documentos e metadados serem salvos. Ou seja, o escopo do Osiris é restringido somente a processos de execução fiscal.
Os dados coletados/produzidos são armazenados em uma estrutura de pastas, com o objetivo de facilitar o mecanismo de identificação dos dados e seus metadados, como mostrado abaixo:

```

    fa8608560b7446a690d9ce0ffe930e7f
        statistics.json
        processos
        07419953420208070016
            avisos.json
            metadados.json
            documentos-avisos.json
            documentos-expedicao.json
            Documentos
```

### Download dos metados externos

Com a estrutura de pastas criada, o Osiris contata o Pje Integração a fim de traduzir os IDs dos documentos que foram mencionados nos movimentos do processo mas nao estão presentes na lista de documentos baixados, estes documentos
sao chamados de documentos de expedição. Em seguida, o Pje Integração e contatado novamente para recuperar todos os avisos gerados referentes ao processo em questão. Os dados coletados sao persistidos na estrutura de pastas criada anteriormente.

### Análise de dados

Em seguida, os documentos que possuem a data de criação mais próximas as datas de criação dos avisos baixados anteriormente, passam por um modelo de Machine Learning para que sejam classificados com base em seu conteúdo. Por fim, é gerado um HTML que sumariza as informações geradas pelo sistema. Nele é possível visualizar informações sobre os Avisos e documentos dos processos, além de alguns relacionamentos entre os documentos e seus movimentos.
Durante cada etapa do fluxo, são gerados dados estatísticos referentes ao processo e a performance do sistema, gravando informações como: quantidade de documentos do processo, tempo gasto para baixar o processo, tempo total para concluir o fluxo entre outros. Além disso, são gerados logs que permitem identificar em qual etapa do fluxo cada processo está.

### Tratamento de erros

Ao acontecer um erro durante qualquer etapa do fluxo, seja um erro interno ao Osiris ou em algum dos serviços que ele depende (MNI, PJE Integração), o processo é colocado em uma fila de erros.
Cada processo que entra na fila de erros recebe uma penalidade baseada na quantidade de vezes que ele entrou nessa fila, de modo que os processos que tiveram mais falhas sucessivas recebam uma penalidade maior do que os processos com menos falhas.
Essa fila de erros é implementada através de uma fila de prioridades, e a penalidade associada ao processo representa a chave de ordenação dessa fila. Deste modo, o processo com a menor penalidade irá ser desenfileirado primeiro. A penalidade do processo é utilizada para calcular quanto tempo um processo deverá ficar esperando na fila de erros até que possa voltar para a fila de processamento. Evitando assim, que os processos que falharem sobrecarreguem o sistema.
Quando um processo que já cumpriu a sua penalidade sai da fila de erros ele é recolocado na fila de processamento para que possa seguir o fluxo inteiro novamente. Esse ciclo se repete até que o processo conclua todas as etapas do fluxo com sucesso.

## Fluxo de execução dinâmico

Os submódulos do Osiris são executados através de um **Fluxo Dinâmico**, onde é possível adicionar novas funcionalidades ao fluxo de processamento de forma mais fácil e configurável. Os atuais fluxos de execução do Osiris é o fluxo `default` e o `SISBAJUD`.

Para adicionar um fluxo, necessário seguir alguns passos: 

1. Adicionar em `FlagsSubmodulesOrder` no arquivo `src/endpoints/process/utils/submodules.py`.

2. Adicionar/alterar o `process_router` do endpoint de provocação, em `src/application/controllers/process_controller.py`.

3. Adicionar/alterar em `RequestConfig` em `src/application/schemas/request_config.py`.

## Submódulos

Para adicionar uma nova funcionalidade utilizando o **Fluxo Dinâmico** é necessário criar um script Python no diretório `src/submodules`, esse script deve possuir uma função assíncrona chamada **run** que receba os seguintes parâmetros:

- request_uuid: Uma string representando o ID da requisição.
- process_id: Uma string representando o ID do processo a ser processado.
- ip: Uma string representando o IP do usuário que está fazendo a requisição (Usado principalmente em logs)

Os argumentos para esta função serão passados pelo nome, ou seja, caso queira ignorar algum parâmetro pode se utilizar a sintaxe de _kwargs_. Exemplo de como a função será chamada:

```python
await run(request_uuid='UUID da requisição', process_id='ID do processo', ip='IP do cliente')
```

Com o script criado, é necessário configurar em qual fluxo e em qual momento ele irá ser executado. Para isso deve-se utilizar o arquivo `src/submodules/execution_order.json`. Este JSON possui os seguintes campos:

- *[chave com o nome específico do fluxo]*
    - on_process_success: Scripts a serem executados quando um processo é finalizado sem erros.
    - on_request_completed: Scripts que são executados quando todos os processo de uma requisição são finalizados, independente de terem sido finalizados com sucesso ou não.

Os scripts serão executados na ordem que foi definida no arquivo `src/submodules/execution_order.json`. Caso queira executar mais de um script de forma concorrente basta separá-los por vírgula. Exemplo de configuração válido:

```json
{
  "fluxo1": {
    "on_process_success": [
        "processamento_paralelo1,processamento_paralelo_2",
        "depois_do_processamento_paralelo"
    ],
    "on_request_completed": [
        "processamento_fixo_1",
        "processamento_fixo_2"
    ]
  },
  "fluxo2": {
    "on_process_success": [
        "processamento_diferente"
    ],
    "on_request_completed": [
        "processamento_fixo_diferente"
    ]
  }
}
```

### Visualizador

_Visualizador_ é o submódulo responsável por transformar os metadados e informações de uma requisição em uma página `HTML`.


!!! info ""
    === "seção 1"
        !!! info ""
            Nesta sessão, vamos encontrar uma versão para cada componente do Osíris na qual aquela requisição foi executada.
        ![Image title](../_media/exemplo_da_secao_1.png){ align=left }
    === "seção 2"
        !!! info ""
            Nesta sessão, vamos encontrar informações sobre os avisos referentes a cada processo. Além disso, também são apresentadas informações geradas pelo Osíris (.
        ![Image title](../_media/exemplo_da_secao_2.png){ align=left }
    === "seção 2.1.1"
        !!! info ""
            Em requisições que incluem o módulo do _SISBAJUS_, podemos ver a minuta que será enviada no `send_avisos` e um resumo das CDAs
        ![Image title](../_media/exemplo_minuta_secao_2.png){ align=left }
    === "seção 2.2"
        !!! info ""
            Nesta sessão, vamos encontrar o resulmo de todas as CDA conhecidos no processo, esse informações os obtidade em `documentos-cdas.json` com o respectivo documento que embasa essas informações. Note que algumas CDAs são relatadas em mais de um documento.
        ![Image title](../_media/exemplo_CDA_secao_2_2.png){ align=left }
    === "seção 2.3"
        !!! info ""
            Nesta sessão, vamos encontrar a lista de movimentos do processo de forma cronológica.
        ![Image title](../_media/exemplo_movimentos_secao_2_3.png){ align=left }
    === "seção 2.4"
        !!! info ""
            Nesta sessão, vamos encontrar a lista de todos os documentos do processo em ordem cronológica.
        ![Image title](../_media/exemplo_documentos_2_4.png){ align=left }
    === "seção 2.4.1"
        !!! info ""
            Nesta sessão, vamos encontrar uma representação em grafo das duas tabelas mostradas anteriormente (documentos e movimentos). Note que existe uma ordem cronológica (de cima para baixo).
        ![Image title](../_media/exemplo_grafo_2_4_1.png){ align=left }

#### Como obter o visualizador

Existem duas formas de recuperar o visualizador:

* **Utilizando o endpoint `/resultados/visualizador/{request_uuid}`**  
   Esse método retorna uma página em **HTML**, oferecendo uma versão simplificada do visualizador.  

    !!! warning "Atenção"
        Nessa versão, não será possível acessar os documentos referenciados pelo visualizador.

   ---

2. **Utilizando o endpoint `/resultados/dados/{request_uuid}`**  
   Esse endpoint não foi projetado exclusivamente para o visualizador, mas oferece acesso a todos os artefatos gerados por uma requisição do Osires.  
   Se você abrir o HTML do visualizador nessa pasta, terá acesso à versão completa, onde os links para os documentos estarão funcionando corretamente.

   ---


!!! tip "Nota"
    A escolha entre as duas opções depende do nível de acesso necessário. O primeiro método é ideal para uma visualização simplificada, enquanto o segundo garante acesso completo aos documentos vinculados.

Para mais detalhes sobre a implementação, acesse o [repositório oficial](https://gitlab.com/gpam/osiris/prototypes/osiris-visualizador).

### Pré-Processador

O _pré-processador_ é um submódulo responsável por reunir informações obtidas no submódulo do OCR com informações extraídas do `m̀etadados.json` em um arquivo _parquet_ que será utilizado pelo submódulo do agente.

O resultado do processamento será um arquivo Parquet chamado `doc_processos_avisos_rotulados.parquet`, que será criado na pasta do processo correspondente.

Uma das funcionalidades mais importantes do aplicativo é a classificação da origem do documento (exequente, executado, tribunal). Esse fluxo ocorre individualmente para cada documento de um processo.

``` mermaid
graph LR
    A([Início da classificação<br>de origem do documento]) --> B{O usuário que juntou<br>o documento aparece<br>em alguma lista de usuários?}
    B --> |Sim| I[A origem do<br>documento é do órgão<br>em que ele foi encontrado]
    B --> |Não| G[Classificação<br>utilizando deep learning]
    G --> E([Fim da classificação<br>de origem])
    I --> E
```
Ao final do fluxo do Pré-Processador é gerado um arquivo .parquet. Segue uma breve descrição das coluas presentes no arquivo:

| Coluna  | Descrição  |
|-----------|-----------|
| num_processo | numero do processo |
| id_doc | identificador do documento | 
| tipo_id_usuario | tipo de identificador do usuário, usuário = Autor do documento |
| id_usuario | identificador do usuário responsavel pelo cadastro |
| nome_usuario | nome do usuário responsavel pelo cadastro |
| origem_doc | orgão que emitiu o documento (PG,EX)  |
| datahora | data e hora em que foi cadastrado  |
| ids_doc_vinc | identificador dos documentos vinculados  |
| num_doc_vinc | quantidade de documentos vinculados  |
| tipo_doc | Tipo de elemento destinado à transferência ou à viabilização de transferência de documento processual.  |
| mimetype | formato do documento (text/html', 'application/pdf', 'image/jpeg', 'video/mp4','image/png', 'audio/mp4', 'video/quicktime', 'audio/ogg')  |
| descricao | Expliação do que se trata no documento  |
| process_number | numero do processo |
| txt | uma string contendo o conteudo das paginas do doc |
| num_pags | quantidade de paginas |
| id_root_doc | identificador do documento de origem  |

Para mais detalhes sobre a implementação, acesse o [repositório oficial](https://gitlab.com/gpam/osiris/prototypes/preprocessador-osiris).

### Agente

O _Agente_ é o submódulo responsável pelo processamento automatizado de documentos jurídicos. Ele foi projetado para interpretar e classificar textos com o auxílio de aprendizado de máquina e técnicas de NLP (Processamento de Linguagem Natural). Seu propósito é automatizar a análise de documentos jurídicos, categorizá-los com precisão e gerenciar seu estado em diferentes fases de um processo, tornando o trabalho mais eficiente e reduzindo erros manuais.

#### Estrutura do Sistema e Fluxo de Execução
O fluxo de execução do agente começa com a leitura dos documentos a partir de um arquivo Parquet, carregando os dados em um DataFrame do Pandas. O Parquet deve ser previamente gerado por um preprocessador e armazena dados com estrutura definida, como em `doc_processos_avisos_rotulados.parquet`. Cada documento no DataFrame é processado de forma sequencial, e o histórico de cada processamento é armazenado para referência futura em uma estrutura de pastas organizada.

#### Gerenciamento de Cache
Para otimizar o desempenho, o agente usa a classe `FileCache`, que armazena respostas frequentes em um arquivo JSON configurável para evitar reexecuções de chamadas ao modelo de linguagem (LLM). Esse cache é gerado por uma chave única (hash) baseada nos parâmetros da função, garantindo que cada resultado seja específico para uma entrada. O arquivo de cache tem caminho configurável e pode requerer varreduras periódicas para manter o tamanho gerenciável, pois armazena as respostas acumuladas sem remoção automática.

No código `agente.py`, o caminho do arquivo de cache é configurável por meio do parâmetro `chat_cache_path`. Esse parâmetro é passado para a classe `FileCache`, que cria e gerencia o arquivo de cache. Caso o caminho não seja especificado ao executar o agente, o arquivo de cache padrão é criado com o nome `chat_cache.json` no diretório onde o script é executado.

#### Comparação e Consulta de Embeddings
Para identificar o tipo de conteúdo jurídico, o agente carrega embeddings de documentos anteriores e compara esses embeddings com o conteúdo atual. A classe `EmbeddingManager` é responsável por carregar esses embeddings do Parquet e realizar cálculos de similaridade. Caso o novo documento tenha uma correspondência acima de um limite de similaridade, ele é classificado com base no rótulo do embedding correspondente.

#### Máquina de Estados e Transições
O coração do agente é a máquina de estados `Processo`, configurada com base em transições definidas em um arquivo JSON. Esse mecanismo permite que o agente transite por estados jurídicos (como "ajuizado", "suspenso", "arquivado") de acordo com o gatilho identificado no documento. Para cada estado, o agente tem ações e transições possíveis, permitindo que ele gerencie a complexidade dos estados de um processo jurídico.

A máquina de estados analisa o conteúdo dos documentos em busca de padrões com o uso de expressões regulares e embeddings. Ela utiliza essas informações para determinar qual gatilho disparar, o que altera o estado do processo conforme necessário. Quando um gatilho não é identificado por regex ou embeddings, o agente recorre ao modelo de linguagem para classificar o documento.

#### Interação com Modelos de Linguagem (LLM)
Para documentos cuja categorização não é clara com métodos tradicionais, o agente faz uso de um modelo de linguagem (LLM) para resumir o conteúdo e encontrar a melhor classificação. A função `query_llm` envia o conteúdo ao modelo e retorna uma resposta categorizada. Atualmente, a URL do LLM pode ser usada sem o sufixo `/chat`. Esse recurso é usado principalmente para consultas complexas ou para determinar o tipo de documento em casos menos padronizados.

#### Utilização do LLM

Para a utilização do modelo ser possível, é necessário a configuração do URL e o modelo a ser utilizado no arquivo de configuração `settings.json`. 

```json
{
  "llm_url_prod": "http://127.0.0.1:11434/api/chat",
  "llm_model_prod": "llama3",
  "llm_url_dev": "http://127.0.0.1:11434/api/chat",
  "llm_model_dev": "llama3"
}
```

Caso aplicável, é possível a configuração de credenciais para uso do LLM a partir do nome de usuário e senha (HTTP Basic Auth) no arquivo de configuração `settings.json`.

```json
{
  "llm_user_dev": "user",
  "llm_password_dev": "password",
  "llm_user_prod": "user",
  "llm_password_prod": "password",
}
```

Caso aplicável, é possível a configuração de credenciais para o uso LLM a partir do uso de uma chave de autenticação no arquivo de configuração `settings.json`.

```json
{
  "llm_apikey_dev": "apikey",
  "llm_apikey_prod": "apikey",
}
```

#### Geração de Histórico e Relatórios
Após o processamento de cada documento, o agente gera um histórico detalhado, incluindo informações como o gatilho detectado, método de detecção (regex, embedding ou LLM), estado inicial e estado final do processo. Esse histórico é armazenado na estrutura de pastas do processo e pode ser visualizado em formato de tabela para fácil acompanhamento e auditoria.

#### Exploração dos Dados Estáticos (ver.0.5.2)

O conjunto de dados fornecido representa um fluxo de transições de estado dentro de um sistema, onde cada linha descreve a mudança de um estado para outro com base em uma determinada ação (ato). Para a extração das fases, estados e atos, foi realizada uma análise das colunas presentes na tabela. As fases foram identificadas como os estágios ou etapas principais do processo, como "leave_steady_phase", "update_phase_ajuizado", e outras fases de transição como "suspenso" ou "em_citacao".

Já os estados representam as diferentes condições de um processo dentro do ciclo, por exemplo, "aguardando_espolio_emenda", "aguardando_indicacao_bens", "aguardando_endereco", entre outros, que indicam o momento específico em que o processo se encontra. As ações (ou atos) são os eventos que provocam a transição entre os estados, como "peticao_ajuizamento", "mandado_citacao", "despacho_intimar_exequente_alegacao_parcelamento", e assim por diante.

Para documentar as fases, estados e atos, foi realizada uma inspeção detalhada das colunas correspondentes, selecionando as entradas únicas para cada categoria. O resultado final foi uma tabela que lista as diferentes fases, estados e atos que fazem parte do ciclo de um processo. Essas transições e ações refletem a evolução de um processo judicial ou administrativo, conforme o fluxo de trabalho especificado. 

#### Dados Estáticos (ver.0.5.2)

Segue as tabelas contendo Atos, Estados e Fases:

  <details>
      <summary style="font-size: 1.3em;">Lista de Atos</summary>
      <div style="display: flex; justify-content: center; width: 100%;">
        <table style="width: 100%; border-collapse: collapse; table-layout: fixed; text-align: left;">
          <thead>
            <tr>
              <th style="border: 1px solid #ddd; padding: 8px; background-color: #f2f2f2; text-align: center;">Atos</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td style="border: 1px solid #ddd; padding: 8px;">AR_Correios</td>
            </tr>
            <tr>
              <td style="border: 1px solid #ddd; padding: 8px;">AR_ausente</td>
            </tr>
            <tr>
              <td style="border: 1px solid #ddd; padding: 8px;">AR_ausente_tres_vezes</td>
            </tr>
            <tr>
              <td style="border: 1px solid #ddd; padding: 8px;">AR_cumprido</td>
            </tr>
            <tr>
              <td style="border: 1px solid #ddd; padding: 8px;">AR_desconhecido</td>
            </tr>
            <tr>
              <td style="border: 1px solid #ddd; padding: 8px;">AR_endereco_incorreto</td>
            </tr>
            <tr>
              <td style="border: 1px solid #ddd; padding: 8px;">AR_endereco_insuficiente</td>
            </tr>
            <tr>
              <td style="border: 1px solid #ddd; padding: 8px;">AR_falecido</td>
            </tr>
            <tr>
              <td style="border: 1px solid #ddd; padding: 8px;">AR_mudou</td>
            </tr>
            <tr>
              <td style="border: 1px solid #ddd; padding: 8px;">AR_nao_existe_numero</td>
            </tr>
            <tr>
              <td style="border: 1px solid #ddd; padding: 8px;">GRU</td>
            </tr>
            <tr>
              <td style="border: 1px solid #ddd; padding: 8px;">SISBAJUD_infrutifero</td>
            </tr>
            <tr>
              <td style="border: 1px solid #ddd; padding: 8px;">alvara_levantamento</td>
            </tr>
            <tr>
              <td style="border: 1px solid #ddd; padding: 8px;">arquivar_processo</td>
            </tr>
            <tr>
              <td style="border: 1px solid #ddd; padding: 8px;">ata_audiencia_conciliacao</td>
            </tr>
            <tr>
              <td style="border: 1px solid #ddd; padding: 8px;">ata_reuniao</td>
            </tr>
            <tr>
              <td style="border: 1px solid #ddd; padding: 8px;">certidao_OJ_desconhecido</td>
            </tr>
            <tr>
              <td style="border: 1px solid #ddd; padding: 8px;">certidao_OJ_mudou</td>
            </tr>
            <tr>
              <td style="border: 1px solid #ddd; padding: 8px;">certidao_OJ_nao_reside_local</td>
            </tr>
            <tr>
              <td style="border: 1px solid #ddd; padding: 8px;">certidao_OJ_redistribuicao</td>
            </tr>
            <tr>
              <td style="border: 1px solid #ddd; padding: 8px;">certidao_SEDEX_cumprido</td>
            </tr>
            <tr>
              <td style="border: 1px solid #ddd; padding: 8px;">certidao_SISBAJUD_parcialmente_frutifera</td>
            </tr>
            <tr>
              <td style="border: 1px solid #ddd; padding: 8px;">certidao_SISBAJUD_positivo</td>
            </tr>
            <tr>
              <td style="border: 1px solid #ddd; padding: 8px;">certidao_adiamento_audiencia</td>
            </tr>
            <tr>
              <td style="border: 1px solid #ddd; padding: 8px;">certidao_alvara_disponivel</td>
            </tr>
            <tr>
              <td style="border: 1px solid #ddd; padding: 8px;">certidao_alvara_expedido</td>
            </tr>
            <tr>
              <td style="border: 1px solid #ddd; padding: 8px;">certidao_apto_arquivamento</td>
            </tr>
            <tr>
              <td style="border: 1px solid #ddd; padding: 8px;">certidao_bloqueio_SISBAJUD</td>
            </tr>
            <tr>
              <td style="border: 1px solid #ddd; padding: 8px;">certidao_cadastro_advogado</td>
            </tr>
            <tr>
              <td style="border: 1px solid #ddd; padding: 8px;">certidao_cancelamento_audiencia</td>
            </tr>
            <tr>
              <td style="border: 1px solid #ddd; padding: 8px;">certidao_consulta_BANDI</td>
            </tr>
            <tr>
              <td style="border: 1px solid #ddd; padding: 8px;">certidao_consulta_valor_debito_consolidado</td>
            </tr>
            <tr>
              <td style="border: 1px solid #ddd; padding: 8px;">certidao_decorrido_prazo_suspensao_12_meses_parcelamento</td>
            </tr>
            <tr>
              <td style="border: 1px solid #ddd; padding: 8px;">certidao_desentranhamento</td>
            </tr>
            <tr>
              <td style="border: 1px solid #ddd; padding: 8px;">certidao_disponibiliza_DJe</td>
            </tr>
            <tr>
              <td style="border: 1px solid #ddd; padding: 8px;">certidao_diversa</td>
            </tr>
            <tr>
              <td style="border: 1px solid #ddd; padding: 8px;">certidao_encerrado_prazo_verificacao_conformidade_processo_eletronico</td>
            </tr>
            <tr>
              <td style="border: 1px solid #ddd; padding: 8px;">certidao_encerramento_expediente</td>
            </tr>
            <tr>
              <td style="border: 1px solid #ddd; padding: 8px;">certidao_envio_AR</td>
            </tr>
            <tr>
              <td style="border: 1px solid #ddd; padding: 8px;">certidao_exequente_ciencia_infojud_andamento_feito</td>
            </tr>
            <tr>
              <td style="border: 1px solid #ddd; padding: 8px;">certidao_expedicao_alvara</td>
            </tr>
            <tr>
              <td style="border: 1px solid #ddd; padding: 8px;">certidao_indisponibilidade_de_bens</td>
            </tr>
            <tr>
              <td style="border: 1px solid #ddd; padding: 8px;">certidao_indisponibilidade_frustrada_de_bens</td>
            </tr>
            <tr>
              <td style="border: 1px solid #ddd; padding: 8px;">certidao_inspecao_anual</td>
            </tr>
            <tr>
              <td style="border: 1px solid #ddd; padding: 8px;">certidao_juntada_rastreio_AR</td>
            </tr>
            <tr>
              <td style="border: 1px solid #ddd; padding: 8px;">certidao_liquidacao_parcelamento</td>
            </tr>
            <tr>
              <td style="border: 1px solid #ddd; padding: 8px;">certidao_migracao</td>
            </tr>
            <tr>
              <td style="border: 1px solid #ddd; padding: 8px;">certidao_negativa_onus</td>
            </tr>
            <tr>
              <td style="border: 1px solid #ddd; padding: 8px;">certidao_obito</td>
            </tr>
            <tr>
              <td style="border: 1px solid #ddd; padding: 8px;">certidao_parcelamento_administrativo</td>
            </tr>
            <tr>
              <td style="border: 1px solid #ddd; padding: 8px;">certidao_parte_executada_inerte</td>
            </tr>
            <tr>
              <td style="border: 1px solid #ddd; padding: 8px;">certidao_penhora_RENAJUD_efetivada</td>
            </tr>
            <tr>
              <td style="border: 1px solid #ddd; padding: 8px;">certidao_positiva_debito</td>
            </tr>
            <tr>
              <td style="border: 1px solid #ddd; padding: 8px;">certidao_positiva_distribuicao</td>
            </tr>
            <tr>
              <td style="border: 1px solid #ddd; padding: 8px;">certidao_positiva_efeito_negativa</td>
            </tr>
            <tr>
              <td style="border: 1px solid #ddd; padding: 8px;">certidao_prazo_decorrido_exequente</td>
            </tr>
            <tr>
              <td style="border: 1px solid #ddd; padding: 8px;">certidao_redistribuicao_migrado</td>
            </tr>
            <tr>
              <td style="border: 1px solid #ddd; padding: 8px;">certidao_solicitacao_sisbajud</td>
            </tr>
            <tr>
              <td style="border: 1px solid #ddd; padding: 8px;">certidao_transcorrido_prazo_suspensao</td>
            </tr>
            <tr>
              <td style="border: 1px solid #ddd; padding: 8px;">certidao_transferencia_alvara_levantamento</td>
            </tr>
            <tr>
              <td style="border: 1px solid #ddd; padding: 8px;">certidao_transito_julgado</td>
            </tr>
            <tr>
              <td style="border: 1px solid #ddd; padding: 8px;">certidao_vista_defensoria_publica</td>
            </tr>
            <tr>
              <td style="border: 1px solid #ddd; padding: 8px;">comprovante_pagamento</td>
            </tr>
            <tr>
              <td style="border: 1px solid #ddd; padding: 8px;">comprovante_situacao_cadastral</td>
            </tr>
            <tr>
              <td style="border: 1px solid #ddd; padding: 8px;">comunicado_anexo</td>
            </tr>
            <tr>
              <td style="border: 1px solid #ddd; padding: 8px;">consulta_CNPJ_receita</td>
            </tr>
            <tr>
              <td style="border: 1px solid #ddd; padding: 8px;">consulta_CPF_base_nacional</td>
            </tr>
            <tr>
              <td style="border: 1px solid #ddd; padding: 8px;">consulta_RENAJUD</td>
            </tr>
            <tr>
              <td style="border: 1px solid #ddd; padding: 8px;">consulta_SITAF_AJUIZAMENTO</td>
            </tr>
            <tr>
              <td style="border: 1px solid #ddd; padding: 8px;">consulta_SITAF_DIVIDA_ATIVA</td>
            </tr>
            <tr>
              <td style="border: 1px solid #ddd; padding: 8px;">consulta_SITAF_ENDERECO</td>
            </tr>
            <tr>
              <td style="border: 1px solid #ddd; padding: 8px;">consulta_SITAF_FAC2</td>
            </tr>
            <tr>
              <td style="border: 1px solid #ddd; padding: 8px;">consulta_SITAF_IMOVEL</td>
            </tr>
            <tr>
              <td style="border: 1px solid #ddd; padding: 8px;">consulta_SITAF_PARCELAMENTO</td>
            </tr>
            <tr>
              <td style="border: 1px solid #ddd; padding: 8px;">consulta_SITAF_PF_PJ</td>
            </tr>
            <tr>
              <td style="border: 1px solid #ddd; padding: 8px;">consulta_SITAF_VALOR</td>
            </tr>
            <tr>
              <td style="border: 1px solid #ddd; padding: 8px;">consulta_SITAF_VEICULO</td>
            </tr>
            <tr>
              <td style="border: 1px solid #ddd; padding: 8px;">consulta_binco</td>
            </tr>
            <tr>
              <td style="border: 1px solid #ddd; padding: 8px;">consulta_cartorios</td>
            </tr>
            <tr>
              <td style="border: 1px solid #ddd; padding: 8px;">consulta_ficha_cadastral_junta_comercial</td>
            </tr>
            <tr>
              <td style="border: 1px solid #ddd; padding: 8px;">consulta_infoseg</td>
            </tr>
            <tr>
              <td style="border: 1px solid #ddd; padding: 8px;">consulta_veiculo</td>
            </tr>
            <tr>
              <td style="border: 1px solid #ddd; padding: 8px;">decisao_acolhe_embargos_de_declaracao_rejeita_pedido</td>
            </tr>
            <tr>
              <td style="border: 1px solid #ddd; padding: 8px;">decisao_acolher_embargos_declaracao_parte_autora</td>
            </tr>
            <tr>
              <td style="border: 1px solid #ddd; padding: 8px;">decisao_acolher_excecao_pre_exec</td>
            </tr>
            <tr>
              <td style="border: 1px solid #ddd; padding: 8px;">decisao_arquiva_provimento_13</td>
            </tr>
            <tr>
              <td style="border: 1px solid #ddd; padding: 8px;">decisao_declinacao_compentencia</td>
            </tr>
            <tr>
              <td style="border: 1px solid #ddd; padding: 8px;">decisao_defere_penhora_RENAJUD</td>
            </tr>
            <tr>
              <td style="border: 1px solid #ddd; padding: 8px;">decisao_extincao_desistencia_exequente</td>
            </tr>
            <tr>
              <td style="border: 1px solid #ddd; padding: 8px;">decisao_indefere_penhora_RENAJUD</td>
            </tr>
            <tr>
              <td style="border: 1px solid #ddd; padding: 8px;">decisao_indefere_penhora_citacao_frustrada</td>
            </tr>
            <tr>
              <td style="border: 1px solid #ddd; padding: 8px;">decisao_intima_exequente_prescricao</td>
            </tr>
            <tr>
              <td style="border: 1px solid #ddd; padding: 8px;">decisao_intimar_exequente_certidao_obito</td>
            </tr>
            <tr>
              <td style="border: 1px solid #ddd; padding: 8px;">decisao_intimar_exequente_indicar_administrador_judicia_empresa</td>
            </tr>
            <tr>
              <td style="border: 1px solid #ddd; padding: 8px;">decisao_intimar_exequente_indicar_bens</td>
            </tr>
            <tr>
              <td style="border: 1px solid #ddd; padding: 8px;">decisao_intimar_exequente_indicar_valor_penhora</td>
            </tr>
            <tr>
              <td style="border: 1px solid #ddd; padding: 8px;">decisao_penhora_seg_indica_bens</td>
            </tr>
            <tr>
              <td style="border: 1px solid #ddd; padding: 8px;">decisao_rejeitar_embargos_parte_autora</td>
            </tr>
            <tr>
              <td style="border: 1px solid #ddd; padding: 8px;">decisao_rejeitar_excecao_pre_exec</td>
            </tr>
            <tr>
              <td style="border: 1px solid #ddd; padding: 8px;">decisao_rejeitar_excecao_pre_exec_com_penhora</td>
            </tr>
            <tr>
              <td style="border: 1px solid #ddd; padding: 8px;">decisao_rejeitar_excecao_pre_exec_indicar_bens</td>
            </tr>
            <tr>
              <td style="border: 1px solid #ddd; padding: 8px;">decisao_suspensao_12_meses_parcelamento</td>
            </tr>
            <tr>
              <td style="border: 1px solid #ddd; padding: 8px;">decisao_suspensao_1ano_art40</td>
            </tr>
            <tr>
              <td style="border: 1px solid #ddd; padding: 8px;">decisao_suspensao_90_dias</td>
            </tr>
            <tr>
              <td style="border: 1px solid #ddd; padding: 8px;">decisao_suspensao_em_virtude_embargos_execucao</td>
            </tr>
            <tr>
              <td style="border: 1px solid #ddd; padding: 8px;">declaracao_hipossuficiencia</td>
            </tr>
            <tr>
              <td style="border: 1px solid #ddd; padding: 8px;">defere_INFOJUD</td>
            </tr>
            <tr>
              <td style="border: 1px solid #ddd; padding: 8px;">defere_INFOJUD_registro_data_suspensao_art40</td>
            </tr>
            <tr>
              <td style="border: 1px solid #ddd; padding: 8px;">despacho_citar_executado</td>
            </tr>
            <tr>
              <td style="border: 1px solid #ddd; padding: 8px;">despacho_diligencia_OJ</td>
            </tr>
            <tr>
              <td style="border: 1px solid #ddd; padding: 8px;">despacho_intima_exequente_embargos_declaracao</td>
            </tr>
            <tr>
              <td style="border: 1px solid #ddd; padding: 8px;">despacho_intima_valor_inferior_LC</td>
            </tr>
            <tr>
              <td style="border: 1px solid #ddd; padding: 8px;">despacho_intimar_exequente_alegacao_parcelamento</td>
            </tr>
            <tr>
              <td style="border: 1px solid #ddd; padding: 8px;">despacho_intimar_exequente_alegacao_quitacao</td>
            </tr>
            <tr>
              <td style="border: 1px solid #ddd; padding: 8px;">despacho_intimar_exequente_sobrestamento</td>
            </tr>
            <tr>
              <td style="border: 1px solid #ddd; padding: 8px;">despacho_intimar_manifestacao_conciliacao</td>
            </tr>
            <tr>
              <td style="border: 1px solid #ddd; padding: 8px;">despacho_juntar_AR</td>
            </tr>
            <tr>
              <td style="border: 1px solid #ddd; padding: 8px;">despacho_nada_a_prover</td>
            </tr>
            <tr>
              <td style="border: 1px solid #ddd; padding: 8px;">despacho_retorno_juizo_origem</td>
            </tr>
            <tr>
              <td style="border: 1px solid #ddd; padding: 8px;">determina_citacao_edital</td>
            </tr>
            <tr>
              <td style="border: 1px solid #ddd; padding: 8px;">determina_indisponibilidade_de_bens_suspensao_1ano_art40</td>
            </tr>
            <tr>
              <td style="border: 1px solid #ddd; padding: 8px;">determina_indisponibilidade_registro_data_suspensao_art40</td>
            </tr>
            <tr>
              <td style="border: 1px solid #ddd; padding: 8px;">edital_citacao</td>
            </tr>
            <tr>
              <td style="border: 1px solid #ddd; padding: 8px;">extrato_previdenciario</td>
            </tr>
            <tr>
              <td style="border: 1px solid #ddd; padding: 8px;">guia_deposito_judicial</td>
            </tr>
            <tr>
              <td style="border: 1px solid #ddd; padding: 8px;">impressao_IR</td>
            </tr>
            <tr>
              <td style="border: 1px solid #ddd; padding: 8px;">impugnacao_embargos_declaracao_executado</td>
            </tr>
            <tr>
              <td style="border: 1px solid #ddd; padding: 8px;">impugnacao_excecao_pre_exec</td>
            </tr>
            <tr>
              <td style="border: 1px solid #ddd; padding: 8px;">indefere_INFOJUD</td>
            </tr>
            <tr>
              <td style="border: 1px solid #ddd; padding: 8px;">indefere_citadao_OJ_endereco</td>
            </tr>
            <tr>
              <td style="border: 1px solid #ddd; padding: 8px;">intima_executado_pagamento_sinal</td>
            </tr>
            <tr>
              <td style="border: 1px solid #ddd; padding: 8px;">intima_exequente_andamento_feito</td>
            </tr>
            <tr>
              <td style="border: 1px solid #ddd; padding: 8px;">intima_exequente_detalhe_veiculo</td>
            </tr>
            <tr>
              <td style="border: 1px solid #ddd; padding: 8px;">intima_exequente_excecao_pre_executividade</td>
            </tr>
            <tr>
              <td style="border: 1px solid #ddd; padding: 8px;">intima_manifestacao_retificar_polo</td>
            </tr>
            <tr>
              <td style="border: 1px solid #ddd; padding: 8px;">intima_manifestar_parcelamento</td>
            </tr>
            <tr>
              <td style="border: 1px solid #ddd; padding: 8px;">intimacao_executado_audiencia_conciliacao</td>
            </tr>
            <tr>
              <td style="border: 1px solid #ddd; padding: 8px;">intimacao_executado_penhora</td>
            </tr>
            <tr>
              <td style="border: 1px solid #ddd; padding: 8px;">intimacao_exequente_audiencia_conciliacao</td>
            </tr>
            <tr>
              <td style="border: 1px solid #ddd; padding: 8px;">intimacao_indicar_bens_penhora</td>
            </tr>
            <tr>
              <td style="border: 1px solid #ddd; padding: 8px;">intimacao_indicar_endereco</td>
            </tr>
            <tr>
              <td style="border: 1px solid #ddd; padding: 8px;">intimacao_parcelamento_quitacao</td>
            </tr>
            <tr>
              <td style="border: 1px solid #ddd; padding: 8px;">intimacao_terceiro_dados_alienacao_fiduciaria</td>
            </tr>
            <tr>
              <td style="border: 1px solid #ddd; padding: 8px;">intimacao_transferencia_bancaria</td>
            </tr>
            <tr>
              <td style="border: 1px solid #ddd; padding: 8px;">inventario</td>
            </tr>
            <tr>
              <td style="border: 1px solid #ddd; padding: 8px;">junta_ata_audiencia</td>
            </tr>
            <tr>
              <td style="border: 1px solid #ddd; padding: 8px;">mandado_citacao</td>
            </tr>
            <tr>
              <td style="border: 1px solid #ddd; padding: 8px;">mandado_citacao_com_audiencia</td>
            </tr>
            <tr>
              <td style="border: 1px solid #ddd; padding: 8px;">mandado_intimacao_penhora</td>
            </tr>
            <tr>
              <td style="border: 1px solid #ddd; padding: 8px;">notifica_INFOJUD_negativo</td>
            </tr>
            <tr>
              <td style="border: 1px solid #ddd; padding: 8px;">notifica_decisao_indisponibilidade_de_bens_suspensao_1ano_art40</td>
            </tr>
            <tr>
              <td style="border: 1px solid #ddd; padding: 8px;">oficio_INSS_obito</td>
            </tr>
            <tr>
              <td style="border: 1px solid #ddd; padding: 8px;">peca_doc_diverso</td>
            </tr>
            <tr>
              <td style="border: 1px solid #ddd; padding: 8px;">pesquisa_de_imoveis</td>
            </tr>
            <tr>
              <td style="border: 1px solid #ddd; padding: 8px;">peticao_INFOJUD</td>
            </tr>
            <tr>
              <td style="border: 1px solid #ddd; padding: 8px;">peticao_RENAJUD</td>
            </tr>
            <tr>
              <td style="border: 1px solid #ddd; padding: 8px;">peticao_SISBAJUD</td>
            </tr>
            <tr>
              <td style="border: 1px solid #ddd; padding: 8px;">peticao_abatimento_divida</td>
            </tr>
            <tr>
              <td style="border: 1px solid #ddd; padding: 8px;">peticao_agravo_instrumento</td>
            </tr>
            <tr>
              <td style="border: 1px solid #ddd; padding: 8px;">peticao_ajuizamento</td>
            </tr>
            <tr>
              <td style="border: 1px solid #ddd; padding: 8px;">peticao_andamento_apesar_valor</td>
            </tr>
            <tr>
              <td style="border: 1px solid #ddd; padding: 8px;">peticao_ciencia</td>
            </tr>
            <tr>
              <td style="border: 1px solid #ddd; padding: 8px;">peticao_dados_parcelamento_suspensao</td>
            </tr>
            <tr>
              <td style="border: 1px solid #ddd; padding: 8px;">peticao_debito_supera_valor_minimo_provimento_13</td>
            </tr>
            <tr>
              <td style="border: 1px solid #ddd; padding: 8px;">peticao_declinacao_competencia</td>
            </tr>
            <tr>
              <td style="border: 1px solid #ddd; padding: 8px;">peticao_desistencia_valor_inferior</td>
            </tr>
            <tr>
              <td style="border: 1px solid #ddd; padding: 8px;">peticao_diligencia_OJ_endereco</td>
            </tr>
            <tr>
              <td style="border: 1px solid #ddd; padding: 8px;">peticao_embargos_declaracao_executado</td>
            </tr>
            <tr>
              <td style="border: 1px solid #ddd; padding: 8px;">peticao_embargos_declaracao_exequente</td>
            </tr>
            <tr>
              <td style="border: 1px solid #ddd; padding: 8px;">peticao_excecao_pre_executividade</td>
            </tr>
            <tr>
              <td style="border: 1px solid #ddd; padding: 8px;">peticao_executado_comprovar_parcelamento</td>
            </tr>
            <tr>
              <td style="border: 1px solid #ddd; padding: 8px;">peticao_executado_disponibilizacao_ato</td>
            </tr>
            <tr>
              <td style="border: 1px solid #ddd; padding: 8px;">peticao_executado_extincao_pagamento</td>
            </tr>
            <tr>
              <td style="border: 1px solid #ddd; padding: 8px;">peticao_executado_indeferir_sobrestamento</td>
            </tr>
            <tr>
              <td style="border: 1px solid #ddd; padding: 8px;">peticao_executado_suspensao_sobrestamento</td>
            </tr>
            <tr>
              <td style="border: 1px solid #ddd; padding: 8px;">peticao_exequente_extincao_pagamento</td>
            </tr>
            <tr>
              <td style="border: 1px solid #ddd; padding: 8px;">peticao_exequente_indeferir_sobrestamento</td>
            </tr>
            <tr>
              <td style="border: 1px solid #ddd; padding: 8px;">peticao_exequente_suspensao_sobrestamento</td>
            </tr>
            <tr>
              <td style="border: 1px solid #ddd; padding: 8px;">peticao_expedicao_alvara</td>
            </tr>
            <tr>
              <td style="border: 1px solid #ddd; padding: 8px;">peticao_extincao_LC</td>
            </tr>
            <tr>
              <td style="border: 1px solid #ddd; padding: 8px;">peticao_habilitacao</td>
            </tr>
            <tr>
              <td style="border: 1px solid #ddd; padding: 8px;">peticao_indisponibilidade_de_bens_suspensao</td>
            </tr>
            <tr>
              <td style="border: 1px solid #ddd; padding: 8px;">peticao_informa_embargos_execucao</td>
            </tr>
            <tr>
              <td style="border: 1px solid #ddd; padding: 8px;">peticao_informa_endereco</td>
            </tr>
            <tr>
              <td style="border: 1px solid #ddd; padding: 8px;">peticao_informa_pesquisa_frustrada_bens</td>
            </tr>
            <tr>
              <td style="border: 1px solid #ddd; padding: 8px;">peticao_juntada_dados_credor_fiduciario</td>
            </tr>
            <tr>
              <td style="border: 1px solid #ddd; padding: 8px;">peticao_nova_tentativa_penhora_SISBAJUD</td>
            </tr>
            <tr>
              <td style="border: 1px solid #ddd; padding: 8px;">peticao_oferecimento_garantia</td>
            </tr>
            <tr>
              <td style="border: 1px solid #ddd; padding: 8px;">peticao_penhora_imovel</td>
            </tr>
            <tr>
              <td style="border: 1px solid #ddd; padding: 8px;">peticao_regularizar_polo_passivo_espolio</td>
            </tr>
            <tr>
              <td style="border: 1px solid #ddd; padding: 8px;">peticao_sem_interesse_recorrer</td>
            </tr>
            <tr>
              <td style="border: 1px solid #ddd; padding: 8px;">peticao_suspensao_12_meses</td>
            </tr>
            <tr>
              <td style="border: 1px solid #ddd; padding: 8px;">peticao_suspensao_12_meses_parcelamento</td>
            </tr>
            <tr>
              <td style="border: 1px solid #ddd; padding: 8px;">peticao_suspensao_6_meses_parcelamento</td>
            </tr>
            <tr>
              <td style="border: 1px solid #ddd; padding: 8px;">peticao_suspensao_90_dias</td>
            </tr>
            <tr>
              <td style="border: 1px solid #ddd; padding: 8px;">peticao_suspensao_90_dias_inss_certidao_obito</td>
            </tr>
            <tr>
              <td style="border: 1px solid #ddd; padding: 8px;">peticao_suspensao_defensoria_publica</td>
            </tr>
            <tr>
              <td style="border: 1px solid #ddd; padding: 8px;">precatorio</td>
            </tr>
            <tr>
              <td style="border: 1px solid #ddd; padding: 8px;">procuracao</td>
            </tr>
            <tr>
              <td style="border: 1px solid #ddd; padding: 8px;">realizar_penhora</td>
            </tr>
            <tr>
              <td style="border: 1px solid #ddd; padding: 8px;">recibo_INFOJUD</td>
            </tr>
            <tr>
              <td style="border: 1px solid #ddd; padding: 8px;">recibo_SISBAJUD</td>
            </tr>
            <tr>
              <td style="border: 1px solid #ddd; padding: 8px;">recorrer_decisao</td>
            </tr>
            <tr>
              <td style="border: 1px solid #ddd; padding: 8px;">relacao_debitos_atualizados</td>
            </tr>
            <tr>
              <td style="border: 1px solid #ddd; padding: 8px;">relatorio_consulta_imovel_cartorios</td>
            </tr>
            <tr>
              <td style="border: 1px solid #ddd; padding: 8px;">relatorio_enderecos_cadastrados</td>
            </tr>
            <tr>
              <td style="border: 1px solid #ddd; padding: 8px;">relatorio_enderecos_diligenciados</td>
            </tr>
            <tr>
              <td style="border: 1px solid #ddd; padding: 8px;">relatorio_indisponibilidade</td>
            </tr>
            <tr>
              <td style="border: 1px solid #ddd; padding: 8px;">relatorio_pesquisa_bens_infrutifera</td>
            </tr>
            <tr>
              <td style="border: 1px solid #ddd; padding: 8px;">solicitacao_protesto</td>
            </tr>
            <tr>
              <td style="border: 1px solid #ddd; padding: 8px;">substabelecimento</td>
            </tr>
            <tr>
              <td style="border: 1px solid #ddd; padding: 8px;">termo_acordo</td>
            </tr>
          </tbody>
        </table>
      </div>
  </details>

  <details>
      <summary style="font-size: 1.3em;">Lista de Estados</summary>
      <div style="display: flex; justify-content: center; width: 100%;">
        <table style="width: 100%; border-collapse: collapse; table-layout: fixed; text-align: left;">
          <thead>
            <tr>
              <th style="border: 1px solid #ddd; padding: 8px; background-color: #f2f2f2; text-align: center;">Estados</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td style="border: 1px solid #ddd; padding: 8px;">aguardando_alegacao_parcelamento</td>
            </tr> 
            <tr>
              <td style="border: 1px solid #ddd; padding: 8px;">aguardando_dados_administrador_judicial</td>
            </tr>
            <tr>
              <td style="border: 1px solid #ddd; padding: 8px;">aguardando_detalhe_veiculo</td>
            </tr>
            <tr>
              <td style="border: 1px solid #ddd; padding: 8px;">aguardando_endereco</td>
            </tr>
            <tr>
              <td style="border: 1px solid #ddd; padding: 8px;">aguardando_espolio_emenda</td>
            </tr>
            <tr>
              <td style="border: 1px solid #ddd; padding: 8px;">aguardando_impugnacao_excecao_pre_exec</td>
            </tr>
            <tr>
              <td style="border: 1px solid #ddd; padding: 8px;">aguardando_indicacao_bens</td>
            </tr>
            <tr>
              <td style="border: 1px solid #ddd; padding: 8px;">aguardando_intimacao_executado_pagamento_sinal</td>
            </tr>
            <tr>
              <td style="border: 1px solid #ddd; padding: 8px;">aguardando_intimacao_executado_penhora</td>
            </tr>
            <tr>
              <td style="border: 1px solid #ddd; padding: 8px;">aguardando_levantamento</td>
            </tr>
            <tr>
              <td style="border: 1px solid #ddd; padding: 8px;">aguardando_manifestacao_conciliacao</td>
            </tr>
            <tr>
              <td style="border: 1px solid #ddd; padding: 8px;">aguardando_manifestacao_embargos_declaracao_executado</td>
            </tr>
            <tr>
              <td style="border: 1px solid #ddd; padding: 8px;">aguardando_manifestacao_parcelamento</td>
            </tr>
            <tr>
              <td style="border: 1px solid #ddd; padding: 8px;">aguardando_manifestacao_prescricao</td>
            </tr>
            <tr>
              <td style="border: 1px solid #ddd; padding: 8px;">aguardando_manifestacao_retificar_polo</td>
            </tr>
            <tr>
              <td style="border: 1px solid #ddd; padding: 8px;">aguardando_manifestacao_sobrestamento</td>
            </tr>
            <tr>
              <td style="border: 1px solid #ddd; padding: 8px;">aguardando_posicao_alegacao_quitacao</td>
            </tr>
            <tr>
              <td style="border: 1px solid #ddd; padding: 8px;">aguardando_posicao_valor_inferior_LC</td>
            </tr>
            <tr>
              <td style="border: 1px solid #ddd; padding: 8px;">aguardando_valor_penhora</td>
            </tr>
            <tr>
              <td style="border: 1px solid #ddd; padding: 8px;">ajuizado</td>
            </tr>
            <tr>
              <td style="border: 1px solid #ddd; padding: 8px;">arquivado</td>
            </tr>
            <tr>
              <td style="border: 1px solid #ddd; padding: 8px;">diligencia_expedicao_alvara</td>
            </tr>
            <tr>
              <td style="border: 1px solid #ddd; padding: 8px;">diligencia_indisponibilidade</td>
            </tr>
            <tr>
              <td style="border: 1px solid #ddd; padding: 8px;">em_citacao</td>
            </tr>
            <tr>
              <td style="border: 1px solid #ddd; padding: 8px;">em_constricao_INFOJUD</td>
            </tr>
            <tr>
              <td style="border: 1px solid #ddd; padding: 8px;">em_constricao_RENAJUD</td>
            </tr>
            <tr>
              <td style="border: 1px solid #ddd; padding: 8px;">em_constricao_SISBAJUD</td>
            </tr>
            <tr>
              <td style="border: 1px solid #ddd; padding: 8px;">em_constricao_de_bens</td>
            </tr>
            <tr>
              <td style="border: 1px solid #ddd; padding: 8px;">em_embargos</td>
            </tr>
            <tr>
              <td style="border: 1px solid #ddd; padding: 8px;">executado_intimado_penhora</td>
            </tr>
            <tr>
              <td style="border: 1px solid #ddd; padding: 8px;">extinto</td>
            </tr>
            <tr>
              <td style="border: 1px solid #ddd; padding: 8px;">migrado</td>
            </tr>
            <tr>
              <td style="border: 1px solid #ddd; padding: 8px;">suspenso_12meses_parcelamento</td>
            </tr>
            <tr>
            </tr>
          </tbody>
        </table>
      </div>
    </details>

<details>
  <summary style="font-size: 1.3em;">Lista de Fases</summary>
  <div style="display: flex; justify-content: center; width: 100%;">
    <table style="width: 100%; border-collapse: collapse; table-layout: fixed; text-align: left;">
      <thead>
        <tr>
          <th style="border: 1px solid #ddd; padding: 8px; background-color: #f2f2f2; text-align: center;">Fases</th>
        </tr>
      </thead>
      <tbody>
        <tr><td style="border: 1px solid #ddd; padding: 8px;">leave_steady_phase</td></tr>
        <tr><td style="border: 1px solid #ddd; padding: 8px;">update_phase_ajuizado</td></tr>
        <tr><td style="border: 1px solid #ddd; padding: 8px;">update_phase_arquivado</td></tr>
        <tr><td style="border: 1px solid #ddd; padding: 8px;">update_phase_em_citacao</td></tr>
        <tr><td style="border: 1px solid #ddd; padding: 8px;">update_phase_em_constricao_de_bens</td></tr>
        <tr><td style="border: 1px solid #ddd; padding: 8px;">update_phase_em_excecao_pre_exec</td></tr>
        <tr><td style="border: 1px solid #ddd; padding: 8px;">update_phase_extinto</td></tr>
        <tr><td style="border: 1px solid #ddd; padding: 8px;">update_phase_migrado</td></tr>
        <tr><td style="border: 1px solid #ddd; padding: 8px;">update_phase_suspenso</td></tr>
      </tbody>
    </table>
  </div>
</details>







### OCR

_OCR_ é o submódulo responsável por fazer a extração de texto de documentos, sendo capaz de lidar com documentos escaneados. 

Como resultado, um [parquet file](https://parquet.apache.org/) é criado dentro da pasta do processo. Este arquivo contém o texto extraído de cada página do documento. Adicionalmente, um arquivo `documento.txt` é criado em cada pasta de documento, contendo o texto extraído de todas as páginas do documento.

Ao final do fluxo do OCR é gerado um arquivo .parquet. Segue uma breve descrição das coluas presentes no arquivo:

| Coluna  | Descrição  |
|-----------|-----------|
| process_number | numero do processo |
| path | caminho do texto | 
| page | numero de paginas |
| text | texto do processo |
| source | formato do texto (HTML,PDF) |

Para mais detalhes sobre a implementação, acesse o [repositório oficial](https://gitlab.com/gpam/osiris/prototypes/ocr-osiris/).

### CDA

_CDA_ é o submódulo responsável por realizar consultas no *SITAF* para obter informações sobre os CDAs de um processo. O resultado obtido é salvo no arquivo `documentos-cdas.json` dentro da pasta do processo.

Exemplo de resultado obtido:

```json
{
    "debito": false,
    "suspenso": false,
    "quitado": false,
    "Certidoes_CDAs": {},
    "Resumo": {
        "Quitado": {
            "Total": 0
        },
        "Suspenso": {
            "Total": 0
        },
        "Debito": {
            "Total": 0
        }
    }
}
```

#### Obtenção de CDAs

Para obter a lista de CDAs de um processo, o submódulo utiliza o arquivo `.parquet` gerado pelo _OCR_ para ter acesso aos textos dos documentos do processo. Com isso, o submódulo consegue identificar os CDAs presentes nos documentos e, em seguida, realizar consultas no *SITAF* para obter informações sobre os CDAs.

Ao processar um documento, o submódulo verifica a existência de um (ou mais) CDA(s) no texto do documento através de expressões regulares.

#### Consulta no SITAF

Para a consulta no *SITAF* ser possível, é necessário a configuração das *urls* a serem acessadas no arquivo de configuração `settings.json`. 

*Atenção: O serviço de consulta oficial não permite consultas sem estar com o IP autorizado.*

```json
{
  "sitaf_url_dev": "example.com",
  "sitaf_url_prod": "example.com"
}
```

#### Rotulos forçados

O submodulo de CDAs força os rotulos `quitado_sitaf` e `suspensao_divparcelada`. O rotulo `quitado_sitaf` é forçado quando todas as CDAs estão quitadas. O rotulo `suspensao_divparcelada` é forçado quando não existe nenhuma CDA em debito e exista pelo menos uma CDA suspensa. Os rotulos forçados alteram o rotulo do ultimo aviso no arquivo `documentos_avisos.json` na raiz do processo.

### Endereços

_Endereços_ é o submódulo responsável pela verificação de endereços encontrados através da consulta do documento (CPF ou CNPJ) da entidade legal. O objetivo é verificar se houve diligência (citação no eCarta) para o endereço encontrado para sugerir novos endereços para diligência.

As informações a respeito dos documentos e endereços encontrados são salvas no arquivo `documentos-enderecos.json` dentro da pasta do processo. Adicionalmente, o submódulo inclui informações sobre eCartas, caso existam, no arquivo `resposta_ecartas.json` e também adiciona o campo "citado" em cada aviso em `documentos-avisos.json`.

Para a consulta dos endereços serem possíveis, é necessário a configuração das *urls* a serem acessadas no arquivo de configuração `settings.json`. 

```json
{
  "enderecos_url_prod": "example.com",
  "enderecos_url_dev": "example.com",
  "enderecos_auth_prod": "tokenAutenticacao",
  "enderecos_auth_dev": "tokenAutenticacao",
}
```

### Minutas

_Minutas_ é o submódulo responsável pela indicação das minutas correspondentes aos avisos presentes em `documentos-avisos.json`. A partir do rótulo presente em um aviso, o submódulo verifica se existe alguma minuta correspondente. Se não existir, é informado que não existe um template de minuta para tal rótulo.

Uma vez existente, a minuta será indicada no formato *base64*, a partir da chave `minutas` do aviso correspondente no `documentos-avisos.json`. O texto pode ser personalizado, incluindo cabeçalho e outras informações a depender do rótulo.

#### Configuração

Para o submódulo funcionar, algumas configurações são necessárias.

##### Indicar caminho de template

Os templates devem estar no formato `txt`.

```json
"link_minutas": {
    "chave_template": [
      "src/settings/minutas/chave_template.txt"
    ],
    "quitado_sitaf": [
      "src/settings/minutas/quitado_sitaf.txt"
    ],
    "suspensao_divparcelada": [
      "src/settings/minutas/suspensao_divparcelada.txt"
    ],
    "penhora_novapenhora": [
      "src/settings/minutas/penhora_novapenhora.txt"
    ],
}
```

##### Indicar tradução de cada rótulo

Para cada rótulo de um aviso, deve ser indicada a*(s)* chave*(s)* do*(s)* template*(s)* de minuta.

```json
"label_minuta_mapping": {
    "rotulo": ["chave_template", "penhora_novapenhora"],
    "quitado_sitaf": ["quitado_sitaf"],
    "suspensao_divparcelada": ["suspensao_divparcelada"]
},
```

### Send avisos

Este submódulo é responsável por enviar os dados de um aviso gerado pelo Osiris, para um endpoint configurável via _CONFIG.json_. Basta configurar a url `SEND_AVISOS_URL`, e o login `SEND_AVISOS_LOGIN`. Assume-se que o endpoint que receberá os dados é autenticado via bearer, portanto será realizado uma requisição para se autenticar no sistema que receberá os dados, em seguida os dados serão enviados junto ao _Token_ de autenticação. mais detalhes do comportamento esperado pelo endpoint que recebe os dados pode ser encontrado no [repositório](https://gitlab.com/gpam/osiris/prototypes/mni-simulador) que simula o endpoint 'recebedor'.

```json
    ...
    "SEND_AVISOS_URL": "http://0.0.0.0:9090",
    "SEND_AVISOS_LOGIN" : {"username" : "username",  "password" : "password"}
    ...
```

Para se autenticar, o Osiris fará uma requisição utilizando o verbo _POST_ para a URL configurada em `SEND_AVISOS_URL` sufixada pelo path `/token` enviando os campos _username_ e _password_ configurados no `SEND_AVISOS_LOGIN`. É esperado que o endpoint de autenticação retorne um _JSON_ com um campo **access_token** contendo o conteúdo do token [JWT](https://jwt.io/).

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIiwiaWF0IjoxNTE2MjM5MDIyfQ.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c"
}
```

Após se autenticar no sistema, será feita uma requisição utilizando o verbo _POST_ para a URL configurada em `SEND_AVISOS_URL`, sufixada pelo path `/lastAviso`. O header da requisição incluirá o token proveniente da autenticação, e o body conterá os dados no formato JSON. Este último é composto por:

#### request_uuid

UUID da requisição que provocou o sistema.

#### processos

Lista de processos concluídos com sucesso. O campo **aviso** de cada processo possui o mesmo formato do aviso retornado pelo PJE Integração. Adicionalmente, são incluídos o ID do documento (**documento**) associado ao **aviso**, o rótulo (**rotulo**) inferido pelo modelo e uma lista de link para as minutas (**minutas**).

#### ignorados

Lista de processos ignorados pelo `Send Avisos`. Os processos ignorados são aqueles que não possuem dados o suficiente para serem enviados via _send avisos_, nesse caso o processo é enviado em uma lista separada contendo o seu ID (**processo_id**), um _enum_ contendo o motivo dele ter sido ignorado (**status**) e um campo descrevendo o significado do _enum_ (**status_detail**). Possíveis status para um processo ser ignorado incluem:

- NONEXISTENT: Processo não encontrado ao consultar MNI.
- INVALID: Não é um processo de execução fiscal.
- WITHOUT_AVISOS: Não há avisos para este processo.
- MAX_TRIES_EXCEEDED: O processo atingiu o número máximo de tentativas.
- NO_DISK_SPACE: Não há espaço em disco para salvar os dados do processo.
- VERSION_MISMATCH: A requisição foi feita com uma versão diferente da versão atual do Osiris.

#### version

Representa a versão do Osiris e de seus submódulos (**classificador** e **visualizador**) no momento em que o sistema foi acionado. A versão de cada componente é composta pela _tag_ do repositório, sufixada por `-dirty` caso algum arquivo utilizado pelo sistema tenha sido alterado. Caso o componente não possua uma _tag_ associada, ele poderá ser subistituída por uma hash abreviada do commit.

```json
{
  "request_uuid": "5bf963d368e446609a2cc9789f9ad5ef",
  "processos": [
    {
      "aviso": {
        "numeroProcesso": "1111111-11.1111.1.11.1111",
        "numeroAviso": 12345678,
        "dataCriacaoExpediente": "2023-06-15T14:26:15.827-03:00",
        "dataCiencia": "2023-06-24T04:31:52.302-03:00",
        "cienciaSistema": false,
        "classeJudicial": "EXECUÇÃO FISCAL",
        "tipoPrazo": "D",
        "dataPrazoLegal": "2023-08-07T23:59:59.000-03:00",
        "meioExpedicaoExpediente": "E",
        "codigoDocumento": "6541230",
        "tipoProcessoDocumento": "Decisão",
        "fechado": false,
        "orgaoJulgador": {
          "id": 97,
          "nome": "1ª Vara de Execução Fiscal do DF"
        },
        "orgaoJulgadorExpediente": {
          "id": 97,
          "nome": "1ª Vara de Execução Fiscal do DF"
        },
        "quantidadePrazo": 30,
        "plantao": false,
        "prioridade": false,
        "urgencia": false
      },
      "documento": "987654321",
      "rotulo": "rotulo inferido",
      "minutas": ["link para minuta"]
    }
  ],
  "ignorados": [
    {
      "processo_id": "00527215820138070015",
      "status": "INVALID",
      "status_detail": "Os processo(s) foram classificado(s) como inválido(s)."
    }
  ],
  "version": {
    "osiris": "0.0.9-dirty",
    "classificador": "v1.0.0-0",
    "visualizador": "ed78e9a"
  }
}
```

### TJDFT sisbajud

Este submódulo opcional só é executado no fluxo _SISBAJUD_. Ele acessa o arquivo `documentos-cdas.json`, gerado pelo submódulo _CDA_, identifica quais das CDAs estão em estado de débito, e gera uma minuta contendo o resumo de todas as dívidas ativas no processo, bem como o valor total de débito. Além disso, ele acessa todos os avisos a partir do `documentos-avisos.json` e altera o valor do campo `rotulo` de cada aviso para `TJDFT_SISBAJUD`, que será consumido pelo módulo _Send Avisos_ depois.
