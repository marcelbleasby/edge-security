'use client';
import {Icon} from './_ui/icons';
export default function Error({error,reset}){return <div className="panel" role="alert"><div className="empty-state" style={{color:'var(--danger-fg)'}}><Icon name="warning" size={22}/><div><p className="empty-title">Não foi possível concluir a operação</p><p className="empty-text">{error?.message||'Erro inesperado.'} Nenhuma alteração adicional foi feita; tente novamente ou confira os logs da API.</p></div></div><button className="btn btn-secondary" onClick={()=>reset()}><Icon name="refresh" size={16}/>Tentar novamente</button></div>;}
