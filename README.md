# Edge Security

Plataforma experimental de **monitoramento passivo de rede e administração DNS**, executada em Docker Compose. Integra **Suricata** (IDS), **Pi-hole v6** (filtragem DNS), **FastAPI** (API e regras), **PostgreSQL** (persistência), **collector Python** (eventos EVE JSON) e **Next.js** (painel administrativo).

> **Estado:** MVP 0.8 (laboratório). Os testes Python foram executados, mas o build Next.js e a integração completa com Pi-hole em Docker **não foram homologados**. Não exponha o painel à internet nem use as políticas em uma rede de produção antes de validar o ambiente.

## Funcionalidades

- Captura **passiva** com Suricata a partir de PCAP, incluindo alertas e eventos DNS/fluxos quando disponíveis.
- Ingestão incremental de `eve.json`, normalização e persistência no PostgreSQL.
- Consultas de eventos, dispositivos observados, alertas, métricas e saúde da coleta.
- Administração visual própria de políticas DNS, clientes e grupos do Pi-hole.
- Publicação manual de regras compatíveis, visualização de divergências e reconciliação de grupos sob confirmação.
- Login de **um único administrador**, sessões persistentes com cookie `HttpOnly` e logout revogável.
- Histórico de reconciliações com snapshots e rollback condicionado ao estado remoto.

**Importante:** Suricata opera somente como IDS e **não bloqueia pacotes**. Bloqueio DNS é responsabilidade do Pi-hole, apenas para clientes que de fato o utilizarem como resolvedor. `deny` nas políticas locais de observação não significa, por si só, bloqueio ativo.

## Arquitetura

```text
PCAP autorizado -> Suricata -> logs/eve.json -> Python Collector -> PostgreSQL
                                                    ^                  |
                                                    |                  v
                                                FastAPI <---------- Next.js
                                                    |
                                                    v
                                            Pi-hole v6 (API/DNS)
```

O Pi-hole é acessado pela API dentro da rede Docker. As portas publicadas para o host são limitadas a `127.0.0.1`.

## Pré-requisitos

- Docker Engine + Docker Compose v2 (ou Docker Desktop).
- Python 3 para gerar eventos sintéticos (opcional).
- `dig` para consultas DNS de teste (opcional).

## Inicialização

```bash
cp .env.example .env
mkdir -p logs captures
```

Edite `.env` e substitua os valores de exemplo por **senhas e chaves longas, diferentes e aleatórias**:

| Variável | Finalidade |
| --- | --- |
| `POSTGRES_PASSWORD` | Senha do banco |
| `API_KEY` | Chave interna de acesso à API |
| `PIHOLE_PASSWORD` | Senha da API administrativa do Pi-hole |
| `ADMIN_USER` | Usuário único do painel |
| `ADMIN_PASSWORD` | Senha do administrador (mínimo de 16 caracteres) |
| `SESSION_COOKIE_SECURE` | `false` apenas no laboratório HTTP local; `true` com HTTPS |
| `SENSOR_ID` | Identificador lógico do sensor |

**Nunca faça commit do `.env`.**

Para gerar tráfego simulado e iniciar o ambiente:

```bash
python3 scripts/seed_eve.py
docker compose up --build -d
docker compose ps
```

O serviço `migrate` executa as migrações Alembic e encerra normalmente. A inicialização preserva os volumes existentes; **não execute `docker compose down -v` ao atualizar**.

### Endereços locais

| Serviço | URL |
| --- | --- |
| Login do dashboard | http://127.0.0.1:3000/login |
| Administração DNS | http://127.0.0.1:3000/dns |
| Histórico | http://127.0.0.1:3000/history |
| OpenAPI FastAPI | http://127.0.0.1:8000/docs |
| DNS de teste Pi-hole | `127.0.0.1:5353` TCP/UDP |

O Pi-hole **não** é automaticamente definido como DNS da LAN ou do host.

## Testando DNS e Suricata

Consulta pontual ao Pi-hole (sem mudar a configuração DNS da máquina):

```bash
dig @127.0.0.1 -p 5353 example.org
```

Para processar um PCAP autorizado, coloque-o em `captures/test.pcap`:

```bash
docker compose --profile pcap run --rm suricata
docker compose logs --tail=100 collector
```

Os arquivos EVE do Suricata ficam em `logs/`. O gerador `scripts/seed_eve.py` produz **dados fictícios** e não representa detecções reais na rede.

## Políticas DNS e rollback

1. Cadastre domínios e configure os grupos desejados no painel `/dns`.
2. Revise a política e publique explicitamente as regras suportadas pelo Pi-hole.
3. Use a prévia de reconciliação para identificar diferenças entre os grupos locais desejados e o estado remoto.
4. Confirme a alteração apenas após revisar a prévia. Se o estado remoto mudar, a aplicação deve recusar a operação por conflito (`409`).
5. Consulte `/history` para restaurar um snapshot de reconciliação **somente quando** o estado remoto ainda corresponder ao estado esperado.

O rollback **não é um backup integral do Pi-hole** e não deve excluir regras criadas fora do Edge Security. A reversão automática de todo tipo de mudança ainda não existe.

## Testes

```bash
PYTHONPATH=backend python3 -m pytest -q tests
```

Na última execução reportada, **22 testes Python passaram**, incluindo correção para comparação de expiração de sessão com timestamps UTC sem informação de fuso. É necessário reexecutá-los no seu ambiente para confirmar a instalação atual.

Para diagnosticar containers:

```bash
docker compose ps
docker compose logs --tail=100 api dashboard pihole collector
```

**Validações pendentes:** `next build`, fluxos no navegador, testes reais da API Pi-hole v6, expiração de sessão de ponta a ponta e falhas parciais durante publicação/reconciliação/rollback.

## Estrutura

```text
edge-security/
├── backend/       # API FastAPI, collector, modelos e Alembic
├── frontend/      # Painel Next.js
├── scripts/       # Gerador de eventos sintéticos
├── tests/         # Testes Python
├── captures/      # Arquivos PCAP autorizados
├── logs/          # Logs EVE JSON
├── compose.yaml
└── .env.example
```

## Cuidados de segurança e operação

- Mantenha `3000`, `8000` e `5353` restritas ao localhost até ter HTTPS e revisão de segurança.
- Proteja os segredos, o banco e os logs; consultas DNS e metadados de tráfego podem conter informações privadas.
- Não trate ausência de alertas como prova de ausência de ameaças; monitore perda de pacotes e integridade da coleta.
- A captura em Docker Desktop macOS não equivale a uma interface SPAN física; para monitoramento real de rede, use host Linux com espelhamento autorizado.
- Mudanças manuais no Pi-hole podem gerar divergência; reconciliação é deliberadamente confirmada, não automática.

## Roadmap

- Testes de integração Compose/Next.js/Pi-hole e execução de cenários reais de conflito/rollback.
- Resiliência do collector à rotação de arquivos EVE.
- Melhoria de métricas de coleta, retenção e desempenho.
- Implantação opcional em Raspberry Pi ou servidor Linux com interface de captura dedicada.
