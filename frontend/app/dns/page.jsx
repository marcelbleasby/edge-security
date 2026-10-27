import Link from 'next/link';
import {createPolicy, deletePolicy, deployPolicy, rollbackDeployment, addGroup, addClient, assignClientGroups, setPolicyGroups, reconcileApply} from './actions';
export const dynamic = 'force-dynamic';
const BASE = process.env.INTERNAL_API_URL || 'http://api:8000';
async function get(path){try{const r=await fetch(BASE+path,{headers:{'X-API-Key':process.env.API_KEY||''},cache:'no-store'});return r.ok?await r.json():null;}catch{return null;}}
const panel={border:'1px solid #334155',borderRadius:14,padding:20,background:'#162239'};
const button={border:'1px solid #64748b',background:'#26364e',color:'white',padding:'8px 12px',borderRadius:8,cursor:'pointer'};
const input={padding:'10px',borderRadius:8,background:'#0b1220',color:'white',border:'1px solid #64748b'};
export default async function DNS(){
 const [policies,status,preview,overview,audit,groupPolicies,drift]=await Promise.all([get('/api/v1/policies/domains'),get('/api/v1/dns/status'),get('/api/v1/dns/preview'),get('/api/v1/dns/overview'),get('/api/v1/dns/audit'),get('/api/v1/dns/policy-groups'),get('/api/v1/dns/reconcile/preview')]);
 const eligible=new Set((preview?.items||[]).filter(x=>x.eligible).map(x=>x.id));
 return <main>
  <Link href="/" style={{color:'#93c5fd'}}>← Monitoramento</Link>
  <h1>Administração DNS</h1><p style={{color:'#94a3b8'}}>Gerenciamento próprio · Pi-hole v6 · publicação manual · inventário DNS · auditoria de alterações</p>
  <section style={{...panel,marginBottom:18}}><h2>Estado do Pi-hole</h2><b style={{color:status?.available?'#4ade80':'#fbbf24'}}>{status?.available?'API conectada':'Indisponível'}</b><p style={{color:'#94a3b8'}}>O DNS não será alterado até que você publique uma regra explicitamente.</p></section>

  <section style={{...panel,marginBottom:18}}><h2>Telemetria e reconciliação</h2>
   {!overview?<p style={{color:'#fbbf24'}}>Não foi possível consultar o Pi-hole.</p>:<>
   <div style={{display:'flex',gap:28,flexWrap:'wrap'}}><div>Grupos: <strong>{overview.groups?.length??0}</strong></div><div>Clientes: <strong>{overview.clients?.length??0}</strong></div><div>Regras gerenciadas: <strong>{overview.managed?.length??0}</strong></div><div style={{color:overview.managed_missing?'#fbbf24':'#4ade80'}}>Ausentes no Pi-hole: <strong>{overview.managed_missing}</strong></div></div>
   <h3>Clientes DNS do Pi-hole</h3><div style={{maxHeight:160,overflow:'auto'}}>{(overview.clients||[]).map((c,i)=><div key={i} style={{borderBottom:'1px solid #334155',padding:7,fontSize:13}}>{String(c.client??c.ip??JSON.stringify(c))}</div>)}</div>
   <h3>Grupos DNS</h3><div style={{display:'flex',gap:8,flexWrap:'wrap'}}>{(overview.groups||[]).map((g,i)=><span key={i} style={{background:'#26364e',padding:8,borderRadius:8}}>{String(g.name??JSON.stringify(g))}</span>)}</div>
   <h3>Regras publicadas por este projeto</h3>{(overview.managed||[]).map(d=><div key={d.id} style={{display:'flex',alignItems:'center',justifyContent:'space-between',gap:10,borderBottom:'1px solid #334155',padding:'9px 0'}}><div><strong>{d.domain}</strong><div style={{fontSize:12,color:d.present?'#4ade80':'#fbbf24'}}>{d.action} · {d.status} · {d.present?'presente':'ausente no Pi-hole'}</div></div>{d.status==='deployed'&&d.present&&<form action={rollbackDeployment}><input type="hidden" name="id" value={d.id}/><button style={button}>Reverter</button></form>}</div>)}
   </>}
  </section>
  <section style={{...panel,marginBottom:18}}><h2>Grupos e clientes DNS</h2>
   <p style={{color:'#94a3b8'}}>As mudanças são aplicadas diretamente ao Pi-hole após confirmação. Identificação por IP ou CIDR; o IP precisa ser estável para associar uma política ao dispositivo certo.</p>
   <div style={{display:'flex',gap:20,flexWrap:'wrap'}}>
     <form action={addGroup} style={{display:'flex',gap:8,flexWrap:'wrap'}}><input name="name" required placeholder="Nome do grupo" style={input}/><button style={button}>Criar grupo</button></form>
     <form action={addClient} style={{display:'flex',gap:8,flexWrap:'wrap'}}><input name="client" required placeholder="192.168.1.50" style={input}/><select name="group" style={input}>{(overview?.groups||[]).map(g=><option key={g.id} value={g.id}>{g.name}</option>)}</select><button style={button}>Cadastrar cliente</button></form>
   </div>
   <h3>Associação de clientes</h3>
   {(overview?.clients||[]).map((c,i)=><form action={assignClientGroups} key={i} style={{borderBottom:'1px solid #334155',padding:'12px 0'}}>
     <input type="hidden" name="client" value={c.client}/><strong>{c.client}</strong>
     <div style={{display:'flex',gap:12,flexWrap:'wrap',margin:'8px 0'}}>{(overview?.groups||[]).map(g=><label key={g.id} style={{fontSize:13}}><input type="checkbox" name="groups" value={g.id} defaultChecked={(c.groups||[]).includes(g.id)}/> {g.name}</label>)}</div>
     <button style={button}>Salvar grupos</button>
   </form>)}
  </section>
  <section style={{...panel,marginBottom:18}}><h2>Auditoria</h2>{!(audit?.items?.length)?<p>Sem alterações publicadas.</p>:(audit.items).map(x=><div key={x.id} style={{fontSize:13,padding:8,borderBottom:'1px solid #334155'}}><b>{x.event}</b> · {x.domain} · {String(x.created_at)}</div>)}</section>
  <section style={{...panel,marginBottom:18}}><h2>Nova política</h2>
   <form action={createPolicy} style={{display:'flex',gap:10,flexWrap:'wrap'}}>
    <input required name="domain" placeholder="exemplo.com" style={{...input,flex:2}}/>
    <select name="action" style={input}><option value="watch">Monitorar</option><option value="allow">Permitir</option><option value="deny">Bloquear</option></select>
    <button style={button}>Criar política</button>
   </form>
  </section>
  <section style={{...panel,marginBottom:18}}><h2>Reconciliação de grupos</h2>
    {(drift?.items||[]).map(d=><div key={d.deployment_id} style={{padding:7,borderBottom:'1px solid #334155'}}>{d.domain}: <b>{d.status}</b> · desejado: {(d.desired_groups||[]).join(', ')} · remoto: {(d.actual_groups||[]).join(', ')} {d.safe&&d.status==='groups_mismatch'&&<form action={reconcileApply} style={{display:'inline-flex',gap:8,marginLeft:12}}><input type='hidden' name='deployment_id' value={d.deployment_id}/><input type='hidden' name='fingerprint' value={d.expected_fingerprint}/><button style={button}>Confirmar reconciliação</button></form>}</div>)}
    <p style={{fontSize:12,color:'#94a3b8'}}>A prévia é somente leitura; a aplicação ocorre apenas após confirmação e verificação de versão.</p>
  </section>
  <section style={panel}><h2>Políticas cadastradas</h2>
   {!(policies?.items?.length) && <p>Nenhuma política cadastrada.</p>}
   {(policies?.items||[]).map(p=><div key={p.id} style={{display:'flex',alignItems:'center',justifyContent:'space-between',gap:12,borderBottom:'1px solid #334155',padding:'12px 0',flexWrap:'wrap'}}>
    <div><strong>{p.domain}</strong><div style={{color:'#94a3b8',fontSize:13}}>{p.action} · {p.include_subdomains?'subdomínios incluídos':'somente domínio exato'} · {p.enabled?'habilitada':'desabilitada'}</div></div>
    <form action={setPolicyGroups, reconcileApply} style={{display:'flex',gap:8,flexWrap:'wrap',alignItems:'center'}}>
      <input type="hidden" name="id" value={p.id}/>
      {(overview?.groups||[]).map(g=><label key={g.id} style={{fontSize:12}}><input name="groups" type="checkbox" value={g.id} defaultChecked={(groupPolicies?.items||[]).find(x=>x.policy_id===p.id)?.groups?.includes(g.id)??(g.id===0)}/> {g.name}</label>)}
      <button style={button}>Salvar escopo</button>
    </form>
    <div style={{display:'flex',gap:8}}>
     {eligible.has(p.id)&&<form action={deployPolicy}><input type="hidden" name="id" value={p.id}/><button style={button}>Publicar no Pi-hole</button></form>}
     <form action={deletePolicy}><input type="hidden" name="id" value={p.id}/><button style={button}>Excluir do cadastro</button></form>
    </div>
   </div>)}
   <p style={{fontSize:12,color:'#94a3b8'}}>Excluir do cadastro não remove regras já publicadas no Pi-hole. Nesta versão, revise entradas aplicadas diretamente no Pi-hole antes de removê-las.</p>
  </section>
 </main>;
}
