import { apiFetch } from '@/services/http'
import { useAuthStore } from '@/features/auth/stores/auth'
export interface TrainingMetrics { ctl:number; atl:number; tsb:number; tssToday:number; points:Array<{date:string;tss:number}> }
function expWeighted(a:number,t:number,d:number){const k=2/(d+1);return a*(1-k)+t*k}
function estimateTss(a:any):number{
  if(a.tss!=null) return Number(a.tss)
  if(a.hr_tss!=null) return Number(a.hr_tss)
  if(a.trimp!=null) return Number(a.trimp)
  const hrs = (a.total_timer_time ?? a.total_elapsed_time ?? 0)/3600
  if(hrs<=0) return 0
  const rpeFactor = a.workout_rpe ? (a.workout_rpe/50) : 1
  const perHour = Math.max(20, Math.min(150, 60*rpeFactor))
  return Math.round(hrs*perHour)
}
export async function fetchTrainingMetrics(): Promise<TrainingMetrics>{
  let list:any[]=[]
  try{
    const auth = useAuthStore() as any
    const userId = auth.userId ?? auth.user?.value?.id ?? null
    if(userId){
      const res:any = await apiFetch('/activities/user/'+userId+'?num_records=100&page_number=1')
      list = Array.isArray(res) ? res : (res.records ?? res ?? [])
    }
  }catch{}
  if(list.length===0){
    try{
      const res:any = await (apiFetch as any)('/activities?num_records=100&page_number=1')
      list = Array.isArray(res) ? res : (res.records ?? [])
    }catch{ list=[] }
  }
  const byDate:Record<string,number>={}
  for(const a of list){
    const d=String(a.start_time ?? a.start_time_tz_applied ?? '').slice(0,10);
    if(!d) continue;
    const tss=estimateTss(a);
    byDate[d]=(byDate[d] ?? 0)+(Number.isFinite(tss)?Number(tss):0);
  }
  const dates=Array.from({length:60},(_,i)=>{const d=new Date(); d.setDate(d.getDate()-(59-i)); return d.toISOString().slice(0,10)});
  let ctl=0,atl=0;
  const points:Array<{date:string;tss:number}>=[]
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
