import { useMemo } from 'react'
import {
  useReactTable,
  getCoreRowModel,
  flexRender,
  createColumnHelper,
  getSortedRowModel,
  type SortingState,
} from '@tanstack/react-table'
import type { Story } from '../types'
import { useState } from 'react'

const columnHelper = createColumnHelper<Story>()

export default function StoryTable({ stories }: { stories: Story[] }) {
  const [sorting, setSorting] = useState<SortingState>([])

  const columns = useMemo(
    () => [
      columnHelper.accessor('title', { header: 'Title' }),
      columnHelper.accessor('story_points', { header: 'Points' }),
      columnHelper.accessor('business_value', { header: 'Value' }),
      columnHelper.accessor('risk_score', { header: 'Risk' }),
      columnHelper.accessor('required_skill', { header: 'Skill' }),
      columnHelper.accessor('status', { header: 'Status' }),
    ],
    [],
  )

  const table = useReactTable({
    data: stories,
    columns,
    state: { sorting },
    onSortingChange: setSorting,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
  })

  return (
    <div className="table-wrap">
    <table className="table">
      <thead>
        {table.getHeaderGroups().map((hg) => (
          <tr key={hg.id}>
            {hg.headers.map((header) => (
              <th
                key={header.id}
                onClick={header.column.getToggleSortingHandler()}
                style={{ cursor: 'pointer', userSelect: 'none' }}
              >
                {flexRender(header.column.columnDef.header, header.getContext())}
                {header.column.getIsSorted() === 'asc' ? ' ▲' : header.column.getIsSorted() === 'desc' ? ' ▼' : ''}
              </th>
            ))}
          </tr>
        ))}
      </thead>
      <tbody>
        {table.getRowModel().rows.map((row) => (
          <tr key={row.id}>
            {row.getVisibleCells().map((cell) => (
              <td key={cell.id}>{flexRender(cell.column.columnDef.cell ?? (() => String(cell.getValue() ?? '')), cell.getContext())}</td>
            ))}
          </tr>
        ))}
      </tbody>
    </table>
    </div>
  )
}
