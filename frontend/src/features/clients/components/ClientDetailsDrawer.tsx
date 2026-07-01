import { Drawer, DrawerContent } from '@/components/ui/Drawer';
import { ClientDetailCockpit } from './ClientDetailCockpit';

interface ClientDetailsDrawerProps {
  clientId: string | null;
  isOpen: boolean;
  onClose: () => void;
}

export function ClientDetailsDrawer({ clientId, isOpen, onClose }: ClientDetailsDrawerProps) {
  return (
    <Drawer open={isOpen} onOpenChange={(open) => !open && onClose()} direction="right">
      <DrawerContent className="fixed inset-y-0 right-0 bottom-0 top-0 mt-0 h-full w-full max-w-4xl rounded-t-none border-l border-border bg-card shadow-token flex flex-col">
        {clientId && (
          <ClientDetailCockpit clientId={clientId} onClose={onClose} />
        )}
      </DrawerContent>
    </Drawer>
  );
}
