# Coisas que **só você** pode fazer

Tudo que dependia de código, configuração, relatório e estrutura já está
feito. Estas tarefas precisam de **interação humana** (login em sites,
gravação de vídeo, gerar prints) ou de credenciais pessoais que **eu
não devo criar por você**.

> Marque cada item à medida que concluir.

---

## 1. Criar o repositório no GitHub (conta `luanbrant212004@gmail.com`)

A CLI `gh` neste computador está logada com outra conta
(`luan-brant_awsales`). Para subir o projeto **na sua conta pessoal**
(email `luanbrant212004@gmail.com`) você tem duas opções:

### Opção A – via navegador (mais rápido)
1. Logado em <https://github.com> com a conta `luanbrant212004@gmail.com`.
2. **New repository** → nome sugerido: `CardioIA-Fase3` → **Public** → **Create**.
3. Copie a URL HTTPS / SSH que o GitHub mostrar.
4. No terminal, dentro de `CardioIA-Fase3/`:
   ```bash
   git remote add origin git@github.com:<seu-user>/CardioIA-Fase3.git
   git push -u origin main
   ```

### Opção B – via `gh` (autenticar a conta pessoal)
```bash
gh auth login   # escolha "github.com", "HTTPS", "Login with a web browser"
                # autentique com o email luanbrant212004@gmail.com
gh repo create CardioIA-Fase3 --public --source=. --remote=origin --push
```

⚠️ O git do repositório local **já está com o email correto**
(`luanbrant212004@gmail.com` no `git config user.email` global), então
os commits aparecerão atribuídos a você.

---

## 2. Parte 1 – Wokwi link público

1. Abra <https://wokwi.com/projects/new/esp32> (logado no Wokwi).
2. **Code** → cole o conteúdo de
   [`parte1-edge-computing/sketch.ino`](parte1-edge-computing/sketch.ino).
3. **diagram.json** → cole o conteúdo de
   [`parte1-edge-computing/diagram.json`](parte1-edge-computing/diagram.json).
4. **libraries.txt** → cole o conteúdo de
   [`parte1-edge-computing/libraries.txt`](parte1-edge-computing/libraries.txt).
5. **Save**. O Wokwi gera uma URL pública — cole em
   `parte1-edge-computing/README.md` no campo "Link Wokwi".

## 3. Parte 2 – Wokwi link público + prints

1. Repita os passos acima para `parte2-fog-cloud-mqtt/`. Lembre-se: o
   MQTT precisa de internet → o Wokwi-GUEST já vem configurado no
   código.
2. Salve e adicione a URL pública ao
   [`parte2-fog-cloud-mqtt/README.md`](parte2-fog-cloud-mqtt/README.md).
3. **Prints obrigatórios** (salve em `docs/images/`):
   - `wokwi-running.png` — simulador rodando com Serial Monitor mostrando
     `[MQTT] OK` e linhas `[MQTT-TX] ... telemetry ...`.
   - `node-red-flow.png` — flow do Node-RED no editor.
   - `node-red-dashboard.png` — dashboard `/ui` recebendo dados.
   - (Opcional) `mqtt-explorer.png` — MQTT Explorer assinando
     `cardioia/#`.

### Node-RED – instalação rápida
```bash
npm install -g --unsafe-perm node-red node-red-dashboard
node-red                                 # abre em http://127.0.0.1:1880
# Menu (☰) → Import → cole node-red-flow.json → Deploy
# Dashboard em http://127.0.0.1:1880/ui
```

## 4. Ir Além 1 – Email real (opcional)

O `email_alert.py` opera em **dry-run** sem credenciais (imprime o email
no console — ótimo para a apresentação). Se quiser enviar **e-mail
real**:

1. Em <https://myaccount.google.com/apppasswords> gere uma **App
   Password** (precisa ter 2FA ativo).
2. `cd ir-alem-1-rest-email && cp .env.example .env`
3. Edite `.env` com seu SMTP do Gmail.
4. `uvicorn api_server:app --reload`
5. `python api_client.py --crisis` → o e-mail será enviado de verdade.

## 5. Entrega final FIAP

1. Faça **commit + push** de eventuais alterações (links Wokwi, prints).
2. Anexe a URL do repositório GitHub na atividade da plataforma FIAP,
   junto com:
   - Link Wokwi (Parte 1)
   - Link Wokwi (Parte 2)

> O vídeo do "Ir Além 2" não será entregue – toda a análise está no
> [`RELATORIO.md`](ir-alem-2-ia-series-temporais/RELATORIO.md) e no
> notebook executável `cardioia_timeseries.ipynb`.

Pronto. Boa nota.
