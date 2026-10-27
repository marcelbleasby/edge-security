import {NextResponse} from 'next/server';
export async function POST(req){
 const origin=req.headers.get('origin');if(origin&&origin!==new URL(req.url).origin)return NextResponse.json({error:'Origem inválida'},{status:403});
 const token=req.cookies.get('edge_session')?.value;
 if(token)await fetch((process.env.INTERNAL_API_URL||'http://api:8000')+'/api/v1/auth/logout',{method:'POST',headers:{'X-API-Key':process.env.API_KEY||'','X-Admin-Session':token}}).catch(()=>{});
 const out=NextResponse.json({ok:true});out.cookies.delete('edge_session');return out;
}
