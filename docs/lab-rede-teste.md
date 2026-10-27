# Guia: rede local de teste para simular o sensor

Este guia monta uma rede de laboratório **isolada** para exercitar o pipeline completo do sensor com tráfego real (não apenas eventos sintéticos):

```text
lab-client-1/2 ──┐
                 ├── bridge br-edgelab (172.30.0.0/24, sem internet)
lab-web ─────────┤        │
pihole (.53) ────┘        │ af-packet (como uma porta SPAN)
                          v
                    suricata-live -> logs/eve.json -> collector -> PostgreSQL -> API -> painel
```

> **Escopo:** tráfego gerado somente por containers seus, numa rede sem saída para a internet. Não aponte o sensor para redes de terceiros nem capture tráfego sem autorização.

## Três níveis de simulação

| Nível | O que exercita | Comando |
| --- | --- | --- |
| 0. Sintético | Collector, banco, API, painel | `python3 scripts/seed_eve.py` |
| 1. PCAP | Suricata offline + collector | `docker compose --profile pcap run --rm suricata` |
| 2. **Rede de laboratório (este guia)** | Captura ao vivo, alertas, DNS via Pi-hole, perda de pacotes, inventário de dispositivos | `compose.lab.yaml` |
| 3. Rede física | SPAN/espelhamento real em host Linux | ver [Rede física](#nível-3-rede-física-de-laboratório) |

## Componentes

| Arquivo | Função |
| --- | --- |
| `compose.lab.yaml` | Override: rede `lab`, clientes, servidor web, Suricata ao vivo; anexa o Pi-hole à rede `lab` |
| `lab/traffic.sh` | Loop de tráfego benigno + marcadores (DNS, HTTP, portas sensíveis) |
| `lab/rules/lab.rules` | Regras Suricata locais que disparam só com os marcadores |

### Endereços da rede `lab`

| Host | IP | Papel |
| --- | --- | --- |
| `lab-client-1` | 172.30.0.11 | Cliente normal (ciclo de 20s) |
| `lab-client-2` | 172.30.0.12 | Cliente “ruidoso”: ciclo de 45s + conexões às portas 21/23/3389 |
| `pihole` | 172.30.0.53 | Resolvedor DNS dos clientes |
| `lab-web` | 172.30.0.80 | Servidor HTTP (nginx) |

A rede é `internal: true`: os clientes não alcançam a internet. O Pi-hole continua resolvendo upstream pela rede `internal` do projeto.

### Alertas esperados

| SID | Gatilho | Severidade | Quem gera |
| --- | --- | --- | --- |
| 9000001 | Consulta DNS `lab-alerta.test` | 3 | ambos os clientes |
| 9000002 | HTTP para `/lab-marker` | 2 | ambos os clientes |
| 9000003 | SYN para portas 21/23/3389 | 1 | `lab-client-2` |

## Pré-requisitos

- Stack base configurada conforme o `README.md` (`.env` preenchido, `docker compose up --build -d` funcionando).
- Docker com suporte a `network_mode: host` alcançando as bridges do daemon. Testado em **OrbStack** (macOS); também deve funcionar em Linux nativo e Docker Desktop, pois a bridge vive no mesmo namespace de rede do daemon.
- Sub-rede `172.30.0.0/24` livre. Se colidir com sua LAN/VPN, troque a sub-rede e os IPs em `compose.lab.yaml` e `lab/traffic.sh`.

## Passo a passo

### 1. Subir a stack com o laboratório

```bash
docker compose -f compose.yaml -f compose.lab.yaml --profile lab up -d
docker compose -f compose.yaml -f compose.lab.yaml ps
```

O Pi-hole é recriado para entrar na rede `lab`; o volume `pihole_data` é preservado.

Para não repetir os `-f`, exporte na sessão:

```bash
export COMPOSE_FILE=compose.yaml:compose.lab.yaml
export COMPOSE_PROFILES=lab
docker compose ps
```

### 2. Confirmar que o sensor está capturando

```bash
docker compose logs --tail=30 suricata-live
```

Procure `engine started` e ausência de erros sobre `br-edgelab`. Em seguida, acompanhe os alertas chegando:

```bash
tail -f logs/eve.json | grep --line-buffered '"event_type":"alert"'
```

Em até ~1 minuto devem aparecer os SIDs 9000001, 9000002 e 9000003.

### 3. Confirmar a ingestão

```bash
docker compose logs --tail=20 collector   # "Processed N events"
```

### 4. Validar no painel

| Página | Resultado esperado |
| --- | --- |
| `/alerts` | Alertas `EDGE-LAB ...` com severidades 1, 2 e 3 |
| `/events` | Eventos `dns`, `http`, `alert`, `stats` e, após o timeout dos fluxos, `flow` |
| `/devices` | 172.30.0.11, .12, .53 e .80 com primeira/última observação |
| `/sensors` | Sensor `docker-lab-01` com último evento recente e **perda de pacotes em %** (vem dos eventos `stats` da captura ao vivo; no modo PCAP fica “Indisponível”) |

Os eventos `flow` só são emitidos quando o fluxo expira no Suricata; é normal aparecerem com atraso de alguns minutos.

## Cenários de teste

### A. Bloqueio DNS ponta a ponta (Pi-hole)

1. Em `/dns`, cadastre um domínio de bloqueio (ex.: `bloqueado.lab.test`) e publique a política.
2. Consulte a partir de um cliente do laboratório:

   ```bash
   docker compose exec lab-client-1 nslookup bloqueado.lab.test 172.30.0.53
   ```

3. Esperado: resposta `0.0.0.0` (ou NXDOMAIN, conforme o modo de bloqueio do Pi-hole) e o evento `dns` correspondente em `/events`.

Para políticas por cliente/grupo, use os IPs fixos `172.30.0.11` e `172.30.0.12` como clientes no Pi-hole.

### B. Disparo manual de alerta

```bash
docker compose exec lab-client-1 wget -q -O /dev/null http://172.30.0.80/lab-marker
docker compose exec lab-client-1 wget -q -T 1 -O /dev/null http://172.30.0.80:23/
```

### C. Sensor parado (silêncio ≠ segurança)

```bash
docker compose stop suricata-live
```

O tráfego continua, mas `/sensors` deixa de atualizar o último evento. Use para validar como o painel comunica ausência de telemetria. Retome com `docker compose start suricata-live`.

### D. Novo dispositivo na rede

```bash
docker run --rm --network edge-security_lab --ip 172.30.0.99 alpine:3.20 \
  sh -c 'nslookup novo-dispositivo.lab.test 172.30.0.53; wget -q -T 2 -O /dev/null http://172.30.0.80/'
```

Esperado: `172.30.0.99` aparece em `/devices`.

### E. Volume de tráfego / perda de pacotes

Reduza o intervalo dos clientes para gerar carga:

```bash
INTERVAL=1 docker compose up -d --force-recreate lab-client-1
```

Ou edite `INTERVAL` em `compose.lab.yaml`. Acompanhe `drop_percent` em `/sensors`. Lembre: os contadores do Suricata são cumulativos e zeram ao reiniciar o container.

### F. Regras próprias

Adicione regras em `lab/rules/lab.rules` (use SIDs na faixa `9000000–9099999`) e reinicie o sensor:

```bash
docker compose restart suricata-live
docker compose logs --tail=30 suricata-live   # confira se as regras carregaram sem erro
```

## Encerrar e limpar

```bash
# Para só o laboratório, mantendo a stack base
docker compose -f compose.yaml -f compose.lab.yaml stop lab-client-1 lab-client-2 lab-web suricata-live

# Volta o Pi-hole à configuração base (sem a rede lab)
docker compose -f compose.yaml up -d --remove-orphans
```

Não use `docker compose down -v`: isso apaga os volumes do banco e do Pi-hole.

Os eventos do laboratório ficam em `logs/eve.json` e no banco junto dos demais, com o mesmo `SENSOR_ID`. Para isolar um teste, ajuste `SENSOR_ID` no `.env` antes de subir e recrie o `collector`.

## Solução de problemas

| Sintoma | Causa provável | Ação |
| --- | --- | --- |
| `suricata-live` reinicia com erro de interface | Bridge `br-edgelab` não existe ou não é visível no namespace do host | `docker network inspect edge-security_lab`; confirme que o runtime suporta `network_mode: host` |
| Nenhum alerta, mas há eventos `dns` | Regras não carregadas | Veja os logs do Suricata; confira o caminho `-S /opt/edge-lab/lab.rules` |
| Sem eventos `http` | Checksums inválidos por offload na veth | O override já usa `-k none`; não remova |
| Clientes sem resposta DNS | Pi-hole não entrou na rede `lab` | `docker compose -f compose.yaml -f compose.lab.yaml up -d pihole` |
| Conflito de sub-rede ao criar a rede | `172.30.0.0/24` em uso | Troque a sub-rede e os IPs fixos |
| `/sensors` sem perda de pacotes | Ainda não houve evento `stats` (intervalo padrão ~8s) ou eventos vieram só de PCAP | Aguarde e confirme `"event_type":"stats"` em `logs/eve.json` |

## Nível 3: rede física de laboratório

Para aproximar do uso real, use um **host Linux** dedicado (mini-PC, Raspberry Pi 4/5) com duas interfaces:

1. **Gerência** (ex.: `eth0`): acesso ao painel, ainda restrito a `127.0.0.1` ou túnel SSH.
2. **Captura** (ex.: `eth1`): ligada à porta espelhada (SPAN/mirror) de um switch gerenciável, sem IP configurado.

Preparação da interface de captura:

```bash
sudo ip link set eth1 up promisc on
sudo ethtool -K eth1 gro off lro off   # reduz pacotes remontados pela NIC
```

No `compose.lab.yaml` (ou num override próprio), troque a interface do sensor:

```yaml
command: ["--af-packet=eth1", "-k", "none", "-S", "/opt/edge-lab/lab.rules", "-l", "/var/log/suricata"]
```

Ajuste `HOME_NET` para a sub-rede do laboratório se ela não estiver em RFC1918.

Para que dispositivos físicos usem o Pi-hole como DNS, seria preciso publicar a porta 53 num IP da LAN de teste (hoje ela está restrita a `127.0.0.1:5353`). Faça isso **apenas** numa LAN isolada de laboratório, nunca na rede doméstica ou corporativa sem revisão.

Alternativa sem switch gerenciável: roteador de laboratório com espelhamento de porta, ou um host Linux atuando como bridge transparente entre os dispositivos de teste e o uplink.
