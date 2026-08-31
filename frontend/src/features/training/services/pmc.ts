import { apiFetch } from '@/services/http'
export interface TrainingMetrics { ctl:number; atl:number; tsb:number; tssToday:number; points:Array<{date:string;tss:number}> }
function expWeighted(a:number,t:number,d:number){const k=2/(d+1);return a*(1-k)+t*k}
export async function fetchTrainingMetrics(): Promise<TrainingMetrics>{
  const res:any = await (apiFetch as any)('/activities?num_records=100&page_number=1').catch(()=>({records:[]}));
  const list:any[] = Array.isArray(res) ? res : (res.records ?? []);
  const byDate:Record<string,number>={};
  for(const a of list){
    const d=String(a.start_time ?? '').slice(0,10);
    if(!d) continue;
    const tss=a.tss ?? a.hr_tss ?? a.trimp ?? 0;
    byDate[d]=(byDate[d] ?? 0)+(Number.isFinite(tss)?Number(tss):0);
  }
  const dates=Array.from({length:60},(_,i)=>{const d=new Date(); d.setDate(d.getDate()-(59-i)); return d.toISOString().slice(0,10)});
  let ctl=0,atl=0;
  const points:Array<{date:string;tss:number}>=[];
  for(const d of dates){
    const tss=byDate[d] ?? 0;
    ctl=expWeighted(ctl,tss,42);
    atl=expWeighted(atl,tss,7);
    points.push({date:d,tss});
  }
  const tsb=ctl-atl;
  const tssToday=byDate[new Date().toISOString().slice(0,10)] ?? 0;
  return {ctl,atl,tsb,tssToday,points};
}
export function formLabel(tsb:number){
  if(tsb>25) return {label:'Пик',color:'text-blue-600'};
  if(tsb>5) return {label:'Свеж',color:'text-green-600'};
  if(tsb>-10) return {label:'Нейтрально',color:'text-yellow-600'};
  if(tsb>-30) return {label:'Утомлен',color:'text-orange-600'};
  return {label:'Перетрен',color:'text-red-600'};
}
