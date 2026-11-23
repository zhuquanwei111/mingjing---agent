export async function main(operation: string) {
  const product = 'http://127.0.0.1:8501'
  const provider = 'http://127.0.0.1:8502'
  const job = process.env.WM_JOB_ID
  async function post(url: string) {
    const res = await fetch(url, {method:'POST',body:JSON.stringify({job})})
    if (!res.ok) throw Error('HTTP ' + res.status)
    return res.json()
  }
  const claim = await post(product+'/enter/'+operation)
  if (claim.send) await post(provider+'/send/'+operation)
  for (;;) {
    const result = await post(product+'/reconcile/'+operation)
    if (result.receipt) return result.receipt
    await Bun.sleep(400)
  }
}
