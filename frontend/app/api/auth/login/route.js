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
 let body;try{body=await req.json();}catch{return NextResponse.json({error:'Dados inválidos'},{status:400});}
 const response=await fetch((process.env.INTERNAL_API_URL||'http://api:8000')+'/api/v1/auth/login',{method:'POST',headers:{'X-API-Key':process.env.API_KEY||'','Content-Type':'application/json'},body:JSON.stringify({username:String(body.username||''),password:String(body.password||'')}),cache:'no-store'}).catch(()=>null);
 if(!response||!response.ok)return NextResponse.json({error:'Credenciais inválidas ou serviço indisponível'},{status:401});
 const data=await response.json();const out=NextResponse.json({ok:true});
 out.cookies.set('edge_session',data.session,{httpOnly:true,sameSite:'lax',secure:process.env.SESSION_COOKIE_SECURE==='true',path:'/',maxAge:data.expires_in});return out;
}
