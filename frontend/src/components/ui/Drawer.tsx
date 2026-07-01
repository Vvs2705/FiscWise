import { ComponentProps, HTMLAttributes } from 'react';
import { Drawer as VaulDrawer } from 'vaul';
import { cn } from '@/lib/utils';

export function Drawer({
  shouldScaleBackground = true,
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
      className={cn('fixed inset-0 z-50 bg-black/60 backdrop-blur-[2px]', className)}
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
          'fixed inset-x-0 bottom-0 z-50 mt-24 flex h-auto flex-col rounded-t-[20px] border border-border bg-card/95 text-card-foreground shadow-token backdrop-blur-md outline-none',
          className
        )}
        {...props}
      >
        <div className="mx-auto mt-4 h-1.5 w-12 shrink-0 rounded-full bg-muted-foreground/30" />
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
      className={cn('text-lg font-bold leading-none tracking-tight text-foreground', className)}
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
