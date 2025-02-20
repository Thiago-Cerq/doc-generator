import json
import regex
import time
import pandas as pd
from transitions import Machine
from pydantic import BaseModel, Field, ValidationError
from typing import List, Dict, Any, Optional, Tuple, Union, Callable
from pathlib import Path
from functools import wraps
import asyncio
from contextlib import nullcontext
import httpx
import pickle
import numpy as np
import sys
import transitions
import requests
import hashlib
import os
#from utils.json_utils import fread_json, bfl

from FlagEmbedding import BGEM3FlagModel

try:
    from utils.process_regex import regex_search, regex_sub
    from utils.log import log, get_log_formatted, Logger 
except ImportError:
    from .utils.process_regex import regex_search, regex_sub
    from .utils.log import log, get_log_formatted, Logger

BASE_PATH = Path(__file__).parent.parent
DATA_PATH = BASE_PATH / "data" / "interim"
PATTERNS_PATH = DATA_PATH / "patterns.json"
TRANSITIONS_PATH = DATA_PATH / "transitions.json"
EMBEDDINGS_PATH = DATA_PATH / "catalogo_embs_bge_m3.parquet"   

Log = Logger()

def generate_cache_key(*args, **kwargs) -> str:
    """
    Gera uma chave de cache única com base nos argumentos fornecidos.

    Esta função cria uma chave de cache única ao serializar os argumentos posicionais (*args) 
    e os argumentos nomeados (**kwargs) em formato JSON. A string resultante é então 
    convertida em um hash MD5, garantindo que a chave seja uma string curta e única para
    identificar os parâmetros da função.

    Parâmetros:
    ----------
    *args : 
        Argumentos posicionais que devem ser considerados na geração da chave.
    
    **kwargs : 
        Argumentos nomeados que também são incluídos na geração da chave.

    Retorno:
    -------
    str:
        Uma string que representa o hash MD5 gerado a partir dos argumentos, servindo como 
        chave de cache única.

    Exemplo de uso:
    --------------
    >>> generate_cache_key(1, 2, foo='bar')
    'e99a18c428cb38d5f260853678922e03'
    """
    key = json.dumps({'args': args, 'kwargs': kwargs}, sort_keys=True)
    return hashlib.md5(key.encode()).hexdigest()

class FileCache:
    """
    Classe para gerenciamento de cache em arquivo.

    Esta classe permite carregar, salvar e gerenciar um cache persistente em um arquivo
    local no formato JSON. É útil para armazenar dados temporários entre execuções do 
    programa, como resultados de chamadas de funções ou de API, evitando a necessidade 
    de recalcular ou reconsultar dados.

    Atributos:
    ----------
    cache_file : str
        O caminho do arquivo de cache que será utilizado para armazenar os dados.
    
    cache : Dict[str, Dict]
        O dicionário que contém os dados do cache, carregado a partir do arquivo de cache.

    Métodos:
    --------
    __init__(cache_file: str)
        Inicializa a instância da classe com o caminho do arquivo de cache e carrega 
        os dados do arquivo, se disponíveis.

    load_cache() -> Dict[str, Dict]
        Carrega os dados do cache a partir do arquivo especificado. Se o arquivo de cache
        não existir, retorna um dicionário vazio.
    
    save_cache() -> None
        Salva os dados do cache atual no arquivo de cache.
    
    get(key: str) -> Optional[Dict]
        Retorna o valor associado a uma chave no cache. Se a chave não existir, retorna `None`.
    
    set(key: str, value: Dict) -> None
        Define ou atualiza o valor de uma chave no cache e salva o cache no arquivo.
    
    clear() -> None
        Limpa todos os dados do cache e salva o cache vazio no arquivo.
    """
    
    def __init__(self, cache_file: str):
        """
        Inicializa o FileCache com o caminho do arquivo de cache.

        Parâmetros:
        -----------
        cache_file : str
            O caminho do arquivo onde o cache será armazenado.
        """
        self.cache_file = cache_file
        self.cache = self.load_cache()

    def load_cache(self) -> Dict[str, Dict]:
        """
        Carrega o cache a partir de um arquivo.

        Se o arquivo de cache existir, os dados são carregados e retornados como um 
        dicionário. Caso o arquivo não exista, um dicionário vazio é retornado.

        Retorno:
        --------
        Dict[str, Dict]:
            O dicionário contendo os dados do cache.
        """
        if self.cache_file is not None and os.path.exists(self.cache_file):
            with open(self.cache_file, 'r') as f:
                return json.load(f)
        return {}

    def save_cache(self) -> None:
        """
        Salva o cache atual em um arquivo.

        Escreve os dados do cache no arquivo especificado em formato JSON.
        """
        with open(self.cache_file, 'w') as f:
            json.dump(self.cache, f)

    def get(self, key: str) -> Optional[Dict]:
        """
        Recupera um item do cache com base em sua chave.

        Parâmetros:
        -----------
        key : str
            A chave do item a ser recuperado.

        Retorno:
        --------
        Optional[Dict]:
            O valor associado à chave, ou `None` se a chave não existir no cache.
        """
        return self.cache.get(key)

    def set(self, key: str, value: Dict) -> None:
        """
        Define ou atualiza um item no cache.

        Atualiza o valor de uma chave no cache e salva as alterações no arquivo.

        Parâmetros:
        -----------
        key : str
            A chave a ser definida ou atualizada no cache.
        value : Dict
            O valor a ser associado à chave no cache.
        """
        self.cache[key] = value
        self.save_cache()

    def clear(self) -> None:
        """
        Limpa todos os itens do cache.

        Apaga todos os dados do cache e salva o cache vazio no arquivo.
        """
        self.cache = {}
        self.save_cache()

class EmbeddingManager:
    def __init__(self, file_path: str) -> None:
        """
        Inicializa a classe e carrega apenas as colunas 'classe' e 'embedding' de um arquivo Parquet na memória.
        
        :param file_path: Caminho do arquivo Parquet.
        """
        try:
            Log.debug(f"E_S | INIT | Carregando embeddings do arquivo Parquet: {file_path}")
            # Carrega apenas as colunas 'classe' e 'embedding'
            self.df = pd.read_parquet(file_path, columns=['classe', 'embedding', 'origem'])
            
            Log.debug(f"E_S | INIT | Embeddings carregados com sucesso. Total de registros: {len(self.df)}")
        except FileNotFoundError:
            Log.debug("E_F | INIT | Arquivo de embeddings não encontrado.")
            self.df = pd.DataFrame()  # DataFrame vazio se o arquivo não for encontrado
        except Exception as e:
            Log.debug(f"E_F | INIT | Erro ao carregar embeddings: {e}")
            self.df = pd.DataFrame()  # DataFrame vazio em caso de outros erros

    def query_embeddings(
        self, 
        new_embedding: np.ndarray, 
        source_list: Optional[List[str]] = None, 
        unknown_label: str = 'unknown', 
        threshold: float = 0.8
    ) -> Union[Tuple[str, int, int], Tuple[str, int, int]]:
        """
        Consulta embeddings com base no novo embedding e, opcionalmente, em uma lista de origens.
        
        :param new_embedding: O novo embedding que será comparado.
        :param source_list: Lista opcional de origens para filtrar os dados.
        :param unknown_label: Rótulo a ser retornado caso não haja correspondência satisfatória.
        :param threshold: O valor mínimo de similaridade para uma correspondência.
        :return: Um tupla contendo o rótulo correspondente, o índice no DataFrame filtrado e o índice real, 
                 ou 'unknown_label' e (-1, -1) se a correspondência for abaixo do limiar.
        """
        try:
            if self.df is None or self.df.empty:
                Log.debug("E_F | QUERY_EMBEDDINGS | Nenhum embedding carregado na memória.")
                return unknown_label#, -1, -1

            # Se a source_list for fornecida, filtra pelo campo 'origem', se não, usa todos os dados
            if source_list is not None:
                if 'origem' not in self.df.columns:
                    Log.debug(f"E_F | QUERY_EMBEDDINGS | A coluna 'origem' não está disponível na memória.")
                    return unknown_label#, -1, -1
                filtered_df = self.df[self.df['origem'].isin(source_list)]
            else:
                filtered_df = self.df  # Nenhum filtro de origem aplicado

            if filtered_df.empty:
                Log.debug(f"E_F | QUERY_EMBEDDINGS | Nenhuma origem correspondente encontrada na lista: {source_list}")
                return unknown_label#, -1, -1

            # Extrai rótulos e embeddings do DataFrame filtrado
            labels = filtered_df['classe'].tolist()
            embeddings = filtered_df['embedding'].tolist()

            # Calcula similaridade de cosseno entre o novo embedding e cada embedding filtrado
            similarities = [np.dot(new_embedding, emb) / (np.linalg.norm(new_embedding) * np.linalg.norm(emb)) for emb in embeddings]

            max_similarity = max(similarities)
            index_max = similarities.index(max_similarity)
            actual_index = filtered_df.index[index_max]

            Log.debug(f"E_S | QUERY_EMBEDDINGS | Similaridade máxima: {max_similarity}, Limiar: {threshold}, Rótulo: {labels[index_max]}, Índice: {index_max}, Índice real: {actual_index}")
            
            # Verifica se a similaridade máxima excede o limiar
            if max_similarity > threshold:
                return labels[index_max]#, index_max, actual_index
            else:
                return unknown_label#, -1, -1

        except Exception as e:
            Log.debug(f"E_F | QUERY_EMBEDDINGS | Erro ao consultar embeddings: {e}")
            return "error"#, -1, -1

# Load patterns and transitions from JSON files
with open(PATTERNS_PATH, "r") as file:
    patterns = json.load(file)

with open(TRANSITIONS_PATH, "r") as file:
    transitions_data = json.load(file)

# Load embeddings and labels
embedding_manager = EmbeddingManager(EMBEDDINGS_PATH)


class Peca(BaseModel):
    opcao: str = Field(description="tipo da peça processual")


def cosine_similarity(vec1, vec2):
    """
    Calcula a similaridade do cosseno entre dois vetores.

    A similaridade do cosseno é uma medida de similaridade entre dois vetores 
    que mede o cosseno do ângulo entre eles. Ela varia de -1 a 1, onde 1 indica 
    que os vetores apontam na mesma direção, 0 indica que os vetores são ortogonais
    (sem similaridade) e -1 indica que os vetores estão em direções opostas.

    Parâmetros:
    -----------
    vec1 : list ou array-like
        O primeiro vetor de entrada.
    
    vec2 : list ou array-like
        O segundo vetor de entrada.

    Retorno:
    --------
    float:
        O valor da similaridade do cosseno entre os dois vetores.

    Exemplo de uso:
    ---------------
    >>> cosine_similarity([1, 0, 0], [0, 1, 0])
    0.0

    >>> cosine_similarity([1, 0, 0], [1, 0, 0])
    1.0

    >>> cosine_similarity([1, 2, 3], [4, 5, 6])
    0.9746318461970762
    """
    vec1 = np.array(vec1)
    vec2 = np.array(vec2)
    return np.dot(vec1, vec2) / (np.linalg.norm(vec1) * np.linalg.norm(vec2))

@log
async def query_llm(
    msgs: List[Dict[str, str]], 
    model: str, 
    skip_cache=False, 
    **kwargs
) -> dict:
    test_mode: bool = kwargs.pop("test_mode", False)
    default_return: dict = kwargs.pop(
        "default_return", {"message": {"content": "Missing LLM URL"}}
    )
    _format = kwargs.pop("_format", None)
    url = kwargs.pop("url", None)
    semaphore = kwargs.pop("semaphore", None)

    if url in (None, "") or test_mode:
        return default_return

    url += '/chat'

    user = kwargs.pop("llm_user", None)
    password = kwargs.pop("llm_password", None)
    apikey = kwargs.pop("llm_apikey", None)

    cache = kwargs.pop("chat_cache", None)

    auth = httpx.BasicAuth(user, password) if user and password else None
    Log.debug(f"Using model {model} with url {url}")
    for message in msgs:
        Log.debug(f"{message['role']}: {message['content']}")

    temperature = 0

    cache_key = generate_cache_key(msgs, temperature, model)
    cached_response = cache.get(cache_key)

    if cached_response and not skip_cache:
        Log.debug("Using cache")
        return {
            "content": cached_response,
            "input_tokens": 0,
            "output_tokens": 0
        }

    payload = {
        "messages": msgs,
        "model": model,
        "temperature": temperature,
        "stream": False
    }
    headers = {"apikey": apikey} if apikey else None

    if _format is not None:
        payload["format"] = _format

    async with httpx.AsyncClient(timeout=500) as client:
        if semaphore:
            async with semaphore:
                response = await client.post(url, json=payload, auth=auth, headers=headers)
        else:
            response = await client.post(url, json=payload, auth=auth, headers=headers)

    response.raise_for_status()
    response_dict = response.json()
    
    Log.debug(f"queryLLM response_dict: {response_dict}")

    # Extract token usage information
    input_tokens = response_dict.get("prompt_eval_count", 0)
    output_tokens = response_dict.get("eval_count", 0)
    
    try:
        input_tokens = int(input_tokens)
    except Exception as e:
        Log.error(
            f"Erro na tentativa de converter input_tokens: {input_tokens}"
        )
        Log.error(e)
        input_tokens = 0
        
    try:
        output_tokens = int(output_tokens)
    except Exception as e:
        Log.error(
            f"Erro na tentativa de converter output_tokens: {output_tokens}"
        )
        Log.error(e)
        output_tokens = 0        

    # Cache the response content
    cache.set(cache_key, response_dict['message']['content'])

    Log.debug(f"LLM response status: {response.status_code}", flush=True)
    return {
        "content": response_dict['message']['content'],
        "input_tokens": input_tokens,
        "output_tokens": output_tokens
    }


def create_message(role: str, content: str) -> Dict[str, str]:
    """
    Cria uma mensagem estruturada com um papel (role) e conteúdo.

    Esta função recebe dois parâmetros: o papel (role) e o conteúdo (content), e 
    retorna um dicionário com essas informações formatadas para uso, por exemplo, 
    em interações com APIs de modelos de linguagem, onde as mensagens são estruturadas 
    com base no papel (como "user" ou "system") e o conteúdo da mensagem.

    Parâmetros:
    -----------
    role : str
        O papel da mensagem, como "user", "system" ou "assistant".
    
    content : str
        O conteúdo da mensagem que será associada ao papel.

    Retorno:
    --------
    Dict[str, str]:
        Um dicionário contendo o papel e o conteúdo da mensagem.

    Exemplo de uso:
    ---------------
    >>> create_message("user", "Olá, como você está?")
    {'role': 'user', 'content': 'Olá, como você está?'}
    """
    return {"role": role, "content": content}


@log
async def build_prompt_opcao_peca(
    msg_erro: str = None, conteudo: str = "", opcoes: Dict[str, str] = [], **kwargs
) -> List[Dict[str, str]]:
    # Criar lista de mensagens
    messages = []

    input_summary = kwargs.pop("input_summary", False)

    options_str = "\n\n|opcao| descricao|\n|---|---|\n"
    options_str += "\n".join([f"|{key}|{value}|" for key, value in opcoes.items()])
    options_str += "\n|peca_doc_diverso| O conteudo da peça não pode ser associado a nenhumas das opções.|"

    prompt_inicial = "Atue como um assistente prestativo na triagem de peças jurídicas. A sua tarefa é ler o resumo de"
    prompt_inicial += f" uma peça e escolher uma opcao a seguir que a descreva:\n{options_str}\n\nEM CASO DE DÚVIDA RESPONDA: `peca_doc_diverso`"
    messages.append(create_message('system', prompt_inicial))
        
    messages.append(
        create_message(
            "system",
            f"\n\nNAO INVENTE, APENAS ESCOLHA UMA OPCAO. Lembre-se! EM CASO DE DÚVIDA RESPONDA: `peca_doc_diverso`"
            +'\n\nRetorne um json no formato do exemplo a seguir:\n\n```json\n{\n\t"opcao":"peca_doc_diverso",\n\t"razao":"O conteudo da peça não pode ser associado a nenhumas das opções."\n}\n```\n'
        )
    )

    # Add final instructions and content of the piece
    instrucao_final = f"Agora, leia o conteúdo a seguir e retorne a opcao:\n\n{conteudo}"
    messages.append(create_message("user", instrucao_final))

    return messages

@log
async def build_prompt_resumo(conteudo: str = "", **kwargs) -> List[Dict[str, str]]:
    messages = []
    prompt_inicial = """Voce e um assistente juridico hábil em resumir peças judiciais. 
A sua tarefa é ler um conteúdo e resumi-lo de maneira concisa. 
Em seus resumos, voce despreza os nomes de pessoas, quer sejam partes, advogados ou membros da justiça.
Além disso, você ignora informações óbvias, como por exemplo:
* advogado(a) pede deferimento
* autor e data de assinatura do documento
A grande ênfase do seu resumo está nos fatos e pedidos, quando se tratar de petições, ou no pronunciamento da justiça, quando se tratar de decisão, despacho ou sentença. 

Os seus resumos não trazem informações repetidas

O usuario já aguarda o resumo, portanto, você NÃO deve informar que se trata de resumo. 

A sua missão é receber um texto e gerar o resumo, sem aguardar outras interações do usuario."""

    messages.append(
        create_message(
            "user",
            f"{prompt_inicial}\n\nTomando como base o texto a seguir, forneça o seu resumo:\n\n{conteudo}",
        )
    )
    return messages

def validate_response(content: Dict[str, Any], model: BaseModel) -> Any:
    try:
        return model.model_validate(content)
    except ValidationError as e:
        return e

BGEM3_model = BGEM3FlagModel('BAAI/bge-m3', use_fp16=True)

def generate_embedding(sentence, model_name='BAAI/bge-m3', use_fp16=True, batch_size=12, max_length=1024):
    """
    Gera o embedding (vetor de características) de uma sentença usando um modelo pré-treinado.

    Esta função utiliza um modelo de linguagem para codificar uma sentença em um vetor
    denso de características (embedding), que pode ser usado para diversas tarefas de 
    processamento de linguagem natural, como comparação de similaridade entre textos.

    Parâmetros:
    -----------
    sentence : str
        A sentença para a qual o embedding será gerado.
    
    model_name : str, opcional
        O nome do modelo pré-treinado a ser usado para gerar o embedding. O valor padrão 
        é 'BAAI/bge-m3'.
    
    use_fp16 : bool, opcional
        Se True, utiliza ponto flutuante de 16 bits (fp16) para otimizar a eficiência 
        computacional. O valor padrão é True.
    
    batch_size : int, opcional
        O número de exemplos a serem processados em lote. O valor padrão é 12.
    
    max_length : int, opcional
        O tamanho máximo permitido para a sequência de entrada. O valor padrão é 1024.

    Retorno:
    --------
    np.ndarray:
        Um vetor denso representando o embedding da sentença fornecida.

    Exemplo de uso:
    ---------------
    >>> generate_embedding("Este é um exemplo de sentença.")
    array([...])  # Um vetor com os valores do embedding da sentença
    """
    embeddings = BGEM3_model.encode([sentence], batch_size=batch_size, max_length=max_length)['dense_vecs']
    return embeddings[0]

def extract_states(transitions):
    """
    Extrai os estados únicos a partir de uma lista de transições.

    Esta função percorre uma lista de transições, onde cada transição contém um estado 
    de origem ("source") e um estado de destino ("dest"). Ela coleta todos os estados 
    únicos presentes nas transições, tanto as fontes quanto os destinos, e retorna uma 
    lista contendo esses estados.

    Parâmetros:
    -----------
    transitions : list[dict]
        Uma lista de dicionários onde cada dicionário representa uma transição. 
        Cada transição deve conter uma chave "source" (que pode ser uma lista de estados 
        ou um estado único) e, opcionalmente, uma chave "dest", que indica o estado de 
        destino.

    Retorno:
    --------
    list:
        Uma lista contendo todos os estados únicos encontrados nas transições.

    Exemplo de uso:
    ---------------
    >>> transitions = [
            {"source": "A", "dest": "B"},
            {"source": ["B", "C"], "dest": "D"},
            {"source": "E", "dest": None}
        ]
    >>> extract_states(transitions)
    ['A', 'B', 'C', 'D', 'E']
    """
    states = set()
    for transition in transitions:
        if isinstance(transition["source"], list):
            states.update(transition["source"])
        else:
            states.add(transition["source"])
        if transition.get("dest") is not None:
            states.add(transition["dest"])
    return list(states)

class Lawsuit:
    def __init__(self, transitions_data, url, semaphore, model):
        self.states = extract_states(transitions_data)
        self.state = "inicio"
        self.phase = "inicio"
        self.call_state = None
        self.call_phase = None
        self.url = url
        self.semaphore = semaphore
        self.model = model

        # Configure the state machine
        self.machine = Machine(model=self, states=self.states, initial=self.state)

        # Add transitions loaded from JSON file
        for transition in transitions_data:
            self.machine.add_transition(
                trigger=transition["trigger"],
                source=transition["source"],
                dest=transition.get("dest", None),
                after=transition.get("after", None),
                before=transition.get("before", None),
            )

    def update_phase_ajuizado(self):
        self.phase = "ajuizado"

    def update_phase_em_citacao(self):
        self.phase = "em_citacao"

    def update_phase_em_constricao_de_bens(self):
        self.phase = 'em_constricao_de_bens'
        if self.state in ['em_citacao', 'aguardando_endereco']:
            self.state = 'aguardando_SISBAJUD'

    def update_phase_em_embargos_de_declaracao(self):
        self.phase = "em_embargos_declaracao"

    def update_phase_em_apelacao(self):
        self.phase = "em_apelacao"

    def update_phase_suspenso(self):
        self.phase = "suspenso"

    def update_phase_arquivado(self):
        self.phase = "arquivado"

    def update_phase_extinto(self):
        self.phase = "extinto"

    def update_last_phase(self):
        if self.call_phase is None:
            self.call_phase = self.phase    
        if self.call_state is None:
            self.call_state = self.state   

    def update_phase_em_excecao_pre_exec(self):
        self.phase = "em_excecao_pre_exec"

    def leave_phase_em_excecao_pre_exec(self):
        if self.call_phase is not None:
            self.phase = self.call_phase 
            self.call_phase = None
            
    def leave_steady_phase(self):
        if self.call_phase is not None:
            self.phase = self.call_phase 
            self.call_phase = None   
        if self.call_state is not None:
            self.state = self.call_state
            self.call_state = None

    def leave_phase_suspenso(self):
        self.phase = self.call_phase
        self.call_phase = None

    @log
    async def detect_trigger(self, documento, historico, **kwargs):
        metodo = None
        input_tokens = 0
        output_tokens = 0
        trigger_catch = None
        start_time = time.time()
        trigger_detected = False
        
        event_loop = asyncio.get_event_loop()
        
        conteudo = documento["conteudo"]
        
        if conteudo is None:
            return trigger_catch, metodo, 0, input_tokens, ouput_tokens
        
        
#         if documento["origem"]!='tribunal' and documento["id_doc"] != documento["id_root_doc"] and any(
#             doc["state"].startswith("peticao")
#             for doc in historico.values()
#             if doc["id_root_doc"] == documento["id_root_doc"]
#         ):
#             return "doc_peticao", "padrao", 0     
        
        # Verifica menções a documentos anteriores
        for id_doc, event in historico.items():
            if id_doc in conteudo:
                Log.debug(
                    f"Menção a documento {id_doc} encontrado, substituindo por trigger {event['trigger']}"
                )
                conteudo = conteudo.replace(id_doc, f" ({id_doc}) {event['trigger']}")
        pattern_match = await regex_search(
            pattern=r"(?:petição|pedido).{0,100}?(?:retro|imediatamente\s*anterior)",
            string=conteudo,
            flags=regex.IGNORECASE | regex.DOTALL,
        )
        
        if pattern_match:
            keys = list(historico.keys())
            keys.reverse()

            Log.debug(f'{20*">"} {keys}')
            for key in keys:
                event = historico[key]
                if "peticao" in event["trigger"]:
                    conteudo = await regex_sub(
                        pattern=r"(?:petição|pedido).{0,100}?(?:retro|imediatamente\s*anterior)",
                        repl=f" ({key}) {event['trigger']}",
                        string=conteudo,
                        flags=regex.IGNORECASE | regex.DOTALL,
                    )
                    
                    Log.debug(
                        f"Menção a 'peticao/pedido retro' encontrada, substituindo por trigger {event['trigger']}"
                    )
                    Log.debug(f'{50*"$"}\n\n{conteudo}\n\n{50*"$"}')
                    break
        
        pattern_match = await regex_search(
            pattern=r"(?:decis[aã]o|despacho|determina[cç][aã]o).{0,100}?(?:retro|imediatamente\s*anterior)",
            string=conteudo,
            flags=regex.IGNORECASE | regex.DOTALL,
        )
        
        if pattern_match:
            keys = list(historico.keys())
            keys.reverse()

            Log.debug(f'{20*">"} {keys}')
            for key in keys:
                event = historico[key]
                if "decisao" in event["trigger"] or "despacho" in event["trigger"] or "intima" in event["trigger"]:
                    conteudo = await regex_sub(
                        pattern=r"decis[aã]o\s*retro|despacho|determina[cç][aã]o.{0,100}?(?:retro|imediatamente\s*anterior)",
                        repl=f" ({key}) {event['trigger']}",
                        string=conteudo,
                        flags=regex.IGNORECASE | regex.DOTALL,
                    )
                    
                    Log.debug(
                        f"Menção a 'decisao/despacho retro' encontrada, substituindo por trigger {event['trigger']}"
                    )
                    break
        
        Log.debug(f"Conteudo:\n{conteudo}\n\n...")      

        # Stage 1: Regex pattern matching
        
        origens = ["comum", documento["origem"]] if  documento["origem"]!= "unk" else list(patterns.keys())
        
        for origem in origens:
            if origem in patterns:
                for trigger, pats in patterns[origem].items():
                    for pat in pats["padrao"]:
                        #Log.debug(f"DEBUG: trigger {trigger} padrao {pat}")
                        pattern_match = await regex_search(
                            pattern=pat,
                            string=conteudo,
                            flags=regex.IGNORECASE | regex.DOTALL,
                        )
                        if pattern_match:
                            Log.debug(f"Regex pattern matched for origem {origem.upper()} and trigger '{trigger}' with pattern '{pat}'")
                            trigger_detected = True
                            trigger_catch = trigger
                            metodo = "padrao"
                            break
                            
#                         elif verbose:
#                             Log.debug(f"No match for origem {origem.upper()} and trigger '{trigger}' with pattern '{pat}'")
                        #     # if trigger == 'certidao_AR_mudou':
                        #     Log.debug(f'documento : {documento}\n\nhistorico: {historico_triggers}')
                        #     input('>>>>>>>>>>>>> NAO ENCONTROU CERTIDAO AR MUDOU <<<<<<<<<<<<<<<')                            

                    if trigger_detected:
                        break

            if trigger_detected:
                break

        # Stage 2: Embedding comparison if no regex match found
        if not trigger_detected:
            Log.debug("No regex pattern matched, using embeddings for classification.")

            # Generate embedding for the document content
            #test_embedding = generate_embeddings([documento['conteudo']])[documento['conteudo']]
            Log.debug(f'detect_trigger | self.url: {self.url}')
            
            messages = await build_prompt_resumo(conteudo, **kwargs)

            response_dict = await query_llm(
                messages, model=self.model, url=self.url, **kwargs
            )
            
            conteudo = response_dict['content']
            input_tokens += response_dict['input_tokens']
            output_tokens += response_dict['output_tokens']

            Log.debug(f'resposta LLM resumo:\n{conteudo}\n\n')

#             conteudo = response['message']['content']                  
            
            #embedding = generate_embedding(conteudo, API_URL=self.url, model=self.model, **kwargs)
            embedding = generate_embedding(conteudo)

            data = embedding_manager.query_embeddings(embedding, origens, "peca_doc_diverso", 0.83)
            
            #Log.debug(f'detect_trigger | query_embeddings | data: {data}')

            if data != "peca_doc_diverso":
                trigger_catch = data
                metodo = "embedding"
                trigger_detected = True


        # Stage 3: LLM if no embedding match found
        if not trigger_detected:
            Log.debug("No match from embeddings, using LLM for classification.")
                
            estimativa_tokens = len(conteudo.split())*.75
#             Log.debug(f"Estimativa tokens: {estimativa_tokens}")
#             if  estimativa_tokens > 8192 * 2:
#                 end_time = time.time()
#                 duracao = end_time - start_time
#                 return 'peca_doc_diverso', 'MaxToken', duracao
            
            content = None                
                
            # Prepare LLM prompt
            for conta_origem, origem in enumerate(origens):
                if conta_origem == 0:
                    trigger_set = patterns[origem].copy()
                else:
                    trigger_set.update(patterns[origem].copy())
                    
#             else:
#                 trigger_set = patterns[documento["origem"]].copy()
#                 trigger_set.update(patterns["comum"])

            opcoes = {
                trigger: value["descricao"]
                for trigger, value in trigger_set.items()
                if value["llm"]
            }            

            validation_result = None

            tolerance = 3

            msg_erro = None
            
            skip_cache = False

            for count in range(tolerance):

                messages = await build_prompt_opcao_peca(
                    msg_erro, 
                    conteudo, 
                    opcoes,  
                    **{**kwargs, "input_summary": documento["mimetype"]=="application/pdf"})
                
                response_dict = await query_llm(
                    messages,
                    model=self.model,
                    skip_cache=skip_cache, 
                    url=self.url,
                    _format="json",
                    **kwargs
                )
            
                content = response_dict['content']
                input_tokens += response_dict['input_tokens']
                output_tokens += response_dict['output_tokens']

                Log.debug(f"LLM response: {content}")

                try:
                    content = json.loads(content)

                    validation_result = validate_response(content, Peca)

                    if isinstance(validation_result, ValidationError):
                        Log.debug(
                            f"Erro dentro da tolerância {count+1}/{tolerance}\nResposta LLM: {content}\n\nResultado da Validação: {validation_result.errors()}\n\nreenviando o prompt para o LLM..."
                        )
                        msg_erro = ""
                        for error in validation_result.errors():
                            msg_erro += f'{error["type"]}: {error["loc"]}\n'
                        
                    else:
                        if "opcao" in content:
                            valid_triggers = []
                            for origem in origens:
                                valid_triggers += list(patterns[origem].keys())
                            opcao = content["opcao"]
                            if isinstance(opcao, str) and (
                                opcao in valid_triggers
                                or opcao == "peca_doc_diverso"
                            ):
                                trigger_detected = True
                                trigger_catch = opcao
                                metodo = "LLM"
                                break
                            else:
                                print(f"\n[DEBUG] Falhou na tentativa {count+1}/{tolerance}\n")                                
                                
                except Exception as e:
                    Log.debug(
                        f"Erro na tentativa {count+1}/{tolerance}\nResposta LLM: {content}"
                    )
                    Log.debug(e)
                skip_cache = True

        end_time = time.time()
        duracao = end_time - start_time
        Log.debug(f"Time taken for trigger detection: {duracao:.2f} seconds")

        return trigger_catch, metodo, duracao, input_tokens, output_tokens

@log
async def id_polo_passivo(
    metadados_path: Path = None,
    docs_path: Path = None,
    id_doc: str = None
) -> str:

    if docs_path:
        doc_path = docs_path / id_doc / "documento.txt"
    else:
        return "a path do diretório dos documentos não foi informada"

    try:
        with open(doc_path, "r", encoding="utf-8") as file:
            text = file.read()
    except FileNotFoundError:
        return f"arquivo {doc_path} não encontrado"

    if metadados_path:
        try:
            with open(metadados_path, "r") as file:
                metadados = json.loads(file.read())
        except Exception:
            return f"erro ao ler json em {metadados_path}"
    else:
        return "a path dos metadados não foi informada"

    polo = (metadados.get("dadosBasicos", {}).get("polo", [{},{}]))
    if len(polo) < 2:
        return "polo passivo não consta nos metadados"
    
    pessoas = polo[1].get("parte", [{}])

    for p in pessoas:
        doc_polo_passivo = p.get("pessoa", {}).get("numeroDocumentoPrincipal", "")
        nome = p.get("pessoa", {}).get("nome")

        if nome:
            nome_match = await regex_search(
                pattern=nome,
                string=text,
                flags=regex.IGNORECASE,
            )
            if nome_match:
                Log.debug(f"Alvo do AR cumprido encontrado: documento {id_doc} polo passivo {doc_polo_passivo}")
                return doc_polo_passivo

    doc_polo_passivo = "alvo não encontrado"
    return doc_polo_passivo

@log
async def process_documents(
    doc: dict,
    lawsuit: Lawsuit,
    historico: dict,
    last_phase: str = None,
    metadados_path: Path = None,
    docs_path: Path = None,
    **kwargs
) -> str:
    Log.debug("\n--- Processando Documento ---")
    Log.debug(f"Documento ID: {doc['id_doc']}")
    Log.debug(f"Origem: {doc['origem']}")
    Log.debug(f"Estado atual: {lawsuit.state}")
    Log.debug(f"Fase atual: {lawsuit.phase}")

    if last_phase in ["em_citacao", "ajuizado"] and doc["origem"] == "executado":
        lawsuit.update_phase_em_constricao_de_bens()
        Log.debug(f"Mudança de fase em razao de manifestacao do executado.")

    trigger, method, duration, input_tokens, output_tokens = await lawsuit.detect_trigger(doc, historico, **kwargs)

    Log.debug(f"Gatilho detectado: {trigger}")
    Log.debug(f"Executando gatilho '{trigger}' para estado '{lawsuit.state}'")

    last_state = lawsuit.state
    last_phase = lawsuit.phase

    if trigger is not None:
        try:
            if hasattr(lawsuit, trigger):
                getattr(lawsuit, trigger)()
            else:
                Log.debug(f"[ERROR] Gatilho '{trigger}' não encontrado na classe lawsuit.")
        except transitions.core.MachineError as e:
            Log.debug(f"[ERROR] Não é possível disparar o evento '{trigger}' a partir do estado '{lawsuit.state}': {e}")
    else:
        Log.error(f"[ERROR] Nenhum gatilho foi detectado.")
        
    try:
        polo_passivo = await id_polo_passivo(metadados_path, docs_path, doc["id_root_doc"].split('_')[0]) if trigger == "AR_cumprido" else "",
    except Exception as e:
        Log.error(f"[ERROR] Erro ao tentar mapear o polo passivo.\n{e}")
        polo_passivo = ''

    historico[doc["id_doc"]] = {
        "last_state": last_state,
        "last_phase": last_phase,
        "trigger": trigger if trigger is not None else "Nenhum",
        "metodo": method if method is not None else "Falha",
        "state": lawsuit.state,
        "phase": lawsuit.phase,
        "origem": doc["origem"],
        "id_root_doc": doc["id_root_doc"],
        "duracao": f"{duration:.2f}",
        "data": doc["datahora"].strftime("%Y/%m/%d"),
        "polo_passivo": polo_passivo,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        
    }

    Log.debug(f"Novo Estado: {lawsuit.state}")
    Log.debug(f"Nova Fase: {lawsuit.phase}")

    return last_phase

def config_log(func):
    @wraps(func)
    async def wrapper(*args, **kwargs):
        global Log
        Log = get_log_formatted(kwargs["df_doc"], **kwargs)
        Log.debug("Iniciando agente")

        kwargs["log"] = Log
        
        return await func(*args, **kwargs)
    return wrapper

@config_log
@log
async def agente(
    df_doc: pd.DataFrame,
    url: str = None,
    model: str = None,
    semaphore: asyncio.Semaphore = None,
    chat_cache_path: Path = BASE_PATH / 'chat_cache.json',
    num_processo: str = None,
    metadados_path: Path = None,
    docs_path: Path = None,
    **kwargs
) -> Dict[str, Any]:
        
    chat_cache = FileCache(chat_cache_path)
    lawsuit = Lawsuit(transitions_data, url, semaphore, model) 
        
    historico = {}
    fase = None

    for _, row in df_doc.iterrows():
        doc_dict = row.to_dict()
        doc_dict["conteudo"] = doc_dict.pop("txt")
        doc_dict["id_root_doc"] = doc_dict.get("id_root_doc", "-")
        doc_dict["origem"] =  "unk" if '_' in doc_dict["id_doc"] else doc_dict["origem"]
        fase = await process_documents(
            doc=doc_dict,
            lawsuit=lawsuit,
            historico=historico,
            last_phase=fase,
            chat_cache = chat_cache,
            metadados_path = metadados_path,
            docs_path = docs_path,
            **kwargs
        )

    return historico


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python source/agente.py <path_to_parquet> [llm_url] [model_name] [output (stdout)] [llm_apikey] [chat_cache_path] [metadados_path] [docs_path]")
        exit(0)

    df_doc = pd.read_parquet(Path(sys.argv[1]))
    url_llm = sys.argv[2] if len(sys.argv) > 2 else None
    model_llm = sys.argv[3] if len(sys.argv) > 3 else None
    output = sys.argv[4].lower() == "true" if len(sys.argv) > 4 else False
    apikey = sys.argv[5] if len(sys.argv) > 5 else None
    chat_cache_path = Path(sys.argv[6]) if len(sys.argv) > 6 else None
    metadados_path = Path(sys.argv[7]) if len(sys.argv) > 7 else None
    docs_path = Path(sys.argv[8]) if len(sys.argv) > 8 else None
    

    event_loop = asyncio.get_event_loop()
    event_loop.run_until_complete(
        agente(
            df_doc=df_doc,
            url=url_llm,
            model=model_llm,      
            output=output,
            llm_apikey=apikey,
            chat_cache_path=chat_cache_path,
            metadados_path = metadados_path,
            docs_path = docs_path,
        )
    )
