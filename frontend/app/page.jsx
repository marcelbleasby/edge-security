import Link from 'next/link';
import {load} from './_data';
import {Icon} from './_ui/icons';
import {PageHeader,Panel,Note,Banner,EmptyState,Stat,EventType,Classification,Endpoint,fmtTime} from './_ui/ui';
export const dynamic = 'force-dynamic';
const severityLabels=[['high','Alta','danger'],['medium','Média','warning'],['low','Baixa','info'],['unknown','Desconhecida','neutral']];
const hourLabel=h=>String(h).slice(11,16)||String(h);
export default async function Home() {
 const [summary, events, devices, policies, analytics, health] = await Promise.all([
   load('/api/v1/traffic/summary'),load('/api/v1/events?limit=30'),
   load('/api/v1/devices?limit=30'),load('/api/v1/policies/domains'),
   load('/api/v1/analytics/overview?hours=24'),load('/api/v1/sensors/health')]);
 const timeline=analytics?.timeline||[];
 const peak=Math.max(1,...timeline.map(x=>x.total));
 const total=timeline.reduce((a,x)=>a+x.total,0);
 const alertHours=timeline.filter(x=>x.alerts).length;
 const peakItem=timeline.find(x=>x.total===peak);
 const chartSummary=`${total} eventos nas últimas 24 horas${peakItem?`, pico de ${peak} às ${hourLabel(peakItem.hour)} UTC`:''}, ${alertHours} hora(s) com alertas.`;
 const destinations=analytics?.top_destinations||[];
 const topDest=Math.max(1,...destinations.map(x=>x.observations));
 const severity=analytics?.alert_severity||{};
 const severityTotal=Math.max(1,Object.values(severity).reduce((a,b)=>a+b,0));
 return <>
  <PageHeader title="Visão geral" lead="Monitoramento passivo · dados observados, não bloqueados."><Link href="/dns" className="btn btn-secondary">Administrar DNS<Icon name="arrowRight" size={16}/></Link></PageHeader>
  {!summary && <Banner tone="danger"><p><strong>API indisponível.</strong> Confira os logs de api, migrations e banco de dados.</p></Banner>}
  <section className="stats-grid" aria-label="Indicadores">
   <Stat icon="activity" tone="info" label="Eventos" value={Object.values(summary?.by_event_type||{}).reduce((a,b)=>a+b,0)}/>
   <Stat icon="alert" tone="danger" label="Alertas" value={summary?.by_event_type?.alert||0}/>
   <Stat icon="device" label="IPs observados" value={summary?.device_count||0}/>
   <Stat icon="globe" tone="success" label="Políticas DNS" value={summary?.policy_count||0}/>
  </section>
  <div className="stack">
   <div className="grid-wide">
    <Panel title="Observações por hora" meta={<div className="legend"><span className="legend-item"><span className="legend-swatch"/>Eventos</span><span className="legend-item"><span className="legend-swatch alert"/>Hora com alerta</span></div>}>
     {analytics?.truncated && <Banner tone="warning"><p>Amostra limitada: resultados parciais.</p></Banner>}
     {!timeline.length?<EmptyState title="Sem dados de linha do tempo">A API de analytics não retornou observações.</EmptyState>:<>
      <div className="chart" role="img" aria-label={chartSummary}>
       {timeline.map(item=><div key={item.hour} className={`chart-bar${item.alerts?' has-alert':''}`} title={`${hourLabel(item.hour)} UTC: ${item.total} eventos, ${item.alerts} alertas`} style={{height:`${Math.max(2,item.total/peak*100)}%`}}/>)}
      </div>
      <div className="chart-axis" aria-hidden="true"><span>{hourLabel(timeline[0].hour)}</span><span>{hourLabel(timeline[Math.floor(timeline.length/2)].hour)}</span><span>{hourLabel(timeline[timeline.length-1].hour)} UTC</span></div>
      <Note>{chartSummary} Contagem de eventos do sensor, não largura de banda em bytes.</Note>
     </>}
    </Panel>
    <Panel title="Alertas por prioridade">
     {severityLabels.map(([key,label,tone])=><div key={key} className="meter"><span>{label}</span><span className="num mono">{severity[key]||0}</span><div className="meter-track"><div className={`meter-fill ${tone}`} style={{width:`${(severity[key]||0)/severityTotal*100}%`}}/></div></div>)}
     <Note>Prioridade original da assinatura do IDS, não avaliação independente de risco.</Note>
    </Panel>
   </div>
   <div className="grid">
    <Panel title="Principais destinos" meta={<span className="panel-meta">24h</span>}>
     {!destinations.length?<EmptyState title="Sem dados na janela selecionada"/>:destinations.map(x=><div key={x.ip} className="meter"><code>{x.ip}</code><span className="num mono">{x.observations}</span><div className="meter-track"><div className="meter-fill" style={{width:`${x.observations/topDest*100}%`}}/></div></div>)}
    </Panel>
    <Panel title="Telemetria dos sensores" meta={<Link href="/sensors" className="panel-meta">Ver sensores</Link>}>
     {!(health?.items||[]).length?<EmptyState title="Nenhuma telemetria recebida"/>:<ul className="list">{health.items.map(x=><li key={x.sensor_id} className="list-row"><div className="list-main"><strong>{x.sensor_id}</strong><span className="cell-sub">Último evento: {x.last_event_at?fmtTime(x.last_event_at):'não recebido'}</span></div><span className="num">{x.packet_loss?.drop_percent==null?<span className="cell-sub">perda indisponível</span>:`${x.packet_loss.drop_percent}%`}</span></li>)}</ul>}
     <Note>Indicadores observacionais. Sem heartbeat, não é possível confirmar que o sensor está online.</Note>
    </Panel>
   </div>
   <Panel title="Eventos recentes" className="panel-flush" meta={<Link href="/events" className="panel-meta">Ver todos</Link>}>
    <div className="table-scroll"><table><thead><tr><th>Horário</th><th>Tipo</th><th>Origem</th><th>Destino</th><th>Domínio</th><th>Classificação</th></tr></thead><tbody>{(events?.items||[]).map(e=><tr key={e.id}><td className="nowrap mono">{fmtTime(e.timestamp)}</td><td><EventType type={e.event_type}/></td><td><Endpoint ip={e.src_ip}/></td><td><Endpoint ip={e.dest_ip}/></td><td>{e.domain||'—'}</td><td><Classification value={e.classification}/></td></tr>)}</tbody></table></div>
    {!events?.items?.length&&<EmptyState title="Nenhum evento recente"/>}
   </Panel>
   <div className="grid">
    <Panel title="IPs observados" meta={<Link href="/devices" className="panel-meta">Ver inventário</Link>}>
     {!devices?.items?.length?<EmptyState title="Nenhum IP observado"/>:<ul className="list scroll-box">{devices.items.map(d=><li key={d.id} className="list-row"><code>{d.ip}</code><span className="cell-sub">{d.sensor_id}</span></li>)}</ul>}
    </Panel>
    <Panel title="Políticas de domínio" meta={<Link href="/dns" className="panel-meta">Gerenciar</Link>}>
     {!policies?.items?.length?<EmptyState title="Nenhuma política cadastrada">Crie políticas em DNS e políticas.</EmptyState>:<ul className="list scroll-box">{policies.items.map(p=><li key={p.id} className="list-row"><strong className="list-main">{p.domain}</strong><Classification value={p.action}/></li>)}</ul>}
     <Note>Classificação observacional; o DNS só muda após publicação explícita no servidor DNS.</Note>
    </Panel>
   </div>
  </div>
 </>;
}
