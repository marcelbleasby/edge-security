'use server';
import {revalidatePath} from 'next/cache';
import {cookies} from 'next/headers';
const BASE = process.env.INTERNAL_API_URL || 'http://api:8000';
async function assertAdmin(){
 const token=(await cookies()).get('edge_session')?.value;
 if(!token)throw new Error('Login required');
 const r=await fetch(BASE+'/api/v1/auth/session',{headers:{'X-API-Key':process.env.API_KEY||'','X-Admin-Session':token},cache:'no-store'});
 if(!r.ok)throw new Error('Session expired');
}
async function request(path, opts={}) {
  if(opts.method && opts.method!=='GET') await assertAdmin();
  const resp=await fetch(BASE+path,{...opts,headers:{'X-API-Key':process.env.API_KEY||'', 'Content-Type':'application/json'},cache:'no-store'});
  if(!resp.ok) throw new Error('Operação rejeitada pela API: '+resp.status);
  return resp.status===204?null:resp.json();
}
export async function createPolicy(form) {
  const domain=String(form.get('domain')||'').trim();
  const action=String(form.get('action')||'watch');
  if(!['allow','deny','watch'].includes(action)) throw new Error('Ação inválida');
  await request('/api/v1/policies/domains',{method:'POST',body:JSON.stringify({domain,action,include_subdomains:false,enabled:true})});
  revalidatePath('/dns');
}
export async function deletePolicy(form) {
  const id=Number(form.get('id'));
  if(!Number.isSafeInteger(id)||id<1) throw new Error('ID inválido');
  await request('/api/v1/policies/domains/'+id,{method:'DELETE'});
  revalidatePath('/dns');
}
export async function deployPolicy(form) {
  const id=Number(form.get('id'));
  if(!Number.isSafeInteger(id)||id<1) throw new Error('ID inválido');
  await request('/api/v1/dns/deploy/'+id,{method:'POST'});
  revalidatePath('/dns');
}
export async function rollbackDeployment(form) {
  const id=Number(form.get('id'));
  if(!Number.isSafeInteger(id)||id<1) throw new Error('ID inválido');
  await request('/api/v1/dns/rollback/'+id,{method:'POST'});
  revalidatePath('/dns');
}

export async function addGroup(form){
 const name=String(form.get('name')||'').trim();
 if(!name||name.length>60) throw new Error('Nome inválido');
 await request('/api/v1/dns/groups',{method:'POST',body:JSON.stringify({name})});
 revalidatePath('/dns');
}
export async function addClient(form){
 const client=String(form.get('client')||'').trim();
 const group=Number(form.get('group'));
 if(!client||!Number.isSafeInteger(group)||group<0) throw new Error('Cliente/grupo inválido');
 await request('/api/v1/dns/clients',{method:'POST',body:JSON.stringify({client,groups:[group]})});
 revalidatePath('/dns');
}
export async function assignClientGroups(form){
 const client=String(form.get('client')||'');
 const groups=form.getAll('groups').map(Number);
 if(!client||!groups.length||groups.some(n=>!Number.isSafeInteger(n)||n<0)) throw new Error('Selecione pelo menos um grupo');
 await request('/api/v1/dns/clients/'+encodeURIComponent(client)+'/groups',{method:'PUT',body:JSON.stringify({groups})});
 revalidatePath('/dns');
}

export async function setPolicyGroups(form){
 const id=Number(form.get('id'));
 const groups=form.getAll('groups').map(Number);
 if(!Number.isSafeInteger(id)||id<1||!groups.length||groups.some(g=>!Number.isSafeInteger(g)||g<0)) throw new Error('Política/grupos inválidos');
 await request('/api/v1/dns/policies/'+id+'/groups',{method:'PUT',body:JSON.stringify({groups})});
 revalidatePath('/dns');
}

export async function reconcileApply(form){
 const deployment_id=Number(form.get('deployment_id'));
 const expected_fingerprint=String(form.get('fingerprint')||'');
 if(!Number.isSafeInteger(deployment_id)||deployment_id<1||!expected_fingerprint)throw new Error('Prévia inválida');
 await request('/api/v1/dns/reconcile/apply',{method:'POST',body:JSON.stringify({deployment_id,expected_fingerprint})});
 revalidatePath('/dns');revalidatePath('/history');
}
export async function rollbackChange(form){
 const id=Number(form.get('id'));
 if(!Number.isSafeInteger(id)||id<1)throw new Error('ID inválido');
 await request('/api/v1/dns/changes/'+id+'/rollback',{method:'POST'});
 revalidatePath('/dns');revalidatePath('/history');
}
