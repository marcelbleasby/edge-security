'use client';
import {useState} from 'react';import {useRouter} from 'next/navigation';import {Icon} from '../_ui/icons';
export default function Login(){const [username,setUsername]=useState('admin'),[password,setPassword]=useState(''),[busy,setBusy]=useState(false),[error,setError]=useState('');const router=useRouter();
  async function submit(e){
    e.preventDefault();
    setBusy(true);
    setError('');
    try{
      const r=await fetch('/api/auth/login',{
        method:'POST',
        headers:{'Content-Type':'application/json'},
        body:JSON.stringify({username,password})
      });
      if(!r.ok){
        const data=await r.json().catch(()=>({}));
        throw Error(data.error||'Usuário ou senha inválidos');
      }
      router.replace('/');
      router.refresh();
    }catch(e){
      setError(e.message);
    }finally{
      setBusy(false);
    }
  }
 return <main className="login-wrap"><div className="login-card"><div className="brand"><span className="brand-mark"><Icon name="shield"/></span>Edge Security</div><h1>Acesso administrativo</h1><p className="page-lead">Entre para administrar os sensores e as políticas de DNS.</p>
  <form onSubmit={submit} aria-busy={busy}>
   <label className="field" htmlFor="username">Usuário<input id="username" className="input" autoComplete="username" required value={username} onChange={e=>setUsername(e.target.value)} aria-invalid={!!error||undefined} aria-describedby={error?'login-error':undefined}/></label>
   <label className="field" htmlFor="password">Senha<input id="password" className="input" type="password" autoComplete="current-password" required value={password} onChange={e=>setPassword(e.target.value)} aria-invalid={!!error||undefined} aria-describedby={error?'login-error':undefined}/></label>
   {error&&<p id="login-error" role="alert" className="field-error"><Icon name="warning" size={16}/>{error}</p>}
   <button type="submit" disabled={busy} className="btn btn-primary btn-block">{busy?'Autenticando…':'Entrar'}</button>
  </form>
  <p className="login-foot">Acesso restrito a administradores da rede.</p></div></main>;
}
