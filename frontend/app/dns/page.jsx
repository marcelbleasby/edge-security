import {createPolicy, deletePolicy, deployPolicy, rollbackDeployment, addGroup, addClient, assignClientGroups, setPolicyGroups, reconcileApply} from './actions';
import {load} from '../_data';
import {PageHeader,Panel,Note,Banner,Badge,EmptyState,Classification,fmtTime} from '../_ui/ui';
import {SubmitButton} from '../_ui/client';
export const dynamic = 'force-dynamic';
export default async function DNS(){
 const [policies,status,preview,overview,audit,groupPolicies,drift]=await Promise.all([load('/api/v1/policies/domains'),load('/api/v1/dns/status'),load('/api/v1/dns/preview'),load('/api/v1/dns/overview'),load('/api/v1/dns/audit'),load('/api/v1/dns/policy-groups'),load('/api/v1/dns/reconcile/preview')]);
 const eligible=new Set((preview?.items||[]).filter(x=>x.eligible).map(x=>x.id));
 const groups=overview?.groups||[];
 return <>
  <PageHeader title="Administração DNS" lead="Gerenciamento próprio · publicação manual · inventário DNS · auditoria de alterações">
   {status?.available?<Badge tone="success">Servidor DNS conectado</Badge>:<Badge tone="warning">Servidor DNS indisponível</Badge>}
  </PageHeader>
  <Banner tone="info"><p>O DNS não será alterado até que você publique uma regra explicitamente.</p></Banner>
  <div className="stack">
  <Panel title="Telemetria e reconciliação">
   {!overview?<EmptyState title="Não foi possível consultar o servidor DNS">Verifique a conexão e as credenciais da API do servidor DNS.</EmptyState>:<>
   <div className="kv"><div>Grupos<strong>{overview.groups?.length??0}</strong></div><div>Clientes<strong>{overview.clients?.length??0}</strong></div><div>Regras gerenciadas<strong>{overview.managed?.length??0}</strong></div><div>Ausentes no servidor<strong style={{color:overview.managed_missing?'var(--warning-fg)':'var(--accent-fg)'}}>{overview.managed_missing}</strong></div></div>
   <div className="grid" style={{marginTop:'var(--space-xl)'}}>
    <div><h3>Clientes DNS</h3>{!(overview.clients||[]).length?<EmptyState title="Nenhum cliente cadastrado"/>:<ul className="list scroll-box">{overview.clients.map((c,i)=><li key={i} className="list-row"><code>{String(c.client??c.ip??JSON.stringify(c))}</code></li>)}</ul>}</div>
    <div><h3>Grupos DNS</h3>{!groups.length?<EmptyState title="Nenhum grupo"/>:<div className="chips">{groups.map((g,i)=><Badge key={i}>{String(g.name??JSON.stringify(g))}</Badge>)}</div>}</div>
   </div>
   <h3>Regras publicadas por este projeto</h3>
   {!(overview.managed||[]).length?<EmptyState title="Nenhuma regra publicada"/>:<ul className="list">{overview.managed.map(d=><li key={d.id} className="list-row"><div className="list-main"><strong>{d.domain}</strong><div className="chips" style={{marginTop:4}}><Classification value={d.action}/><Badge>{d.status}</Badge>{d.present?<Badge tone="success">presente</Badge>:<Badge tone="warning">ausente no servidor</Badge>}</div></div>{d.status==='deployed'&&d.present&&<form action={rollbackDeployment}><input type="hidden" name="id" value={d.id}/><SubmitButton variant="danger" pendingLabel="Revertendo…" confirm={`Reverter a publicação de ${d.domain} no servidor DNS?`}>Reverter</SubmitButton></form>}</li>)}</ul>}
   </>}
  </Panel>

  <Panel title="Grupos e clientes DNS">
   <p className="panel-meta">As mudanças são aplicadas diretamente ao servidor DNS após confirmação. Identificação por IP ou CIDR; o IP precisa ser estável para associar uma política ao dispositivo certo.</p>
   <div className="grid" style={{marginTop:'var(--space-lg)',alignItems:'start'}}>
     <form action={addGroup} className="form-row"><label className="field">Nome do grupo<input name="name" required maxLength={60} placeholder="ex.: iot" className="input"/></label><SubmitButton pendingLabel="Criando…">Criar grupo</SubmitButton></form>
     <form action={addClient} className="form-row"><label className="field" style={{flex:'1 1 150px'}}>Cliente (IP ou CIDR)<input name="client" required placeholder="192.168.1.50" className="input mono"/></label><label className="field" style={{flex:'0 1 130px'}}>Grupo<select name="group" className="input">{groups.map(g=><option key={g.id} value={g.id}>{g.name}</option>)}</select></label><SubmitButton pendingLabel="Cadastrando…">Cadastrar cliente</SubmitButton></form>
   </div>
   <h3>Associação de clientes</h3>
   {!(overview?.clients||[]).length?<EmptyState title="Nenhum cliente para associar"/>:<ul className="list">{overview.clients.map((c,i)=><li key={i} className="list-row"><form action={assignClientGroups} className="form-row" style={{width:'100%',justifyContent:'space-between',alignItems:'center'}}>
     <input type="hidden" name="client" value={c.client}/><code>{c.client}</code>
     <fieldset className="chips" style={{border:0,margin:0,padding:0,flex:1}}><legend className="sr-only">Grupos de {c.client}</legend>{groups.map(g=><label key={g.id} className="check"><input type="checkbox" name="groups" value={g.id} defaultChecked={(c.groups||[]).includes(g.id)}/>{g.name}</label>)}</fieldset>
     <SubmitButton pendingLabel="Salvando…">Salvar grupos</SubmitButton>
   </form></li>)}</ul>}
  </Panel>

  <Panel title="Nova política">
   <form action={createPolicy} className="form-row">
    <label className="field" style={{flex:'2 1 260px'}}>Domínio<input required name="domain" placeholder="exemplo.com" className="input mono"/></label>
    <label className="field" style={{flex:'0 1 180px'}}>Ação<select name="action" className="input"><option value="watch">Monitorar</option><option value="allow">Permitir</option><option value="deny">Bloquear</option></select></label>
    <SubmitButton variant="primary" pendingLabel="Criando…">Criar política</SubmitButton>
   </form>
   <Note>A política é apenas cadastrada; publique no servidor DNS para que tenha efeito.</Note>
  </Panel>

  <Panel title="Políticas cadastradas" meta={<span className="panel-meta">{policies?.items?.length||0} políticas</span>}>
   {!(policies?.items?.length)?<EmptyState title="Nenhuma política cadastrada">Use o formulário acima para criar a primeira.</EmptyState>:<ul className="list">{policies.items.map(p=><li key={p.id} className="list-row" style={{flexWrap:'wrap',alignItems:'flex-start'}}>
    <div className="list-main" style={{flex:'1 1 220px'}}><strong>{p.domain}</strong><div className="chips" style={{marginTop:4}}><Classification value={p.action}/><Badge>{p.include_subdomains?'subdomínios incluídos':'somente domínio exato'}</Badge>{p.enabled?<Badge tone="success">habilitada</Badge>:<Badge>desabilitada</Badge>}</div></div>
    <form action={setPolicyGroups} className="form-row" style={{flex:'2 1 320px',alignItems:'center'}}>
      <input type="hidden" name="id" value={p.id}/>
      <fieldset className="chips" style={{border:0,margin:0,padding:0}}><legend className="sr-only">Grupos de {p.domain}</legend>{groups.map(g=><label key={g.id} className="check"><input name="groups" type="checkbox" value={g.id} defaultChecked={(groupPolicies?.items||[]).find(x=>x.policy_id===p.id)?.groups?.includes(g.id)??(g.id===0)}/>{g.name}</label>)}</fieldset>
      <SubmitButton pendingLabel="Salvando…">Salvar escopo</SubmitButton>
    </form>
    <div className="list-actions">
     {eligible.has(p.id)&&<form action={deployPolicy}><input type="hidden" name="id" value={p.id}/><SubmitButton variant="primary" pendingLabel="Publicando…" confirm={`Publicar a política de ${p.domain} no servidor DNS? O DNS da rede será alterado.`}>Publicar no DNS</SubmitButton></form>}
     <form action={deletePolicy}><input type="hidden" name="id" value={p.id}/><SubmitButton variant="danger" pendingLabel="Excluindo…" confirm={`Excluir ${p.domain} do cadastro? Regras já publicadas no servidor DNS não são removidas.`}>Excluir do cadastro</SubmitButton></form>
    </div>
   </li>)}</ul>}
   <Note>Excluir do cadastro não remove regras já publicadas no servidor DNS. Nesta versão, revise entradas aplicadas diretamente no servidor DNS antes de removê-las.</Note>
  </Panel>

  <Panel title="Reconciliação de grupos">
    {!(drift?.items||[]).length?<EmptyState title="Nenhuma divergência para reconciliar"/>:<ul className="list">{drift.items.map(d=><li key={d.deployment_id} className="list-row" style={{flexWrap:'wrap'}}><div className="list-main"><strong>{d.domain}</strong> <Badge tone={d.status==='groups_mismatch'?'warning':'neutral'}>{d.status}</Badge><span className="cell-sub">desejado: {(d.desired_groups||[]).join(', ')||'—'} · remoto: {(d.actual_groups||[]).join(', ')||'—'}</span></div>{d.safe&&d.status==='groups_mismatch'&&<form action={reconcileApply}><input type='hidden' name='deployment_id' value={d.deployment_id}/><input type='hidden' name='fingerprint' value={d.expected_fingerprint}/><SubmitButton variant="primary" pendingLabel="Aplicando…" confirm={`Aplicar os grupos desejados de ${d.domain} no servidor DNS?`}>Confirmar reconciliação</SubmitButton></form>}</li>)}</ul>}
    <Note>A prévia é somente leitura; a aplicação ocorre apenas após confirmação e verificação de versão.</Note>
  </Panel>

  <Panel title="Auditoria">{!(audit?.items?.length)?<EmptyState title="Sem alterações publicadas"/>:<ul className="list scroll-box">{audit.items.map(x=><li key={x.id} className="list-row"><div className="list-main"><strong>{x.event}</strong> · {x.domain}</div><span className="mono cell-sub">{fmtTime(x.created_at)}</span></li>)}</ul>}</Panel>
  </div>
 </>;
}
