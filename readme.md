# Celesc RPA Crawler ⚡

Um script de automação (RPA) robusto desenvolvido em Python e Playwright para realizar o login e o download em lote de faturas de energia (PDFs) diretamente da Agência Virtual da Celesc (Conecte Celesc).

## 🚀 Funcionalidades

* **Login Automatizado e Validação via API:** Intercepta o retorno da requisição de login para validar credenciais instantaneamente, sem depender de tempos de carregamento de tela.
* **Suporte a Múltiplos Perfis (Grupo A e B):** O script mapeia a conta do usuário interceptando o JSON da API GraphQL (`findOneUserProfile`), permitindo a navegação inteligente em contas corporativas com múltiplos parceiros de negócio e filiais.
* **Download Inteligente:** Verifica o status da fatura (Paga ou Em Aberto) e executa os cliques corretos para cada cenário.
* **Padronização de Nomes:** Salva os arquivos automaticamente no formato `Fatura_{UC}_{Mes}_{Data}.pdf`.
* **Resiliência (Retry Pattern):** Sistema de tentativas automáticas (até 3 vezes) para contornar lentidão no servidor da concessionária durante a geração dos PDFs.
* **Tratamento de Popups e SPAs:** Lida com modais promocionais ("Simplifique sua vida") e respeita o ciclo de vida do framework Angular (Virtual Scrolling e Network Idle).

## 🛠️ Tecnologias Utilizadas

* [Python 3](https://www.python.org/)
* [Playwright (Sync API)](https://playwright.dev/python/) - Automação web e interceptação de rede.
* Expressões Regulares (`re`) - Extração e formatação de datas.

## ⚙️ Instalação

1. Clone este repositório:
   ```bash
   git clone https://github.com/gfooky/celesc_crawler.git
   cd celesc_crawler
   ```

2. Instale o Playwright:
   ```bash
   pip install playwright
   playwright install chromium
   ```

## 💻 Como usar

O script funciona via linha de comando (CLI), exigindo 3 argumentos: E-mail, Senha e Unidade Consumidora (UC).

```bash
python main.py seu_email@dominio.com sua_senha_aqui 12345678
```
*(Nota: Se a sua senha contiver caracteres especiais, coloque-a entre aspas: `"Senha*123"`).*

## ⚠️ Aviso Legal
Este é um projeto com fins educacionais para demonstrar técnicas de Web Scraping e RPA. Não me responsabilizo pelo uso indevido da ferramenta. Evite sobrecarregar os servidores da instituição com requisições massivas.