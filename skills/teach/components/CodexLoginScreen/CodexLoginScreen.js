export function connectCodexLogin({authUrl='/api/codex/auth',loginUrl='/api/codex/login',redirectUrl='/',pollMs=2500}={}){
  const button=document.getElementById('codexLogin')
  const status=document.getElementById('codexLoginStatus')
  const panel=document.getElementById('codexLoginPanel')
  const link=document.getElementById('codexDeviceLink')
  const code=document.getElementById('codexDeviceCode')
  let polling=null
  const stop=()=>{if(polling){clearInterval(polling);polling=null}}
  const check=async()=>{
    const response=await fetch(authUrl)
    const auth=await response.json()
    if(auth.authenticated){stop();location.assign(redirectUrl);return true}
    if(auth.status==='error'){stop();status.textContent=auth.error||'Codex login failed.';button.disabled=false}
    return false
  }
  button.addEventListener('click',async()=>{
    button.disabled=true
    status.textContent='Preparing Codex login…'
    try{
      const response=await fetch(loginUrl,{method:'POST'})
      const auth=await response.json()
      if(!response.ok)throw new Error(auth.error||'Could not start Codex login.')
      if(auth.authenticated){location.assign(redirectUrl);return}
      if(!auth.user_code||!auth.verification_url)throw new Error('Codex did not provide a device code.')
      link.href=auth.verification_url
      code.textContent=auth.user_code
      panel.hidden=false
      status.textContent='Open the device page, enter the code, and approve the login.'
      if(!polling)polling=setInterval(()=>check().catch(()=>{}),pollMs)
    }catch(error){status.textContent=error.message||'Could not start Codex login.';button.disabled=false}
  })
  check().catch(()=>{})
  return{check,stop}
}
