const BASE=process.env.INTERNAL_API_URL||'http://api:8000';
export async function load(path){try{const r=await fetch(BASE+path,{headers:{'X-API-Key':process.env.API_KEY||''},cache:'no-store'});return r.ok?await r.json():null;}catch{return null;}}
export function heading(title,subtitle){return {title,subtitle};}
