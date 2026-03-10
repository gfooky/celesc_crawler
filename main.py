import re
import sys
import json
from playwright.sync_api import sync_playwright

def baixar_faturas_celesc(email, senha, unidade_desejada):
    # Dicionário global para armazenar os JSONs capturados em background
    dados_globais = {
        "perfil": [], 
        "contratos_iniciais": []
    }

    def interceptador_graphql(response):
        """ Captura os JSONs vitais enquanto o robô navega """
        if "graphql" in response.url and response.request.method == "POST":
            try:
                payload = response.request.post_data or ""
                if "findOneUserProfile" in payload:
                    body = response.json()
                    categorias = body.get("data", {}).get("findOneUserProfile", {}).get("categories", [])
                    if categorias:
                        dados_globais["perfil"].extend(categorias)
                        
                elif "allContracts" in payload:
                    body = response.json()
                    contratos = body.get("data", {}).get("allContracts", {}).get("contracts", [])
                    if contratos:
                        dados_globais["contratos_iniciais"].extend(contratos)
            except Exception:
                pass

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context()
        page = context.new_page()

        # Ativa o listener para capturar os JSONs de forma assíncrona
        page.on("response", interceptador_graphql)

        print("Acessando a página da Celesc...")
        page.goto("https://conecte.celesc.com.br/autenticacao/login")

        try:
            page.click('text="Já tenho o novo cadastro"', timeout=5000)
        except Exception:
            pass

        print("Preenchendo credenciais...")
        page.wait_for_timeout(1000)
        page.fill('input[type="email"]', email)
        page.fill('input[type="password"]', senha)

        # ---------------------------------------------------------
        # PASSO 1: Login e Validação via JSON
        # ---------------------------------------------------------
        print("Enviando requisição de login...")
        with page.expect_response(lambda response: "auth/login" in response.url and response.request.method == "POST") as response_info:
            page.click('button:has-text("Entrar")')
        
        try:
            login_json = response_info.value.json()
            auth_data = login_json.get("data", {}).get("authenticate", {})
            if auth_data.get("message") == "Login efetuado com sucesso!" or "login" in auth_data:
                nome_usuario = auth_data.get("profile", {}).get("givenName", "Usuário")
                print(f"[API] Login bem-sucedido! Bem-vindo(a), {nome_usuario}.")
            else:
                erro_msg = auth_data.get("message", "Credenciais incorretas!")
                print(f"[ERRO API] Falha no login: {erro_msg}")
                sys.exit(1)
        except Exception:
            print("[ERRO API] Erro ao analisar login.")
            sys.exit(1)

        # ---------------------------------------------------------
        # PASSO 2: Verificação da URL
        # ---------------------------------------------------------
        print("Aguardando o roteamento do sistema...")
        try:
            page.wait_for_url(re.compile(r"/autenticacao/selecao-acesso|/contrato/selecao"), timeout=15000)
        except Exception:
            pass
            
        page.wait_for_timeout(3000) # Tempo para o listener processar os JSONs iniciais
        url_atual = page.url
        uc_encontrada = False

        # ---------------------------------------------------------
        # PASSO 3A: Lógica para Múltiplos Perfis (selecao-acesso)
        # ---------------------------------------------------------
        if "selecao-acesso" in url_atual:
            num_parceiros = len(dados_globais['perfil'])
            print(f"[INFO] Tela de seleção intermediária. Lendo JSON: {num_parceiros} parceiros mapeados.")

            if num_parceiros == 0:
                print("[ERRO] JSON de perfis vazio. Não é possível prosseguir.")
                sys.exit(1)

            # Separa os parceiros pelos grupos definidos no JSON
            parceiros_grpa = [p for p in dados_globais["perfil"] if p.get("categoryId") == "GRPA"]
            parceiros_grpb = [p for p in dados_globais["perfil"] if p.get("categoryId") == "GRPB"]

            # Estrutura com os SEUS locadores exatos
            grupos_para_verificar = []
            if parceiros_grpa:
                grupos_para_verificar.append((
                    "Grupo A",
                    page.locator("celesc-profile-card").filter(has_text="work_outline Grupo A Perfil").get_by_role("button"),
                    parceiros_grpa
                ))
            if parceiros_grpb:
                grupos_para_verificar.append((
                    "Para você e seu negócio",
                    page.locator("celesc-profile-card").filter(has_text="person_outline Para você e").get_by_role("button"),
                    parceiros_grpb
                ))

            # Itera sobre os Menus
            for nome_grupo, btn_grupo, parceiros in grupos_para_verificar:
                if uc_encontrada: break
                print(f"\n--- Abrindo o menu '{nome_grupo}' ---")

                # Itera sobre os parceiros do menu
                for parceiro in parceiros:
                    if uc_encontrada: break

                    num_parceiro = parceiro.get("partnerNumber")
                    nome_parceiro = parceiro.get("partnerName")
                    print(f"  -> Acessando parceiro: {num_parceiro} - {nome_parceiro}")

                    # Se a gente testou um parceiro e a URL mudou para /contrato/selecao, 
                    # voltamos para a raiz para testar o próximo
                    if "selecao-acesso" not in page.url:
                        page.goto("https://conecte.celesc.com.br/autenticacao/selecao-acesso")
                        page.wait_for_timeout(2000)

                    # Clica no botão do Grupo (A ou B) se ele estiver recolhido
                    if btn_grupo.is_visible():
                        btn_grupo.click()
                        page.wait_for_timeout(1500)

                    # Localiza o botão "Selecionar" daquele parceiro específico
                    caixa_parceiro = page.locator("div").filter(has_text=num_parceiro).filter(has=page.get_by_role("button", name="Selecionar")).last

                    # Rola a tela (Virtual Scrolling) até o parceiro aparecer
                    tentativas = 0
                    while not caixa_parceiro.is_visible() and tentativas < 5:
                        page.mouse.wheel(0, 1000)
                        page.wait_for_timeout(500)
                        tentativas += 1

                    if not caixa_parceiro.is_visible():
                        print(f"     [AVISO] Parceiro {num_parceiro} não apareceu na tela.")
                        continue

                    # Clica no parceiro e INTERCEPTA o json allContracts daquele momento
                    with page.expect_response(lambda r: "graphql" in r.url and "allContracts" in (r.request.post_data or ""), timeout=15000) as resp:
                        caixa_parceiro.get_by_role("button", name="Selecionar").click()

                    try:
                        page.wait_for_url("**/contrato/selecao", timeout=15000)
                    except Exception:
                        pass
                    page.wait_for_timeout(2000)

                    # Verifica o JSON que acabou de ser baixado!
                    try:
                        json_contratos = resp.value.json()
                        dados_contratos = json_contratos.get("data", {}).get("allContracts", {}).get("contracts", [])
                        if dados_contratos is None: dados_contratos = []

                        if any(c.get('installation') == unidade_desejada for c in dados_contratos):
                            print(f"     [OK] SUCESSO! UC {unidade_desejada} encontrada aqui.")
                            uc_encontrada = True
                            break
                        else:
                            print(f"     [X] UC não encontrada neste parceiro.")
                    except Exception as e:
                        print(f"     [ERRO] Falha ao processar allContracts: {e}")

        # ---------------------------------------------------------
        # PASSO 3B: Lógica para Conta Simples (contrato/selecao)
        # ---------------------------------------------------------
        elif "contrato/selecao" in url_atual:
            print("[INFO] Tela direta de contratos. Verificando JSON allContracts inicial...")
            
            if any(c.get('installation') == unidade_desejada for c in dados_globais["contratos_iniciais"]):
                print(f"[OK] SUCESSO! UC {unidade_desejada} encontrada no JSON inicial.")
                uc_encontrada = True

        # Se terminamos tudo e não achou
        if not uc_encontrada:
            print(f"\n[ERRO FATAL] A UC '{unidade_desejada}' não existe nesta conta.")
            sys.exit(1)

        # ---------------------------------------------------------
        # PASSO 4: Abertura da Unidade Consumidora e Download
        # ---------------------------------------------------------
        print(f"\nAcessando o painel da UC {unidade_desejada}...")
        caixa_alvo = page.locator("div").filter(has_text=unidade_desejada).filter(has=page.get_by_role("button", name="Selecionar unidade")).last
        caixa_alvo.scroll_into_view_if_needed()
        caixa_alvo.get_by_role("button", name="Selecionar unidade").last.click()

        print("Aguardando o sistema registrar a sessão e carregando o painel...")
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(3000) # Um segundo extra por causa daquele "loader" que vimos no log

        # ---------------------------------------------------------
        # NOVO: Tratamento do Popup de Fatura Digital
        # ---------------------------------------------------------
        try:
            # Procura pelo texto exato na tela
            botao_agora_nao = page.get_by_text("Agora não", exact=True)
            
            # Espera até 5 segundos para ver se o popup dá as caras
            if botao_agora_nao.is_visible(timeout=5000):
                print("[INFO] Popup 'Simplifique sua vida' detectado na tela. Fechando...")
                botao_agora_nao.click()
                page.wait_for_timeout(1000) # Pausa rápida para a animação do popup sumir
        except Exception:
            # Se der timeout e o botão não aparecer, ele ignora silenciosamente e segue a vida
            pass
        # ---------------------------------------------------------

        print("Acessando o Histórico de Faturas via menu...")
        page.get_by_role("button", name=re.compile("Histórico de faturas", re.IGNORECASE)).first.click()
        page.wait_for_selector("ui-celesc-table-row", timeout=15000)

        linhas_faturas = page.locator("ui-celesc-table-row").all()
        quantidade = len(linhas_faturas)

        # ---------------------------------------------------------
        # Loop de Download (Com sistema de tentativas / Retry)
        # ---------------------------------------------------------
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
                    print("  -> Fatura em aberto. Abrindo opções...")
                    botao_pagar.click()
                    page.wait_for_timeout(1000)

                    # Tenta baixar até 3 vezes
                    sucesso = False
                    for tentativa in range(3):
                        try:
                            # Reduzimos o timeout para 15 segundos por tentativa
                            with page.expect_download(timeout=15000) as informacoes_download:
                                page.get_by_role("button", name="receipt Gerar 2ª via").click(force=True)

                            download = informacoes_download.value
                            download.save_as(nome_arquivo)
                            print(f"  -> Salvo: {nome_arquivo}")
                            sucesso = True
                            break # Deu certo, sai do loop de tentativas
                        except Exception:
                            print(f"  [AVISO] Servidor demorou ou falhou. Tentativa {tentativa + 2} de 3...")
                            page.wait_for_timeout(2000) # Pausa antes de tentar clicar de novo
                            
                    if not sucesso:
                        print(f"  [ERRO] Pulando a fatura de {mes} após 3 tentativas falhas.")

                    page.keyboard.press("Escape")
                    page.mouse.click(10, 10)
                    page.wait_for_timeout(1000)

                else:
                    print("  -> Fatura paga. Baixando direto...")
                    
                    # Tenta baixar até 3 vezes
                    sucesso = False
                    for tentativa in range(3):
                        try:
                            with page.expect_download(timeout=15000) as informacoes_download:
                                linha_alvo.get_by_role("button", name=re.compile("Gerar 2ª via", re.IGNORECASE)).click(force=True)

                            download = informacoes_download.value
                            download.save_as(nome_arquivo)
                            print(f"  -> Salvo: {nome_arquivo}")
                            sucesso = True
                            break # Deu certo, sai do loop de tentativas
                        except Exception:
                            print(f"  [AVISO] Servidor demorou ou falhou. Tentativa {tentativa + 2} de 3...")
                            page.wait_for_timeout(2000) # Pausa antes de tentar clicar de novo

                    if not sucesso:
                        print(f"  [ERRO] Pulando a fatura de {mes} após 3 tentativas falhas.")

                page.wait_for_timeout(1000)

            print("\n*** TODOS OS DOWNLOADS CONCLUÍDOS COM SUCESSO! ***")

        else:
            print("Nenhuma fatura encontrada para baixar.")

        browser.close()

if __name__ == "__main__":
    if len(sys.argv) != 4:
        print("Erro: Quantidade incorreta de argumentos.")
        print("Uso correto: python main.py <email> <senha> <UC>")
        sys.exit(1)

    arg_email = sys.argv[1]
    arg_senha = sys.argv[2]
    arg_uc = sys.argv[3]

    baixar_faturas_celesc(arg_email, arg_senha, arg_uc)