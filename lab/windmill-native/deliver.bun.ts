export async function main(operation: string, verdict: string) {
  const res = await fetch('http://127.0.0.1:8501/deliver/'+operation, {method:'POST',body:JSON.stringify({verdict})})
  if (!res.ok) throw Error('Delivery refused ' + res.status)
  return res.json()
}
