import re
import sys
from playwright.sync_api import sync_playwright

def baixar_faturas_celesc(email, senha, unidade_desejada):
    with sync_playwright() as p:
        # headless=True executa sem abrir a janela do navegador
        browser = p.chromium.launch(headless=True) 
        context = browser.new_context()
        page = context.new_page()

        print("Acessando a página da Celesc...")
        page.goto("https://conecte.celesc.com.br/autenticacao/login")

        # 1. Trata o aviso de novo cadastro
        try:
            page.click('text="Já tenho o novo cadastro"', timeout=5000)
        except Exception:
            pass

        # 2. Login
        print("Preenchendo credenciais...")
        page.wait_for_timeout(1000) 
        page.fill('input[type="email"]', email)
        page.fill('input[type="password"]', senha)
        page.click('button:has-text("Entrar")')

        # 3. Seleção de Unidade Consumidora
        print("Aguardando a tela de seleção de contratos...")
        page.wait_for_url("https://conecte.celesc.com.br/contrato/selecao", timeout=15000)
        page.wait_for_timeout(2000)

        print(f"Buscando a unidade: {unidade_desejada}...")
        caixa_da_unidade = (
            page.locator("div")
            .filter(has_text=unidade_desejada)
            .filter(has=page.get_by_role("button", name="Selecionar unidade"))
            .last
        )
        caixa_da_unidade.get_by_role("button", name="Selecionar unidade").click()
        print(f"Entrou na unidade {unidade_desejada} com sucesso!")

        # 4. Acesso ao Histórico
        print("Navegando direto para o Histórico...")
        page.goto("https://conecte.celesc.com.br/fatura/historico")
        page.wait_for_selector("ui-celesc-table-row", timeout=15000)
        
        linhas_faturas = page.locator("ui-celesc-table-row").all()
        quantidade = len(linhas_faturas)
        
        # 5. Loop de Download
        if quantidade > 0:
            print(f"\nIniciando o download de {quantidade} faturas...")

            for i in range(quantidade):
                linha_alvo = page.locator("ui-celesc-table-row").nth(i)
                texto_linha = linha_alvo.inner_text()

                mes = texto_linha.split()[0]
                match_data = re.search(r"Vencimento: (\d{2}/\d{2}/\d{4})", texto_linha)
                data_vencimento = match_data.group(1).replace("/", "-") if match_data else "DataDesconhecida"

                nome_arquivo = f"./Fatura_{unidade_desejada}_{mes}_{data_vencimento}.pdf"
                print(f"[{i+1}/{quantidade}] Baixando {mes} (Venc: {data_vencimento})...")

                botao_pagar = linha_alvo.get_by_role("button", name="Pagar")
                
                if botao_pagar.is_visible():
                    botao_pagar.click()
                    page.wait_for_timeout(1000) 

                    with page.expect_download() as informacoes_download:
                        page.get_by_role("button", name="receipt Gerar 2ª via").click()
                    
                    download = informacoes_download.value
                    download.save_as(nome_arquivo)
                    print(f"  -> Salvo: {nome_arquivo}")

                    page.keyboard.press("Escape")
                    page.wait_for_timeout(1000)

                else:
                    with page.expect_download() as informacoes_download:
                        linha_alvo.get_by_role("button", name=re.compile("Gerar 2ª via", re.IGNORECASE)).click()
                    
                    download = informacoes_download.value
                    download.save_as(nome_arquivo)
                    print(f"  -> Salvo: {nome_arquivo}")

                page.wait_for_timeout(1000)

            print("\n*** TODOS OS DOWNLOADS CONCLUÍDOS COM SUCESSO! ***")

        else:
            print("Nenhuma fatura encontrada para baixar.")

        browser.close()

# ---------------------------------------------------------
# BLOCO DE EXECUÇÃO
# ---------------------------------------------------------
if __name__ == "__main__":
    # sys.argv[0] é sempre o nome do próprio script (ex: main.py)
    # Por isso precisamos garantir que o usuário passou mais 3 argumentos
    if len(sys.argv) != 4:
        print("Erro: Quantidade incorreta de argumentos.")
        print("Uso correto: python main.py <email> <senha> <UC>")
        sys.exit(1) # Encerra o script com código de erro

    # Captura os argumentos
    arg_email = sys.argv[1]
    arg_senha = sys.argv[2]
    arg_uc = sys.argv[3]

    # Inicia a automação
    baixar_faturas_celesc(arg_email, arg_senha, arg_uc)