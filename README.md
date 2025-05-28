```markdown
# SIGEC-VE
# Sistema Inteligente de Gestão de Estações de Carregamento de VE (CSMS) com LLMs

Este projeto propõe uma arquitetura robusta e modular para um **Sistema de Gestão Central de Estações de Carregamento de Veículos Elétricos (CSMS)** que integra **Large Language Models (LLMs)** para funcionalidades avançadas de inteligência e automação. Utiliza o protocolo **OCPP (Open Charge Point Protocol)** para comunicação com os postos de carregamento e o **Model Context Protocol (MCP)** da Anthropic para a orquestração com os LLMs.

---

## 🚀 Visão Geral

O objetivo principal é construir um CSMS que não só gerencie as operações padrão de uma rede de carregamento (autenticação, transações, status), mas que também aproveite o poder dos LLMs para:

* **Interpretação de Linguagem Natural:** Permitir que operadores e, futuramente, usuários interajam com o sistema usando comandos em linguagem natural.
* **Smart Charging Avançado:** Otimizar o carregamento com base em dados contextuais complexos (previsões de demanda, preços de energia, preferências do usuário) analisados pelos LLMs.
* **Diagnóstico Preditivo:** Analisar logs e telemetria para prever falhas em postos de carregamento e sugerir ações de manutenção proativas.
* **Automação Inteligente:** Orquestrar fluxos de trabalho complexos, como reset remoto de postos ou ajustes de configuração, com base em decisões do LLM.

---

## 🏗️ Arquitetura do Projeto

A arquitetura é dividida em camadas lógicas para modularidade, escalabilidade e clareza.

### **1. Camada de Comunicação OCPP (`core/`)**
O coração do CSMS, responsável por estabelecer e manter a comunicação com os **Postos de Carregamento (CPs)**.
* **`ocpp_server.py`**: Implementa o servidor WebSocket que aceita conexões dos CPs e gerencia o roteamento das mensagens OCPP.
* **`ocpp_handlers.py`**: Contém as funções que processam e respondem às mensagens OCPP recebidas (e.g., `BootNotification`, `Authorize`, `MeterValues`).
* **Tecnologia**: **`mobilityhouse/ocpp`** (para implementação do protocolo) e **`websockets`** (para o transporte).

### **2. Camada de Lógica de Negócio (`business_logic/`)**
Contém as regras e inteligência operacional do CSMS. Interage com a camada de dados e, crucialmente, com a camada de integração LLM.
* **`auth_service.py`**: Lógica para autenticação e autorização de usuários.
* **`transaction_service.py`**: Gerencia o ciclo de vida das transações de carregamento.
* **`smart_charging_service.py`**: Implementa os algoritmos de gestão de energia, recebendo **insights e instruções do LLM**.
* **`device_management_service.py`**: Gerencia o inventário, configuração e status dos CPs.
* **`reporting_service.py`**: Responsável pela agregação e geração de dados para relatórios.

### **3. Camada de Dados (`data/`)**
Responsável pelo armazenamento persistente de todas as informações.
* **`database.py`**: Configuração da conexão com o banco de dados (ex: PostgreSQL).
* **`repositories.py`**: Abstrai as operações de CRUD (Criar, Ler, Atualizar, Deletar) para os modelos de dados (ChargePoint, User, Transaction).

### **4. Camada de Integração LLM (`llm_integration/`)**
A ponte entre o **LLM (Claude da Anthropic)** e as funcionalidades do CSMS, utilizando o **Model Context Protocol (MCP)**.
* **`mcp_server.py`**: Implementa o servidor HTTP que expõe as **"ferramentas"** (ações) e **"recursos"** (dados) para o LLM, seguindo o protocolo MCP.
* **`mcp_tools.py`**: Contém as funções Python que o LLM pode "chamar" para realizar ações no CSMS (e.g., `start_charging_session`, `send_remote_reset`). Elas interagem com os serviços da `business_logic`.
* **`mcp_resources.py`**: Contém as funções Python que o LLM pode "consultar" para obter dados do CSMS (e.g., `get_charge_point_status`, `list_available_connectors`). Elas interagem com os `repositories` ou serviços do CSMS.
* **`llm_prompts.py`**: Modelos de prompts otimizados para guiar o LLM sobre como usar as ferramentas e recursos de forma eficaz e como formular respostas.
* **Tecnologia**: **Anthropic's MCP SDK** (para o servidor MCP) e **`anthropic`** (para interagir com o modelo Claude).

### **5. Camada de Interfaces Externas (`api/`)**
Exposição de APIs para interação com interfaces de usuário (web/móvel) e outros sistemas.
* **`rest_api.py`**: Implementa uma API RESTful para que front-ends ou outros serviços possam interagir com o CSMS.
* **`schemas.py`**: Define os esquemas de validação de dados para a API REST.
* **Tecnologia**: **`FastAPI`** (para o framework API) e **`uvicorn`** (para o servidor web ASGI).

### **6. Modelos de Dados (`models/`)**
Definições das estruturas de dados principais do sistema.
* **`charge_point.py`**: Modelos para `ChargePoint` e `ChargePointConnector`.
* **`user.py`**: Modelo para `User`.
* **`transaction.py`**: Modelo para `Transaction`.
* **`llm_tool.py`**: Modelos para `LLMToolDefinition` e `LLMResourceDefinition` (para o MCP).
* **Tecnologia**: **`dataclasses`** ou **`Pydantic`** (para validação e serialização).

---

## 📂 Estrutura do Projeto

```
ev_charging_system/
├── core/
│   ├── ocpp_server.py             # Implementação do servidor OCPP (CSMS)
│   ├── ocpp_handlers.py           # Funções que tratam mensagens OCPP recebidas
│   ├── connection_manager.py      # Gerencia as conexões WebSocket com os CPs
│   └── __init__.py
│
├── business_logic/
│   ├── auth_service.py            # Lógica de autenticação e autorização
│   ├── transaction_service.py     # Gerenciamento de sessões de carregamento
│   ├── smart_charging_service.py  # Algoritmos e regras de smart charging
│   ├── device_management_service.py # Gestão de CPs (firmware, configs)
│   ├── reporting_service.py       # Geração de relatórios
│   └── __init__.py
│
├── data/
│   ├── database.py                # Configuração e interface com o banco de dados
│   ├── repositories.py            # Métodos para interagir com os modelos (CRUD)
│   └── __init__.py
│
├── llm_integration/
│   ├── mcp_server.py              # Implementação do Servidor MCP (Anthropic-compatible)
│   ├── mcp_tools.py               # Definição e implementação das funções das "ferramentas" do MCP
│   ├── mcp_resources.py           # Definição e implementação das funções dos "recursos" do MCP
│   ├── llm_prompts.py             # Modelos de prompts para o LLM
│   └── __init__.py
│
├── api/
│   ├── rest_api.py                # API RESTful para interfaces de usuário/integrações
│   ├── schemas.py                 # Esquemas de validação para a API REST
│   └── __init__.py
│
├── models/
│   ├── charge_point.py            # Modelos para ChargePoint e ChargePointConnector
│   ├── user.py                    # Modelo para User
│   ├── transaction.py             # Modelo para Transaction
│   ├── llm_tool.py                # Modelos para LLMToolDefinition e LLMResourceDefinition
│   └── __init__.py
│
├── config/
│   ├── settings.py                # Configurações do projeto (portas, URLs de DB, chaves de API, etc.)
│   └── __init__.py
│
├── tests/                         # Testes unitários e de integração
│   ├── test_ocpp_server.py
│   ├── test_mcp_server.py
│   └── ...
│
├── main.py                        # Ponto de entrada principal da aplicação
├── requirements.txt               # Lista de dependências Python
├── Dockerfile                     # Para conteinerização da aplicação
└── README.md                      # Este arquivo!
```

---

## ⚙️ Como Rodar o Projeto

### **Pré-requisitos**

* Python 3.9+
* Um banco de dados (ex: PostgreSQL)
* Chave de API da Anthropic para acesso ao LLM Claude
* Conhecimento básico de Docker (opcional, para conteinerização)

### **Instalação**

1.  **Clone o repositório:**
    ```bash
    git clone [https://github.com/seu-usuario/ev_charging_system.git](https://github.com/seu-usuario/ev_charging_system.git)
    cd ev_charging_system
    ```
2.  **Crie e ative um ambiente virtual:**
    ```bash
    python -m venv venv
    source venv/bin/activate  # No Windows: `venv\Scripts\activate`
    ```
3.  **Instale as dependências:**
    ```bash
    pip install -r requirements.txt
    ```
4.  **Configure o banco de dados:**
    * Crie um banco de dados e atualize as informações de conexão em `config/settings.py` (ou variáveis de ambiente).
    * Execute as migrações do banco de dados (serão definidas mais tarde).

5.  **Configure as variáveis de ambiente:**
    * Crie um arquivo `.env` na raiz do projeto ou defina as variáveis de ambiente necessárias, incluindo sua chave da Anthropic.
        ```
        ANTHROPIC_API_KEY="sua_chave_aqui"
        DATABASE_URL="postgresql://user:password@host:port/dbname"
        OCPP_SERVER_PORT=9000
        MCP_SERVER_PORT=8000
        FASTAPI_PORT=8001
        ```

### **Execução**

O `main.py` será o ponto de entrada para iniciar todos os serviços:

1.  **Inicie o Servidor OCPP (CSMS), Servidor MCP e a API REST:**
    ```bash
    python main.py
    ```
    Isso deve iniciar os servidores nas portas configuradas (ex: 9000 para OCPP, 8000 para MCP, 8001 para FastAPI).

2.  **Conecte um Charge Point (Simulador ou Real):**
    * Se você tiver um simulador de Charge Point (usando a biblioteca `mobilityhouse/ocpp` para o lado do CP), configure-o para se conectar ao `ws://localhost:9000/CP_ID`.

3.  **Interaja com o LLM (via Claude API):**
    * Sua aplicação cliente (ex: chatbot, painel de controle) que utiliza a API da Anthropic pode agora chamar o LLM Claude, que por sua vez usará o seu Servidor MCP (`http://localhost:8000/`) para acessar as ferramentas e recursos do CSMS.

---

## 🧪 Testes

Para garantir a robustez e segurança do sistema:

* **Testes Unitários:** Use `pytest` para testar funções e módulos isolados.
    ```bash
    pytest tests/unit/
    ```
* **Testes de Integração:** Teste a comunicação entre os módulos (ex: `ocpp_handlers` chamando `business_logic`).
    ```bash
    pytest tests/integration/
    ```
* **Auditoria de Segurança do MCP:** É altamente recomendável usar ferramentas como o `MCPSafetyScanner` (se disponível publicamente para a versão do SDK que você está usando) para identificar vulnerabilidades potenciais no seu Servidor MCP.

---

## 📚 Recursos Adicionais

* **Documentação OCPP:** [openchargealliance.org](https://www.openchargealliance.org/)
* **`mobilityhouse/ocpp` GitHub:** [github.com/mobilityhouse/ocpp](https://github.com/mobilityhouse/ocpp)
* **FastAPI Documentação:** [fastapi.tiangolo.com](https://fastapi.tiangolo.com/)
* **Anthropic's Model Context Protocol (MCP) Artigo:** Consulte a documentação da Anthropic e artigos como "Model Context Protocol (MCP): A Guide With Demo Project" para detalhes sobre a implementação do MCP.
* **`websockets` Documentação:** [websockets.readthedocs.io](https://websockets.readthedocs.io/en/stable/)

---

Este `README.md` oferece uma base sólida para o seu projeto. Lembre-se de atualizá-lo à medida que o projeto evolui e novas funcionalidades são adicionadas!
```#   S I G E C - V E  
 