import { useState } from 'react';
import { Send, Mail, MessageSquare, Phone, Clock, CheckCircle } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { toast } from 'sonner';
import { API } from '@/App';
import axios from 'axios';

export default function SupportPage() {
  const [form, setForm] = useState({
    subject: '',
    description: '',
    contact_email: ''
  });
  const [submitting, setSubmitting] = useState(false);
  const [submitted, setSubmitted] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    if (!form.subject || !form.description || !form.contact_email) {
      toast.error('Заполните все обязательные поля');
      return;
    }

    setSubmitting(true);
    try {
      await axios.post(`${API}/support-tickets`, form);
      setSubmitted(true);
      toast.success('Обращение отправлено');
    } catch (error) {
      toast.error('Ошибка отправки обращения');
    } finally {
      setSubmitting(false);
    }
  };

  if (submitted) {
    return (
      <div className="min-h-[60vh] flex items-center justify-center animate-fadeIn" data-testid="support-success">
        <Card className="border-none shadow-lg max-w-md w-full">
          <CardContent className="p-8 text-center">
            <div className="w-16 h-16 rounded-full bg-emerald-100 dark:bg-emerald-900/30 flex items-center justify-center mx-auto mb-4">
              <CheckCircle className="w-8 h-8 text-emerald-500" />
            </div>
            <h2 className="text-2xl font-heading font-bold text-foreground mb-2">
              Обращение отправлено!
            </h2>
            <p className="text-muted-foreground mb-6">
              Мы получили ваше сообщение и свяжемся с вами в ближайшее время.
            </p>
            <Button
              onClick={() => { setSubmitted(false); setForm({ subject: '', description: '', contact_email: '' }); }}
              className="bg-mint-500 hover:bg-mint-600 rounded-full"
              data-testid="new-ticket-btn"
            >
              Отправить ещё одно обращение
            </Button>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="space-y-6 animate-fadeIn" data-testid="support-page">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-heading font-bold text-foreground">Поддержка</h1>
        <p className="text-muted-foreground">Свяжитесь с нами, если у вас есть вопросы или проблемы</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Contact Form */}
        <Card className="lg:col-span-2 border-none shadow-md" data-testid="support-form-card">
          <CardHeader>
            <CardTitle className="font-heading">Форма обращения</CardTitle>
            <CardDescription>Опишите вашу проблему или вопрос, и мы постараемся помочь</CardDescription>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleSubmit} className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="subject">Тема обращения *</Label>
                <Select
                  value={form.subject}
                  onValueChange={(value) => setForm({ ...form, subject: value })}
                >
                  <SelectTrigger id="subject" data-testid="subject-select">
                    <SelectValue placeholder="Выберите тему" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="technical">Техническая проблема</SelectItem>
                    <SelectItem value="billing">Вопрос по оплате</SelectItem>
                    <SelectItem value="feature">Предложение по улучшению</SelectItem>
                    <SelectItem value="integration">Помощь с интеграцией</SelectItem>
                    <SelectItem value="other">Другое</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              <div className="space-y-2">
                <Label htmlFor="email">Email для связи *</Label>
                <Input
                  id="email"
                  type="email"
                  value={form.contact_email}
                  onChange={(e) => setForm({ ...form, contact_email: e.target.value })}
                  placeholder="your@email.com"
                  data-testid="email-input"
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="description">Описание *</Label>
                <Textarea
                  id="description"
                  value={form.description}
                  onChange={(e) => setForm({ ...form, description: e.target.value })}
                  placeholder="Подробно опишите вашу проблему или вопрос..."
                  rows={6}
                  data-testid="description-input"
                />
              </div>

              <Button 
                type="submit" 
                className="w-full bg-mint-500 hover:bg-mint-600 rounded-full"
                disabled={submitting}
                data-testid="submit-ticket-btn"
              >
                {submitting ? (
                  <>
                    <div className="spinner mr-2" />
                    Отправка...
                  </>
                ) : (
                  <>
                    <Send className="w-4 h-4 mr-2" />
                    Отправить обращение
                  </>
                )}
              </Button>
            </form>
          </CardContent>
        </Card>

        {/* Contact Info */}
        <div className="space-y-4">
          <Card className="border-none shadow-md" data-testid="contact-info-card">
            <CardHeader>
              <CardTitle className="font-heading text-lg">Контакты</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex items-start gap-3">
                <div className="w-10 h-10 rounded-xl bg-mint-100 dark:bg-mint-900/30 flex items-center justify-center flex-shrink-0">
                  <Mail className="w-5 h-5 text-mint-500" />
                </div>
                <div>
                  <p className="font-medium text-foreground">Email</p>
                  <a href="mailto:support@restaurant.ru" className="text-sm text-muted-foreground hover:text-mint-500">
                    support@restaurant.ru
                  </a>
                </div>
              </div>

              <div className="flex items-start gap-3">
                <div className="w-10 h-10 rounded-xl bg-blue-100 dark:bg-blue-900/30 flex items-center justify-center flex-shrink-0">
                  <MessageSquare className="w-5 h-5 text-blue-500" />
                </div>
                <div>
                  <p className="font-medium text-foreground">Telegram</p>
                  <a href="https://t.me/restaurant_support" target="_blank" rel="noopener noreferrer" className="text-sm text-muted-foreground hover:text-mint-500">
                    @restaurant_support
                  </a>
                </div>
              </div>

              <div className="flex items-start gap-3">
                <div className="w-10 h-10 rounded-xl bg-emerald-100 dark:bg-emerald-900/30 flex items-center justify-center flex-shrink-0">
                  <Phone className="w-5 h-5 text-emerald-500" />
                </div>
                <div>
                  <p className="font-medium text-foreground">Телефон</p>
                  <a href="tel:+79991234567" className="text-sm text-muted-foreground hover:text-mint-500">
                    +7 (999) 123-45-67
                  </a>
                </div>
              </div>
            </CardContent>
          </Card>

          <Card className="border-none shadow-md" data-testid="working-hours-card">
            <CardContent className="p-6">
              <div className="flex items-center gap-3 mb-3">
                <div className="w-10 h-10 rounded-xl bg-amber-100 dark:bg-amber-900/30 flex items-center justify-center">
                  <Clock className="w-5 h-5 text-amber-500" />
                </div>
                <p className="font-heading font-semibold text-foreground">Время работы</p>
              </div>
              <div className="space-y-1 text-sm">
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Пн-Пт:</span>
                  <span className="text-foreground">09:00 - 21:00</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Сб-Вс:</span>
                  <span className="text-foreground">10:00 - 18:00</span>
                </div>
              </div>
            </CardContent>
          </Card>

          <Card className="border-none shadow-md bg-mint-50 dark:bg-mint-900/20" data-testid="response-time-card">
            <CardContent className="p-6">
              <p className="text-sm text-mint-700 dark:text-mint-300">
                <strong>Среднее время ответа:</strong> до 2 часов в рабочее время
              </p>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
