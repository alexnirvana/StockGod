import * as React from 'react'
import { Slot } from '@radix-ui/react-slot'
import { cva, type VariantProps } from 'class-variance-authority'
import { clsx } from 'clsx'
import { twMerge } from 'tailwind-merge'

const buttonVariants = cva('button', { variants: { variant: { default: 'primary', secondary: 'secondary', ghost: 'ghost', danger: 'danger' }, size: { default: '', sm: 'small', icon: 'icon-button' } }, defaultVariants: { variant: 'default', size: 'default' } })
export function Button({ className, variant, size, asChild = false, ...props }: React.ComponentProps<'button'> & VariantProps<typeof buttonVariants> & { asChild?: boolean }) {
  const Comp = asChild ? Slot : 'button'
  return <Comp className={twMerge(clsx(buttonVariants({ variant, size }), className))} {...props} />
}

