# Celesc RPA Crawler ⚡

Um script de automação (RPA) robusto desenvolvido em Python e Playwright para realizar o login e o download em lote de faturas de energia (PDFs) diretamente da Agência Virtual da Celesc (Conecte Celesc).

---

## 🚀 Funcionalidades

- **Login automatizado e validação via API:** Intercepta o retorno da requisição de login para validar credenciais instantaneamente, sem depender de tempos de carregamento de tela.
- **Suporte a múltiplos perfis (Grupo A, Grupo B e Imobiliária):** O script mapeia a conta interceptando o JSON da API GraphQL (`findOneUserProfile`), permitindo navegação inteligente em contas corporativas com múltiplos parceiros de negócio e filiais.
- **Detector de pulo de tela (auto-load):** Quando um perfil possui apenas um parceiro, a Celesc pula a tela de seleção e carrega as UCs diretamente. O script detecta esse comportamento automaticamente e segue o fluxo sem falhas.
- **Download inteligente:** Verifica o status de cada fatura (Paga ou Em Aberto) e executa os cliques corretos para cada cenário.
- **Freio de 6 meses:** Por padrão, o script baixa apenas as últimas 6 faturas do histórico, evitando requisições desnecessárias ao servidor.
- **Padronização de nomes:** Salva os arquivos automaticamente no formato `Fatura_{UC}_{Mes}_{Data}.pdf`.
- **Resiliência (Retry Pattern):** Sistema de tentativas automáticas (até 3 vezes) para contornar lentidão no servidor durante a geração dos PDFs.
- **Tolerância a falhas de paginação:** O loop de download é protegido por `try/except`, garantindo que as faturas já baixadas sejam salvas mesmo que o Angular esconda linhas via virtual scrolling.
- **Reutilizável como módulo:** A função principal `baixar_faturas_celesc()` lança `ValueError` em vez de encerrar o processo com `sys.exit()`, permitindo que seja importada e chamada por interfaces externas (GUI, API, etc.).
- **Tratamento de popups e SPAs:** Lida com modais promocionais ("Simplifique sua vida") e respeita o ciclo de vida do framework Angular (Virtual Scrolling e Network Idle).

---

## 🛠️ Tecnologias utilizadas

- [Python 3](https://www.python.org/)
- [Playwright (Sync API)](https://playwright.dev/python/) — Automação web e interceptação de rede.
- Expressões Regulares (`re`) — Extração e formatação de datas.

---

## ⚙️ Instalação

1. Clone este repositório:

```bash
git clone https://github.com/gfooky/celesc_crawler.git
cd celesc_crawler
```

2. Instale as dependências:

```bash
pip install playwright
playwright install chromium
```

---

## 💻 Como usar

### Via linha de comando (CLI)

O script aceita 3 argumentos: e-mail, senha e Unidade Consumidora (UC).

```bash
python main.py seu_email@dominio.com sua_senha_aqui 12345678
```

> Se a sua senha contiver caracteres especiais, coloque-a entre aspas: `"Senha*123"`.

### Como módulo Python

A função principal pode ser importada e integrada a outros projetos. Ela aceita dois callbacks opcionais para acompanhar o progresso em tempo real.

```python
from main import baixar_faturas_celesc

def ao_encontrar(mes, vencimento):
    print(f"Fatura encontrada: {mes} | Venc: {vencimento}")

def ao_baixar(mes, sucesso):
    status = "OK" if sucesso else "FALHOU"
    print(f"Download {mes}: {status}")

baixar_faturas_celesc(
    email="seu_email@dominio.com",
    senha="sua_senha",
    unidade_desejada="12345678",
    on_fatura_encontrada=ao_encontrar,
    on_fatura_baixada=ao_baixar
)
```

Em caso de erro (credenciais inválidas, UC não encontrada, etc.), a função lança um `ValueError` com a mensagem descritiva.

---

## ⚠️ Aviso legal

Este é um projeto com fins educacionais para demonstrar técnicas de Web Scraping e RPA. Não me responsabilizo pelo uso indevido da ferramenta. Evite sobrecarregar os servidores da instituição com requisições massivas.