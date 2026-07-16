import type { ButtonHTMLAttributes } from 'react'

type ButtonProps = ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: 'default' | 'secondary' | 'ghost'
}

export function Button({ variant = 'default', className = '', ...props }: ButtonProps) {
  const base = 'btn'
  const variantClass = variant === 'secondary' ? 'secondary' : variant === 'ghost' ? 'ghost' : ''
  const classes = [base, variantClass, className].filter(Boolean).join(' ')

  return <button className={classes} {...props} />
}
