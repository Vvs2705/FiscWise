import { useParams, useNavigate } from 'react-router-dom';
import { ClientDetailCockpit } from '@/features/clients/components/ClientDetailCockpit';

export default function ClientDetailPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();

  const handleClose = () => {
    navigate('/clientes');
  };

  if (!id) {
    return (
      <div className="flex h-screen items-center justify-center bg-background text-foreground">
        <div className="text-center">
          <p className="text-muted-foreground text-sm">Identificador do cliente não fornecido.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="h-full w-full bg-background flex flex-col">
      <ClientDetailCockpit clientId={id} onClose={handleClose} />
    </div>
  );
}
