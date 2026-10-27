import {NextResponse} from 'next/server';
export async function middleware(request){
 const path=request.nextUrl.pathname;
 if(path==='/login'){const h=new Headers(request.headers);h.set('x-edge-login','1');return NextResponse.next({request:{headers:h}});}
 if(path.startsWith('/api/auth/'))return NextResponse.next();
 const token=request.cookies.get('edge_session')?.value;
 if(!token)return NextResponse.redirect(new URL('/login',request.url));
 try{
  const r=await fetch((process.env.INTERNAL_API_URL||'http://api:8000')+'/api/v1/auth/session',{headers:{'X-API-Key':process.env.API_KEY||'','X-Admin-Session':token},cache:'no-store',signal:AbortSignal.timeout(3500)});
  if(r.ok)return NextResponse.next();
 }catch{}
 const resp=NextResponse.redirect(new URL('/login',request.url));resp.cookies.delete('edge_session');return resp;
}
export const config={matcher:['/((?!_next/static|_next/image|favicon.ico).*)']};
