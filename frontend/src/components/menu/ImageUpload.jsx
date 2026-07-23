import { useState, useRef } from 'react';
import { Upload, X, Loader2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { toast } from 'sonner';
import { API } from '@/App';
import axios from 'axios';
import { ImageCropperDialog } from './ImageCropperDialog';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;

export function ImageUpload({ value, onChange }) {
  const [uploading, setUploading] = useState(false);
  const [cropSrc, setCropSrc] = useState(null);     // data URL передаваемая в cropper
  const [cropOpen, setCropOpen] = useState(false);
  const [origName, setOrigName] = useState('image');
  const fileInputRef = useRef(null);

  // Read the file into a data URL and open the cropper.
  const handleFileSelect = (e) => {
    const file = e.target.files?.[0];
    // reset the input so re-selecting the same file re-triggers onChange
    if (e.target) e.target.value = '';
    if (!file) return;

    const allowedTypes = ['image/jpeg', 'image/png', 'image/gif', 'image/webp'];
    if (!allowedTypes.includes(file.type)) {
      toast.error('Недопустимый формат. Разрешены: JPG, PNG, GIF, WebP');
      return;
    }
    if (file.size > 15 * 1024 * 1024) {
      toast.error('Файл слишком большой. Максимум 15MB');
      return;
    }

    const reader = new FileReader();
    reader.onload = () => {
      setCropSrc(reader.result);
      setOrigName(file.name || 'image');
      setCropOpen(true);
    };
    reader.onerror = () => toast.error('Не удалось прочитать файл');
    reader.readAsDataURL(file);
  };

  // Called by ImageCropperDialog once the user confirms.
  const uploadCroppedBlob = async (blob, filename) => {
    setUploading(true);
    try {
      const fd = new FormData();
      fd.append('file', blob, filename || 'image.jpg');
      const response = await axios.post(`${API}/upload`, fd, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });
      const imageUrl = `${BACKEND_URL}${response.data.url}`;
      onChange(imageUrl);
      toast.success('Изображение загружено');
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Ошибка загрузки');
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className="space-y-2">
      <Label>Изображение</Label>
      
      {value ? (
        <div className="relative">
          <img 
            src={value} 
            alt="Preview" 
            className="w-full h-40 object-cover rounded-lg border border-border"
          />
          <Button
            variant="destructive"
            size="icon"
            className="absolute top-2 right-2 h-8 w-8 rounded-full"
            onClick={() => onChange('')}
          >
            <X className="w-4 h-4" />
          </Button>
        </div>
      ) : (
        <div 
          className="border-2 border-dashed border-border rounded-lg p-6 text-center cursor-pointer hover:border-mint-500 hover:bg-mint-50/50 dark:hover:bg-mint-900/10 transition-colors"
          onClick={() => fileInputRef.current?.click()}
        >
          {uploading ? (
            <div className="flex flex-col items-center gap-2">
              <Loader2 className="w-8 h-8 text-mint-500 animate-spin" />
              <p className="text-sm text-muted-foreground">Загрузка...</p>
            </div>
          ) : (
            <div className="flex flex-col items-center gap-2">
              <Upload className="w-8 h-8 text-muted-foreground" />
              <p className="text-sm text-muted-foreground">
                Нажмите для загрузки изображения
              </p>
              <p className="text-xs text-muted-foreground">
                JPG, PNG, GIF, WebP до 15MB
              </p>
            </div>
          )}
        </div>
      )}
      
      <input
        ref={fileInputRef}
        type="file"
        accept="image/jpeg,image/png,image/gif,image/webp"
        className="hidden"
        onChange={handleFileSelect}
        disabled={uploading}
      />
      
      <div className="flex items-center gap-2">
        <Input
          placeholder="Или введите URL изображения"
          value={value}
          onChange={(e) => onChange(e.target.value)}
          className="text-sm"
        />
      </div>

      <ImageCropperDialog
        open={cropOpen}
        onOpenChange={(v) => {
          setCropOpen(v);
          if (!v) setCropSrc(null); // release base64 memory when closed
        }}
        imageSrc={cropSrc}
        filename={origName}
        onCropped={uploadCroppedBlob}
      />
    </div>
  );
}
