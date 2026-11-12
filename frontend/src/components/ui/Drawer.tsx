import { ComponentProps, HTMLAttributes } from 'react';
import { Drawer as VaulDrawer } from 'vaul';
import { cn } from '@/lib/utils';

export function Drawer({
  // Sem escala do fundo (DESIGN.md §7: nada de scale fora do toque em botões)
  shouldScaleBackground = false,
  ...props
}: ComponentProps<typeof VaulDrawer.Root>) {
  return (
    <VaulDrawer.Root
      shouldScaleBackground={shouldScaleBackground}
      {...props}
    />
  );
}

export const DrawerTrigger = VaulDrawer.Trigger;

export const DrawerPortal = VaulDrawer.Portal;

export const DrawerClose = VaulDrawer.Close;

export function DrawerOverlay({
  className,
  ...props
}: ComponentProps<typeof VaulDrawer.Overlay>) {
  return (
    <VaulDrawer.Overlay
      className={cn('fixed inset-0 z-50 bg-foreground/40', className)}
      {...props}
    />
  );
}

export function DrawerContent({
  className,
  children,
  ...props
}: ComponentProps<typeof VaulDrawer.Content>) {
  return (
    <DrawerPortal>
      <DrawerOverlay />
      <VaulDrawer.Content
        className={cn(
          'fixed inset-x-0 bottom-0 z-50 mt-24 flex h-auto max-h-[92vh] flex-col rounded-t-lg border border-border bg-card text-card-foreground shadow-lg outline-none',
          className
        )}
        {...props}
      >
        <div className="mx-auto mt-3 h-1.5 w-10 shrink-0 rounded-full bg-muted-foreground/30" aria-hidden="true" />
        {children}
      </VaulDrawer.Content>
    </DrawerPortal>
  );
}

export function DrawerHeader({
  className,
  ...props
}: HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={cn('grid gap-1.5 p-4 text-center sm:text-left', className)}
      {...props}
    />
  );
}

export function DrawerFooter({
  className,
  ...props
}: HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={cn('mt-auto flex flex-col gap-2 p-4', className)}
      {...props}
    />
  );
}

export function DrawerTitle({
  className,
  ...props
}: ComponentProps<typeof VaulDrawer.Title>) {
  return (
    <VaulDrawer.Title
      className={cn('text-base font-semibold leading-6 text-foreground', className)}
      {...props}
    />
  );
}

export function DrawerDescription({
  className,
  ...props
}: ComponentProps<typeof VaulDrawer.Description>) {
  return (
    <VaulDrawer.Description
      className={cn('text-sm text-muted-foreground', className)}
      {...props}
    />
  );
}
