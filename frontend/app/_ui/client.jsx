'use client';
import Link from 'next/link';
import {usePathname} from 'next/navigation';
import {useFormStatus} from 'react-dom';
import {Icon} from './icons';

export function NavLinks({links}){
  const path=usePathname();
  return <nav className="nav" aria-label="Navegação principal">{links.map(([href,icon,title])=>{
    const active=href==='/'?path==='/':path.startsWith(href);
    return <Link key={href} href={href} className="nav-link" aria-current={active?'page':undefined} title={title}><Icon name={icon}/><span className="nav-label">{title}</span></Link>;
  })}</nav>;
}

// Botão de envio para Server Actions: mostra estado pendente e pede confirmação
// antes de operações que alteram o servidor DNS ou removem dados.
export function SubmitButton({children,variant='secondary',pendingLabel='Processando…',confirm}){
  const {pending}=useFormStatus();
  return <button type="submit" className={`btn btn-${variant}`} disabled={pending} aria-busy={pending||undefined}
    onClick={e=>{if(confirm&&!window.confirm(confirm))e.preventDefault();}}>{pending?pendingLabel:children}</button>;
}
