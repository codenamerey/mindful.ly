export function connectLessonGraphRevision(root,{capture,pollMs=1000}={}){
  const lessonId=root.dataset.lessonId
  const graphIndex=root.dataset.graphIndex
  const trigger=root.querySelector('.lesson-graph-revision__trigger')
  const form=root.querySelector('form')
  const output=root.querySelector('output')
  const key=`lesson-graph-revision:${lessonId}:${graphIndex}`
  const request=async(method,url,body)=>{
    const response=await fetch(url,{method,body})
    const value=await response.json()
    if(!response.ok)throw new Error(value.error||'Graph revision failed')
    return value
  }
  const poll=async jobId=>{
    localStorage.setItem(key,jobId)
    while(true){
      const job=await request('GET',`/api/lesson-graph-revisions/${encodeURIComponent(jobId)}`)
      if(job.status==='error')throw new Error(job.error||'Graph revision failed')
      if(job.status==='complete'){
        const parsed=new DOMParser().parseFromString(job.svg,'image/svg+xml')
        if(parsed.querySelector('parsererror')||parsed.documentElement.localName!=='svg')throw new Error('Invalid revised graph')
        root.querySelector('svg').replaceWith(document.importNode(parsed.documentElement,true))
        localStorage.removeItem(key)
        output.textContent='Graph improved.'
        return
      }
      await new Promise(resolve=>setTimeout(resolve,pollMs))
    }
  }
  trigger.addEventListener('click',()=>{form.hidden=!form.hidden;trigger.setAttribute('aria-expanded',String(!form.hidden));if(!form.hidden)form.querySelector('textarea').focus()})
  form.querySelector('[data-cancel]').addEventListener('click',()=>{form.hidden=true;trigger.setAttribute('aria-expanded','false')})
  form.addEventListener('submit',async event=>{
    event.preventDefault()
    trigger.disabled=true
    output.textContent='Rewriting…'
    try{
      const data=new FormData()
      data.set('message',form.querySelector('textarea').value.trim())
      if(capture)data.set('screenshot',await capture(root.querySelector('svg')),'graph.png')
      const job=await request('POST',`/api/lessons/${encodeURIComponent(lessonId)}/graphs/${graphIndex}/revise`,data)
      await poll(job.job_id)
    }catch(error){localStorage.removeItem(key);output.textContent=error.message}
    finally{trigger.disabled=false}
  })
  const existing=localStorage.getItem(key)
  if(existing)poll(existing).catch(error=>{localStorage.removeItem(key);output.textContent=error.message})
}
