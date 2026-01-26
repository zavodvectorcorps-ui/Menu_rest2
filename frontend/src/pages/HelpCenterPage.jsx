import { useState, useEffect } from 'react';
import { Search, ChevronDown, ChevronUp, HelpCircle, Book, Lightbulb, Settings, Bot, Menu as MenuIcon } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Accordion, AccordionContent, AccordionItem, AccordionTrigger } from '@/components/ui/accordion';
import { Badge } from '@/components/ui/badge';
import { toast } from 'sonner';
import { API } from '@/App';
import axios from 'axios';

const categoryIcons = {
  'Меню': MenuIcon,
  'Столы': Settings,
  'Настройки': Settings,
  'Интеграции': Bot,
  'default': HelpCircle
};

const categoryColors = {
  'Меню': 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-400',
  'Столы': 'bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-400',
  'Настройки': 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400',
  'Интеграции': 'bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400',
  'default': 'bg-gray-100 text-gray-700 dark:bg-gray-900/30 dark:text-gray-400'
};

export default function HelpCenterPage() {
  const [faqs, setFaqs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');

  useEffect(() => {
    const fetchFaqs = async () => {
      try {
        const response = await axios.get(`${API}/faq`);
        setFaqs(response.data);
      } catch (error) {
        toast.error('Ошибка загрузки FAQ');
      } finally {
        setLoading(false);
      }
    };

    fetchFaqs();
  }, []);

  const filteredFaqs = faqs.filter(faq => {
    if (!searchQuery) return true;
    return faq.question.toLowerCase().includes(searchQuery.toLowerCase()) ||
           faq.answer.toLowerCase().includes(searchQuery.toLowerCase());
  });

  // Group FAQs by category
  const groupedFaqs = filteredFaqs.reduce((acc, faq) => {
    const category = faq.category || 'Другое';
    if (!acc[category]) acc[category] = [];
    acc[category].push(faq);
    return acc;
  }, {});

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="spinner" />
      </div>
    );
  }

  return (
    <div className="space-y-6 animate-fadeIn" data-testid="help-center-page">
      {/* Header */}
      <div className="text-center max-w-2xl mx-auto">
        <div className="w-16 h-16 rounded-2xl bg-mint-500 flex items-center justify-center mx-auto mb-4 shadow-lg shadow-mint-500/30">
          <Book className="w-8 h-8 text-white" />
        </div>
        <h1 className="text-3xl font-heading font-bold text-foreground mb-2">Справочный центр</h1>
        <p className="text-muted-foreground">
          Найдите ответы на часто задаваемые вопросы по работе с кабинетом ресторана
        </p>
      </div>

      {/* Search */}
      <div className="max-w-xl mx-auto">
        <div className="relative">
          <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-muted-foreground" />
          <Input
            placeholder="Поиск по вопросам..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="pl-12 h-12 rounded-full text-base"
            data-testid="faq-search-input"
          />
        </div>
      </div>

      {/* Quick Links */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 max-w-3xl mx-auto">
        {[
          { title: 'Меню', icon: MenuIcon, count: faqs.filter(f => f.category === 'Меню').length },
          { title: 'Столы', icon: Settings, count: faqs.filter(f => f.category === 'Столы').length },
          { title: 'Настройки', icon: Settings, count: faqs.filter(f => f.category === 'Настройки').length },
          { title: 'Интеграции', icon: Bot, count: faqs.filter(f => f.category === 'Интеграции').length },
        ].map((item, idx) => {
          const Icon = item.icon;
          return (
            <Card 
              key={idx} 
              className="border-none shadow-sm hover:shadow-md transition-shadow cursor-pointer"
              onClick={() => setSearchQuery(item.title)}
              data-testid={`quick-link-${item.title.toLowerCase()}`}
            >
              <CardContent className="p-4 text-center">
                <div className={`w-10 h-10 rounded-xl ${categoryColors[item.title] || categoryColors.default} flex items-center justify-center mx-auto mb-2`}>
                  <Icon className="w-5 h-5" />
                </div>
                <h3 className="font-medium text-foreground">{item.title}</h3>
                <p className="text-xs text-muted-foreground">{item.count} статей</p>
              </CardContent>
            </Card>
          );
        })}
      </div>

      {/* FAQs */}
      <div className="max-w-3xl mx-auto space-y-6" data-testid="faq-list">
        {Object.keys(groupedFaqs).length === 0 ? (
          <Card className="border-none shadow-md">
            <CardContent className="py-12 text-center">
              <Lightbulb className="w-12 h-12 mx-auto text-muted-foreground/50 mb-4" />
              <p className="text-muted-foreground">
                {searchQuery ? 'По вашему запросу ничего не найдено' : 'FAQ пока нет'}
              </p>
            </CardContent>
          </Card>
        ) : (
          Object.entries(groupedFaqs).map(([category, items]) => {
            const Icon = categoryIcons[category] || categoryIcons.default;
            return (
              <Card key={category} className="border-none shadow-md overflow-hidden">
                <CardHeader className="pb-0">
                  <div className="flex items-center gap-3">
                    <div className={`w-8 h-8 rounded-lg ${categoryColors[category] || categoryColors.default} flex items-center justify-center`}>
                      <Icon className="w-4 h-4" />
                    </div>
                    <CardTitle className="font-heading text-lg">{category}</CardTitle>
                    <Badge variant="secondary" className="ml-auto">{items.length}</Badge>
                  </div>
                </CardHeader>
                <CardContent className="pt-4">
                  <Accordion type="single" collapsible className="w-full">
                    {items.map((faq, idx) => (
                      <AccordionItem 
                        key={faq.id} 
                        value={faq.id}
                        className="border-b border-border/50 last:border-0"
                        data-testid={`faq-item-${faq.id}`}
                      >
                        <AccordionTrigger className="text-left hover:no-underline py-4">
                          <span className="font-medium text-foreground pr-4">{faq.question}</span>
                        </AccordionTrigger>
                        <AccordionContent className="text-muted-foreground pb-4">
                          {faq.answer}
                        </AccordionContent>
                      </AccordionItem>
                    ))}
                  </Accordion>
                </CardContent>
              </Card>
            );
          })
        )}
      </div>

      {/* Contact Support */}
      <Card className="max-w-3xl mx-auto border-none shadow-md bg-accent/50" data-testid="contact-support-card">
        <CardContent className="p-6 text-center">
          <HelpCircle className="w-10 h-10 text-mint-500 mx-auto mb-3" />
          <h3 className="font-heading font-semibold text-foreground mb-2">
            Не нашли ответ на свой вопрос?
          </h3>
          <p className="text-muted-foreground mb-4">
            Свяжитесь с нашей службой поддержки, и мы поможем вам разобраться
          </p>
          <a 
            href="/admin/support" 
            className="inline-flex items-center justify-center px-6 py-2 bg-mint-500 text-white rounded-full font-medium hover:bg-mint-600 transition-colors"
            data-testid="contact-support-btn"
          >
            Написать в поддержку
          </a>
        </CardContent>
      </Card>
    </div>
  );
}
