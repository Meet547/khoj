'use client';
import * as Dialog from '@radix-ui/react-dialog';
import { X, ArrowUpRight } from 'lucide-react';
import { useTranslations } from 'next-intl';
import Link from 'next/link';
import type { ButtonHTMLAttributes, ReactNode } from 'react';
import { cn } from '@/lib/utils/index';
export function Button({
  children,
  className,
  variant = 'dark',
  ...props
}: ButtonHTMLAttributes<HTMLButtonElement> & { variant?: 'dark' | 'outline' | 'plain' }) {
  return (
    <button className={cn('button', variant, className)} {...props}>
      {children}
    </button>
  );
}
export function ActionLink({
  href,
  children,
  variant = 'dark',
  className,
  arrow = false,
}: {
  href: string;
  children: ReactNode;
  variant?: 'dark' | 'outline' | 'plain';
  className?: string;
  arrow?: boolean;
}) {
  return (
    <Link href={href} className={cn('button', variant, className)}>
      {children}
      {arrow && <ArrowUpRight size={18} />}
    </Link>
  );
}
export function Modal({
  open,
  onOpenChange,
  title,
  description,
  children,
  hideClose = false,
}: {
  hideClose?: boolean;
  open: boolean;
  onOpenChange: (v: boolean) => void;
  title: string;
  description?: string;
  children: ReactNode;
}) {
  const t = useTranslations();
  return (
    <Dialog.Root open={open} onOpenChange={onOpenChange}>
      <Dialog.Portal>
        <Dialog.Overlay className="modal-overlay" />
        <Dialog.Content className="modal-content">
          <Dialog.Title className="modal-title">{title}</Dialog.Title>
          <Dialog.Description className={description ? 'modal-desc' : 'sr-only'}>
            {description || title}
          </Dialog.Description>
          {!hideClose && (
            <Dialog.Close className="icon-button modal-close" aria-label={t('close')}>
              <X size={20} />
            </Dialog.Close>
          )}
          {children}
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}
export function ErrorBox({ message }: { message: string }) {
  return (
    <div role="alert" className="error-box">
      {message}
    </div>
  );
}
