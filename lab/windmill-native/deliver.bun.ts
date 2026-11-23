export async function main(operation: string) {
  const res = await fetch('http://127.0.0.1:8501/deliver/'+operation, {method:'POST',body:'{}'})
  if (!res.ok) throw Error('Delivery refused ' + res.status)
  return res.json()
}
