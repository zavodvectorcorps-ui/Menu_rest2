import { useState, useRef } from 'react';
import { Upload, X, Loader2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { toast } from 'sonner';
import { API } from '@/App';
import axios from 'axios';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;

export function ImageUpload({ value, onChange }) {
  const [uploading, setUploading] = useState(false);
  const fileInputRef = useRef(null);

  const handleFileSelect = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;

    const allowedTypes = ['image/jpeg', 'image/png', 'image/gif', 'image/webp'];
    if (!allowedTypes.includes(file.type)) {
      toast.error('Недопустимый формат. Разрешены: JPG, PNG, GIF, WebP');
      return;
    }

    if (file.size > 5 * 1024 * 1024) {
      toast.error('Файл слишком большой. Максимум 5MB');
      return;
    }

    setUploading(true);
    const formData = new FormData();
    formData.append('file', file);

    try {
      const response = await axios.post(`${API}/upload`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
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
                Нажмите для загрузки или перетащите файл
              </p>
              <p className="text-xs text-muted-foreground">
                JPG, PNG, GIF, WebP до 5MB
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
    </div>
  );
}
