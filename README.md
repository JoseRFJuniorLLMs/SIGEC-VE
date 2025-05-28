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