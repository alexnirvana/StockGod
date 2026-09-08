import { t, useLocale } from '../../i18n'
import * as DialogPrimitive from '@radix-ui/react-dialog';
import { X } from 'lucide-react';
import type { ReactNode } from 'react';
export function Dialog({ open, onOpenChange, title, description, children, wide = false }: {
    open: boolean;
    onOpenChange: (open: boolean) => void;
    title: string;
    description: string;
    children: ReactNode;
    wide?: boolean;
}) {
    useLocale();
    return <DialogPrimitive.Root open={open} onOpenChange={onOpenChange}><DialogPrimitive.Portal>
    <DialogPrimitive.Overlay className="dialog-overlay"/>
    <DialogPrimitive.Content className={'dialog-content' + (wide ? ' dialog-wide' : '')}>
      <DialogPrimitive.Title>{title}</DialogPrimitive.Title>
      <DialogPrimitive.Description>{description}</DialogPrimitive.Description>
      <DialogPrimitive.Close className="dialog-close" aria-label={t("关闭")}><X size={20}/></DialogPrimitive.Close>
      {children}
    </DialogPrimitive.Content>
  </DialogPrimitive.Portal></DialogPrimitive.Root>;
}
