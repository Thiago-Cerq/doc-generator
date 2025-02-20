# Crew AI - Gerador de Documentação

Este projeto utiliza o [Crew AI](https://github.com/joaomdmoura/crewAI) para automatizar a geração de documentação baseada no código-fonte do projeto.

## Requisitos
- Python 3.8+
- Virtualenv
- Crew AI
- Ollama (para modelos de IA locais)

## Instalação

1. **Clone este repositório**
   ```bash
   git clone git@github.com:Thiago-Cerq/doc-generator.git
   cd doc-generator
   ```

2. **Crie um ambiente virtual**
   ```bash
   python -m venv venv
   source venv/bin/activate  # Linux/macOS
   venv\Scripts\activate  # Windows
   ```

3. **Instale as dependências**
   ```bash
   pip install -r requirements.txt
   ```

## Uso

1. **Certifique-se de que o Ollama esteja rodando**
   ```bash
   ollama serve
   ```

2. **Inicie o proxy**
   ```bash
   python proxy.py
   ```

3. **Execute a Crew para gerar a documentação**
   ```bash
   python main.py
   ```

4. **Verifique a documentação gerada**
   O arquivo de documentação será salvo no diretório raiz.

## Personalização
Se desejar modificar o comportamento da Crew, ajuste os prompts conforme necessário.

## Problemas Conhecidos
- ####.


## Contribuição
Fique à vontade para abrir issues ou enviar pull requests para melhorias no projeto.

