import { BarChart, Bar, LineChart, Line, XAxis, YAxis, Tooltip, CartesianGrid, ResponsiveContainer } from 'recharts'

export function CapacityBarChart({ values }: { values: number[] }) {
  const data = values.map((v, i) => ({ sprint: `S${i + 1}`, value: v }))
  return <ResponsiveContainer width="100%" height={240}><BarChart data={data}><CartesianGrid strokeDasharray="3 3" stroke="#d3e0d7" /><XAxis dataKey="sprint" /><YAxis /><Tooltip /><Bar dataKey="value" fill="#ea580c" /></BarChart></ResponsiveContainer>
}

export function VelocityLineChart({ values }: { values: number[] }) {
  const data = values.map((v, i) => ({ sprint: `S${i + 1}`, velocity: v }))
  return <ResponsiveContainer width="100%" height={240}><LineChart data={data}><CartesianGrid strokeDasharray="3 3" stroke="#d3e0d7" /><XAxis dataKey="sprint" /><YAxis /><Tooltip /><Line type="monotone" dataKey="velocity" stroke="#0f766e" /></LineChart></ResponsiveContainer>
}
