import { useState } from 'react';
import { useUploadComprovante } from '../hooks/useGuias';
import { Button } from '@/components/ui/Button';
import { Upload } from 'lucide-react';
import { toast } from 'sonner';

interface GuiaUploadComprovanteProps {
  guideId: string;
  onSuccess?: () => void;
}

export function GuiaUploadComprovante({ guideId, onSuccess }: GuiaUploadComprovanteProps) {
  const upload = useUploadComprovante();
  const [selectedFile, setSelectedFile] = useState<File | null>(null);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      setSelectedFile(e.target.files[0]);
    }
  };

  const handleUpload = async () => {
    if (!selectedFile) return;
    try {
      await upload.mutateAsync({ id: guideId, file: selectedFile });
      toast.success('Comprovante enviado com sucesso!');
      setSelectedFile(null);
      onSuccess?.();
    } catch {
      toast.error('Falha ao enviar comprovante.');
    }
  };

  return (
    <div className="flex flex-col gap-2 p-3 bg-muted/10 border border-border/30 rounded-lg">
      <span className="text-xs font-semibold text-muted-foreground uppercase">
        Anexar Comprovante de Pagamento
      </span>
      <div className="flex flex-wrap items-center gap-3 mt-1">
        <label className="flex-1 min-w-[200px] flex items-center justify-between px-3 py-1.5 bg-background border border-input rounded-md text-xs cursor-pointer hover:bg-muted/10">
          <span className="text-muted-foreground truncate max-w-[180px]">
            {selectedFile ? selectedFile.name : 'Selecionar arquivo (PDF/Imagem)...'}
          </span>
          <input type="file" className="hidden" accept=".pdf,image/*" onChange={handleFileChange} />
          <Upload className="h-3.5 w-3.5 text-muted-foreground" />
        </label>

        <Button
          size="sm"
          onClick={handleUpload}
          disabled={!selectedFile || upload.isPending}
          className="h-8 shrink-0"
        >
          {upload.isPending ? 'Enviando...' : 'Enviar'}
        </Button>
      </div>
    </div>
  );
}
