import {NextResponse} from 'next/server';

function isAllowedOrigin(req){
 const origin=req.headers.get('origin');
 if(!origin)return true;
 const host=req.headers.get('x-forwarded-host')||req.headers.get('host');
 try{
  const originUrl=new URL(origin);
  if(host&&originUrl.host===host)return true;
  if(originUrl.origin===new URL(req.url).origin)return true;
  const isLoopback=(h)=>h==='localhost'||h==='127.0.0.1'||h==='::1'||h==='[::1]';
  const reqHost=host?host.split(':')[0]:'';
  if(isLoopback(originUrl.hostname)&&(isLoopback(reqHost)||isLoopback(new URL(req.url).hostname))){
   return true;
  }
 }catch{
  return false;
 }
 return false;
}

export async function POST(req){
 if(!isAllowedOrigin(req))return NextResponse.json({error:'Origem inválida'},{status:403});
 const token=req.cookies.get('edge_session')?.value;
 if(token)await fetch((process.env.INTERNAL_API_URL||'http://api:8000')+'/api/v1/auth/logout',{method:'POST',headers:{'X-API-Key':process.env.API_KEY||'','X-Admin-Session':token}}).catch(()=>{});
 const out=NextResponse.json({ok:true});out.cookies.delete('edge_session');return out;
}
