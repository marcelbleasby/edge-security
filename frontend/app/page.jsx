export const dynamic = 'force-dynamic';
const BASE = process.env.INTERNAL_API_URL || 'http://api:8000';
async function read(path) {
  try {
    const r = await fetch(`${BASE}${path}`, {headers:{'X-API-Key':process.env.API_KEY||''},cache:'no-store'});
    if (!r.ok) return null;
    return await r.json();
  } catch { return null; }
}
const panel = {background:'#162239',border:'1px solid #32405a',borderRadius:12,padding:18};
const cell = {padding:'10px 8px',borderBottom:'1px solid #334155',fontSize:13,textAlign:'left'};
export default async function Home() {
 const [summary, events, devices, policies, analytics, health] = await Promise.all([
   read('/api/v1/traffic/summary'),read('/api/v1/events?limit=30'),
   read('/api/v1/devices?limit=30'),read('/api/v1/policies/domains'),
   read('/api/v1/analytics/overview?hours=24'),read('/api/v1/sensors/health')]);
 return <main>
  <header><a href='/dns' style={{float:'right',color:'#93c5fd'}}>Administrar DNS →</a><h1 style={{marginBottom:4}}>Visão geral </h1><p style={{color:'#94a3b8'}}>Monitoramento passivo • Dados observados, não bloqueados</p></header>
  {!summary && <p style={{padding:16,background:'#78350f'}}>API indisponível. Confira os logs de api, migrations e banco de dados.</p>}
  <section style={{display:'grid',gridTemplateColumns:'repeat(auto-fit,minmax(190px,1fr))',gap:12,margin:'24px 0'}}>
  {[['Eventos',Object.values(summary?.by_event_type||{}).reduce((a,b)=>a+b,0)],['Alertas',summary?.by_event_type?.alert||0],['IPs observados',summary?.device_count||0],['Políticas DNS',summary?.policy_count||0]].map(([name,value])=><div key={name} style={panel}><div style={{color:'#94a3b8'}}>{name}</div><strong style={{fontSize:30}}>{value}</strong></div>)}
  </section>
  <section style={{display:'grid',gridTemplateColumns:'repeat(auto-fit,minmax(300px,1fr))',gap:18,marginBottom:18}}>
    <div style={panel}><h2>Observações por hora (últimas 24h)</h2>
      {analytics?.truncated && <p style={{color:'#fbbf24'}}>Amostra limitada: resultados parciais</p>}
      <div style={{display:'flex',alignItems:'end',gap:3,height:150,borderBottom:'1px solid #475569'}}>
      {(analytics?.timeline||[]).map(item=><div key={item.hour} title={`${item.hour}: ${item.total} eventos, ${item.alerts} alertas`} style={{flex:1,height:`${Math.max(2,(item.total / Math.max(1,...analytics.timeline.map(x=>x.total)))*100)}%`,background:item.alerts?'#fb923c':'#38bdf8',minWidth:3}} />)}
      </div><p style={{fontSize:12,color:'#94a3b8'}}>Contagem de eventos EVE, não largura de banda em bytes.</p>
    </div>
    <div style={panel}><h2>Principais destinos</h2>
      {(analytics?.top_destinations||[]).length === 0 && <p>Sem dados na janela selecionada.</p>}
      {(analytics?.top_destinations||[]).map(x=><div key={x.ip} style={{padding:'6px 0',display:'flex',justifyContent:'space-between',gap:10}}><code>{x.ip}</code><b>{x.observations}</b></div>)}
    </div>
    <div style={panel}><h2>Alertas por prioridade</h2>
      {Object.entries(analytics?.alert_severity||{}).map(([key,value])=><div key={key} style={{padding:'6px 0',display:'flex',justifyContent:'space-between'}}><span>{key}</span><b>{value}</b></div>)}
      <p style={{fontSize:12,color:'#94a3b8'}}>Prioridade original da assinatura Suricata, não avaliação independente de risco.</p>
    </div>
    <div style={panel}><h2>Telemetria dos sensores</h2>
      {(health?.items||[]).map(x=><div key={x.sensor_id}><b>{x.sensor_id}</b><p style={{fontSize:13}}>Último evento: {x.last_event_at||'não recebido'}</p><p style={{fontSize:13}}>Perda na captura: {x.packet_loss?.drop_percent == null?'indisponível':`${x.packet_loss.drop_percent}%`}</p></div>)}
      <p style={{fontSize:12,color:'#94a3b8'}}>Indicadores são observacionais. Sem heartbeat, não é possível confirmar que o sensor está online.</p>
    </div>
  </section>
  <section style={{...panel,overflowX:'auto',marginBottom:18}}><h2>Eventos recentes</h2><table style={{width:'100%',borderCollapse:'collapse'}}><thead><tr>{['Horário','Tipo','Origem','Destino','Domínio','Classificação'].map(h=><th key={h} style={cell}>{h}</th>)}</tr></thead><tbody>{(events?.items||[]).map(e=><tr key={e.id}>{[e.timestamp?.replace('T',' ').slice(0,19)||'—',e.event_type,e.src_ip||'—',e.dest_ip||'—',e.domain||'—',e.classification].map((v,i)=><td style={cell} key={i}>{v}</td>)}</tr>)}</tbody></table></section>
  <div style={{display:'grid',gridTemplateColumns:'repeat(auto-fit,minmax(300px,1fr))',gap:18}}>
   <section style={panel}><h2>IPs observados</h2>{(devices?.items||[]).map(d=><div key={d.id} style={{padding:'8px 0',borderBottom:'1px solid #334155'}}><b>{d.ip}</b> <small style={{color:'#94a3b8'}}>{d.sensor_id}</small></div>)}</section>
   <section style={panel}><h2>Políticas de domínio</h2>{(policies?.items||[]).map(p=><div key={p.id} style={{padding:'8px 0',borderBottom:'1px solid #334155'}}><b>{p.domain}</b> · {p.action} <small style={{color:'#94a3b8'}}>observação</small></div>)}<p style={{fontSize:13,color:'#94a3b8'}}>Gerencie via API autenticada: /docs. Painel somente leitura nesta versão.</p></section>
  </div>
 </main>;
}
