                                  # SIGEC-VE
# Sistema Inteligente de Gestão de Estações de Carregamento de VE (CSMS) com LLMs

![Diagrama 1](assets/v0.png)
![Diagrama 1](assets/v00.png)
![Diagrama 1](assets/v1.png)
![Diagrama 2](assets/v2.png)


Este projeto propõe uma arquitetura robusta e modular para um **Sistema de Gestão Central de Estações de Carregamento de Veículos Elétricos (CSMS)** que integra **Large Language Models (LLMs)** para funcionalidades avançadas de inteligência e automação. Utiliza o protocolo **OCPP (Open Charge Point Protocol)** para comunicação com os postos de carregamento e o **Model Context Protocol (MCP)** da Anthropic para a orquestração com os LLMs.

OCPP 2.0.1 (Open Charge Point Protocol) - Casos de Uso Implementados:
O OCPP 2.0.1 organiza suas funcionalidades em "blocos funcionais". Os códigos (B, C, E, F, G, J, M, P) geralmente se referem a esses blocos.

Bloco B: Provisioning (Provisionamento)

B01 - B04 (Provisioning): Lida com o processo inicial de conexão e configuração de uma estação de carregamento (Charge Point) com o Sistema de Gerenciamento de Ponto de Carga (CSMS). Isso inclui:
B01: Cold Boot: Ações tomadas quando a estação de carregamento é ligada pela primeira vez ou após uma reinicialização completa.
B02: Authorization after Cold Boot: Como a estação se autentica no CSMS após a inicialização.
B03: Change of Charge Point Configuration: Permite que o CSMS altere configurações da estação remotamente.
B04: Update Firmware: Gerenciamento de atualizações de software/firmware da estação.
B11 - B12 (Provisioning): Estes são casos de uso específicos de provisionamento que foram adaptados ou mantidos do OCPP 1.6 para o 2.0.1. Provavelmente relacionados a funcionalidades básicas de inicialização e registro.
B05 - B07 (Variables - Variáveis): Lida com o gerenciamento de variáveis de configuração e estado na estação de carregamento.
B05: Get Variables: O CSMS solicita o valor de uma ou mais variáveis da estação.
B06: Set Variables: O CSMS define o valor de uma ou mais variáveis na estação.
B07: Get Base Report: A estação envia um relatório completo de suas variáveis e configurações para o CSMS.
Bloco C: Authorization (Autorização)

C01 - C06 (Authorization options - Opções de Autorização): Define os diferentes métodos pelos quais um usuário pode ser autorizado a carregar um VE.
C01: Authorization by IdToken (local/online): Autorização usando um identificador (como um cartão RFID ou aplicativo), que pode ser validado localmente pela estação ou online com o CSMS.
C02: Authorization using Start Button: Autorização iniciada por um botão físico na estação.
C03: Authorization using Credit/Debit Card: Se a estação tiver um leitor de cartão de crédito/débito.
C04: Authorization using Pin-Code: Se a estação tiver um teclado para PIN.
C05: Authorization for CSMS initiated transactions: Autorização quando a sessão de carregamento é iniciada pelo próprio CSMS (ex: para teste ou manutenção).
C06: Authorization using local id type: Autorização através de um meio de identificação local.
C15 (Offline Authorization - Autorização Offline): Permite que uma estação de carregamento continue autorizando usuários mesmo que esteja temporariamente desconectada do CSMS, geralmente usando uma lista de IDs autorizados armazenada localmente.
Bloco E: Transactions (Transações)

E01 - E12 (Transactions): Cobre todas as etapas e o gerenciamento de uma sessão de carregamento de um veículo elétrico.
E01: Start Transaction: Iniciar uma sessão de carregamento.
E02: Stop Transaction: Encerrar uma sessão de carregamento.
E03: Transaction Event Reporting: A estação reporta eventos importantes durante a transação (ex: conectado, carregando, erro).
E04: Charging Profile Management: Gerenciamento dos perfis de carregamento (curvas de potência) que definem como o VE será carregado.
E05: Reservation: Permite que um usuário reserve uma estação de carregamento por um período.
E06: Tariff and Cost Display: Exibição de informações de tarifa e custo no display da estação.
E07: Data Transfer for Transactions: Troca de dados relevantes para a transação.
E08: Transaction Data Logging: Registro de dados da transação.
E09: Transaction Summary: Resumo da transação ao final da sessão.
E10: Transaction Event Notification: Notificações de eventos de transação para o CSMS.
E11: Transaction Authorization Timeout: Lida com timeouts de autorização.
E12: Transaction Status Notification: Notificação do status da transação.
Bloco F: Remote Control (Controle Remoto)

F01 - F03 e F05 - F06 (RemoteControl): Permite que o CSMS controle a estação de carregamento remotamente.
F01: Remote Start Transaction: O CSMS inicia uma sessão de carregamento remotamente.
F02: Remote Stop Transaction: O CSMS encerra uma sessão de carregamento remotamente.
F03: Change EVSE Status: O CSMS altera o status de um ponto de conexão (EVSE) (ex: de disponível para fora de serviço).
F05: Unlock Connector: Desbloqueia o conector de carregamento remotamente.
F06: Reset: Reinicia a estação de carregamento (Hard Reset ou Soft Reset).
Bloco G: Availability (Disponibilidade)

G01 - G04 (Availability): Gerenciamento do status de disponibilidade da estação de carregamento.
G01: Change Availability: O CSMS altera o status de disponibilidade da estação (ex: para "Out of Service" ou "Available").
G02: Status Notification: A estação notifica o CSMS sobre sua própria mudança de status.
G03: Get Local Status: O CSMS solicita o status de disponibilidade local da estação.
G04: Set Display Message: O CSMS pode enviar mensagens para serem exibidas na tela da estação.
Bloco J: Tx-related MeterValues (Valores de Medição Relacionados à Transação)

J02 (Tx-related MeterValues): Foca no envio de dados de medição (como energia consumida em kWh) durante ou após uma transação. A nota "persistency not supported yet" indica que a capacidade de armazenar esses dados de forma persistente na estação por um longo período ainda está em desenvolvimento ou não é uma funcionalidade padrão.
Bloco M: Certificate Management (Gerenciamento de Certificados)

M03 - M05 (Certificate management): Essencial para a segurança, especialmente para funcionalidades como o Plug & Charge (ISO 15118).
M03: Install Certificate: O CSMS instala um certificado digital na estação.
M04: Delete Certificate: O CSMS remove um certificado da estação.
M05: Get Installed Certificate Ids: O CSMS solicita uma lista dos IDs dos certificados instalados na estação.
Note: Enable Mbed-TLS to use the built-in certificate store: Isso sugere que a implementação usa a biblioteca Mbed-TLS para gerenciar o armazenamento interno de certificados, que são cruciais para a comunicação segura.
Bloco P: Data Transfer - Protocol Negotiation (Transferência de Dados - Negociação de Protocolo)

P01 - P02 (Data transfer - Protocol negotiation): Lida com a forma como a estação e o CSMS se comunicam e negociam as capacidades do protocolo.
P01: Data Transfer: Um mecanismo genérico para o CSMS e a estação trocarem mensagens personalizadas ou dados que não se encaixam nos outros casos de uso padrão.
P02: Protocol Negotiation: A capacidade de a estação selecionar a versão do OCPP a ser usada em tempo de execução, permitindo compatibilidade com diferentes versões do CSMS.
ISO 15118 (Road vehicles - Vehicle to grid communication interface)
A ISO 15118 não tem "códigos de caso de uso" como o OCPP, mas sim diferentes partes da norma que cobrem funcionalidades específicas. As principais funcionalidades que ela habilita são:

Plug & Charge (PnC):

Identificação e Autorização Automática: O veículo se identifica e autoriza automaticamente com a estação de carregamento assim que é conectado, sem a necessidade de cartões, aplicativos ou outros meios.
Autenticação Baseada em Certificados Digitais: Usa infraestrutura de chave pública (PKI) para garantir a segurança e a autenticidade da comunicação entre o VE e a estação.
Faturamento Simplificado: Permite que o faturamento da sessão de carregamento seja associado diretamente ao veículo.
Smart Charging (Carregamento Inteligente):

Troca de Informações Bidirecional: O VE e a estação trocam informações detalhadas sobre a capacidade da bateria, estado de carga (SoC), necessidades de energia e preferências do usuário (ex: "carregar até 80% até às 7h da manhã").
Otimização de Carregamento: Permite que a estação de carregamento e/ou o CSMS ajustem a taxa de carregamento com base na disponibilidade da rede elétrica, tarifas de energia e outras condições (ex: carregar mais lentamente durante picos de demanda da rede, ou aproveitar tarifas mais baixas fora de pico).
Gerenciamento de Energia: Integração com sistemas de gerenciamento de energia (EMS) da casa ou do edifício para otimizar o consumo de energia.
Vehicle-to-Grid (V2G) / Vehicle-to-Home (V2H) / Vehicle-to-Load (V2L):

Fluxo de Energia Bidirecional: Habilita a capacidade de um VE não apenas consumir energia da rede (carregar), mas também fornecer energia de volta à rede (descarregar) ou para uma residência/carga específica. Isso transforma o VE em um ativo de armazenamento de energia.
Serviços de Rede: Permite que VEs participem de serviços de estabilização da rede elétrica, como regulação de frequência ou balanceamento de carga.
Segurança Aprimorada:

Criptografia de Ponta a Ponta (TLS): Garante que a comunicação entre o VE e a estação seja criptografada e segura, protegendo dados sensíveis.
Assinaturas Digitais: Garante a integridade e a autenticidade das mensagens trocadas.
Conveniência para o Usuário:

Simplifica a experiência de carregamento, tornando-a mais automática e sem atritos.

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
![Diagrama da Arquitetura do SIGEC-VE](assets/arquitetura.png)
ev_charging_system/

├── core/

│   ├── ocpp_server.py             # Implementação do servidor OCPP (CSMS)

│   ├── ocpp_handlers.py           # Funções que tratam mensagens OCPP recebidas

│   ├── connection_manager.py      # Gerencia as conexões WebSocket com os CPs

│   └── init.py
│

├── business_logic/

│   ├── auth_service.py            # Lógica de autenticação e autorização

│   ├── transaction_service.py     # Gerenciamento de sessões de carregamento

│   ├── smart_charging_service.py  # Algoritmos e regras de smart charging

│   ├── device_management_service.py # Gestão de CPs (firmware, configs)

│   ├── reporting_service.py       # Geração de relatórios

│   └── init.py
│

├── data/

│   ├── database.py                # Configuração e interface com o banco de dados

│   ├── repositories.py            # Métodos para interagir com os modelos (CRUD)

│   └── init.py
│

├── llm_integration/

│   ├── mcp_server.py              # Implementação do Servidor MCP (Anthropic-compatible)

│   ├── mcp_tools.py               # Definição e implementação das funções das "ferramentas" do MCP

│   ├── mcp_resources.py           # Definição e implementação das funções dos "recursos" do MCP

│   ├── llm_prompts.py             # Modelos de prompts para o LLM

│   └── init.py
│
├── api/

│   ├── rest_api.py                # API RESTful para interfaces de usuário/integrações

│   ├── schemas.py                 # Esquemas de validação para a API REST

│   └── init.py
│

├── models/

│   ├── charge_point.py            # Modelos para ChargePoint e ChargePointConnector

│   ├── user.py                    # Modelo para User

│   ├── transaction.py             # Modelo para Transaction

│   ├── llm_tool.py                # Modelos para LLMToolDefinition e LLMResourceDefinition

│   └── init.py
│

├── config/
│   ├── settings.py                # Configurações do projeto (portas, URLs de DB, chaves de API, etc.)

│   └── init.py
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

Em resumo:

mcp_tools.py e mcp_resources.py: Atuam como a interface do MCP, descrevendo o que o LLM pode fazer/saber.
device_management_service.py (e outros serviços em business_logic/): Contêm a lógica de negócio principal que executa as ações e recupera os dados.
ocpp_server.py / ocpp_handlers.py: Serão chamados pelos serviços de lógica de negócio para enviar mensagens OCPP aos postos de carregamento, se a ferramenta exigir interação direta com o CP.
repositories.py / database.py: Interagem com o banco de dados para armazenar e buscar dados.

Ferramentas (Tools) - Definidas em mcp_tools.py
Estas são as ações que o LLM pode executar no seu Sistema de Gestão de Estações de Carregamento:

POST /reset_charge_point
Descrição: Solicita o reset remoto de um Charge Point.
POST /update_charge_point_configuration
Descrição: Atualiza a configuração de um Charge Point (e.g., HeartbeatInterval).
POST /start_ocpp_transaction
Descrição: Inicia remotamente uma transação de carregamento OCPP em um conector específico.
POST /stop_ocpp_transaction
Descrição: Para remotamente uma transação de carregamento OCPP em andamento.
POST /set_connector_status
Descrição: Altera o status operacional de um conector (e.g., "Available", "Unavailable", "Faulted").
Recursos (Resources) - Definidos em mcp_resources.py
Estes são os dados e informações que o LLM pode consultar do seu Sistema de Gestão de Estações de Carregamento:

GET /get_charge_point_status/{charge_point_id}
Descrição: Obtém o status atual e detalhes de um Charge Point específico, incluindo o status de seus conectores.
GET /list_charge_points
Descrição: Lista todos os Charge Points registrados, com a opção de filtrar por status geral do CP.
GET /list_connectors_by_status
Descrição: Lista conectores que possuem um status específico (e.g., "Available", "Charging", "Faulted").
GET /get_transaction_details/{transaction_id}
Descrição: Obtém detalhes de uma transação específica (lógica de busca a ser implementada).
---