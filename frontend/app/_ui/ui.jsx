import {Icon} from './icons';

export function fmtTime(value){if(!value)return '—';const s=String(value);return /^\d{4}-\d\d-\d\dT/.test(s)?s.replace('T',' ').slice(0,19):s;}

export function PageHeader({title,lead,children}){return <header className="page-header"><div><h1>{title}</h1>{lead&&<p className="page-lead">{lead}</p>}</div>{children&&<div className="page-actions">{children}</div>}</header>;}

export function Panel({title,meta,children,className=''}){return <section className={`panel ${className}`}>{(title||meta)&&<div className="panel-header">{title&&<h2>{title}</h2>}{meta}</div>}{children}</section>;}

export function Note({children}){return <p className="panel-note">{children}</p>;}

export function Badge({tone='neutral',children}){return <span className={`badge badge-${tone}`}><span className="badge-dot" aria-hidden="true"/>{children}</span>;}

export function Banner({tone='warning',children}){return <div className={`banner banner-${tone}`} role="status"><Icon name={tone==='info'?'info':'warning'}/><div>{children}</div></div>;}

export function EmptyState({title,children}){return <div className="empty-state"><Icon name="inbox" size={22}/><div><p className="empty-title">{title}</p>{children&&<p className="empty-text">{children}</p>}</div></div>;}

export function Stat({icon,label,value,tone}){return <div className={`stat${tone?` stat-${tone}`:''}`}><div className="stat-label"><Icon name={icon} size={16}/>{label}</div><div className="stat-value">{value}</div></div>;}

const eventTones={alert:'danger',dns:'info',flow:'neutral'};
export function EventType({type}){return <Badge tone={eventTones[type]||'neutral'}>{type||'—'}</Badge>;}

const classes={allow:['success','Permitido'],deny:['danger','Bloqueado'],watch:['warning','Monitorado'],unclassified:['neutral','Sem política']};
export function Classification({value}){const [tone,label]=classes[value]||['neutral',value||'—'];return <Badge tone={tone}>{label}</Badge>;}

// Prioridade da assinatura do IDS: número menor = mais urgente.
const priorities={1:['danger','P1 · alta'],2:['warning','P2 · média'],3:['info','P3 · baixa']};
export function Priority({value}){if(value==null)return '—';const [tone,label]=priorities[value]||['neutral',`P${value}`];return <Badge tone={tone}>{label}</Badge>;}

export function Endpoint({ip,port}){if(!ip)return '—';return <code>{ip}{port!=null&&<span className="port">:{port}</span>}</code>;}
