export function connectStateEvents({loadState,getOpenContext,restoreOpenContext,pollMs=2500}){
  let version=0
  let refreshing=false
  let queued=0
  let polling=null
  let events=null
  const refresh=async incoming=>{
    queued=Math.max(queued,Number(incoming)||version+1)
    if(refreshing)return
    refreshing=true
    const context=getOpenContext()
    try{
      while(queued>version){version=queued;await loadState()}
      await restoreOpenContext(context)
    }finally{refreshing=false}
  }
  const startPolling=()=>{
    if(polling)return
    polling=setInterval(()=>refresh(version+1).catch(()=>{}),pollMs)
  }
  if(window.EventSource){
    events=new EventSource('/api/events')
    events.addEventListener('state',event=>{
      try{refresh(JSON.parse(event.data).version).catch(startPolling)}catch(error){startPolling()}
    })
    events.onerror=startPolling
  }else startPolling()
  return{close(){events?.close();if(polling)clearInterval(polling)},startPolling}
}
