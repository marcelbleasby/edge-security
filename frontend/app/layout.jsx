import './globals.css';
import Link from 'next/link';
import {Fira_Code,Fira_Sans} from 'next/font/google';
import LogoutButton from './logout-button';
import {headers} from 'next/headers';
import {Icon} from './_ui/icons';
import {NavLinks} from './_ui/client';
const sans=Fira_Sans({subsets:['latin'],weight:['400','500','600','700'],variable:'--font-fira-sans',display:'swap'});
const mono=Fira_Code({subsets:['latin'],weight:['400','500','600'],variable:'--font-fira-code',display:'swap'});
export const metadata={title:'Edge Security | Administração',description:'Monitoramento e administração de segurança de rede'};
export const viewport={width:'device-width',initialScale:1,themeColor:'#0f172a'};
const links=[['/','overview','Visão geral'],['/events','activity','Eventos'],['/alerts','alert','Alertas'],['/devices','device','Dispositivos'],['/sensors','sensor','Sensores'],['/dns','globe','DNS e políticas'],['/history','history','Histórico']];
export default async function RootLayout({children}){const h=await headers();const login=h.get('x-edge-login')==='1';return <html lang="pt-BR" className={`${sans.variable} ${mono.variable}`}><body>{login?children:<>
  <a href="#conteudo" className="skip-link">Pular para o conteúdo</a>
  <div className="app-layout">
    <aside className="sidebar">
      <Link href="/" className="brand" aria-label="Edge Security, visão geral"><span className="brand-mark"><Icon name="shield"/></span><span className="brand-name">Edge Security</span></Link>
      <div className="side-heading">Workspace</div>
      <NavLinks links={links}/>
      <div className="sidebar-footer"><strong>Painel administrativo</strong>IDS + DNS</div>
    </aside>
    <div className="content-shell">
      <header className="topbar"><span className="topbar-eyebrow">Segurança de rede / Console</span><div className="topbar-right"><span className="topbar-mode"><span className="badge badge-info"><span className="badge-dot" aria-hidden="true"/>Monitoramento passivo</span></span><LogoutButton/></div></header>
      <main id="conteudo" className="page-content">{children}</main>
    </div>
  </div>
</>}</body></html>}
