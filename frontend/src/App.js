import { useState, useEffect } from "react";
import "@/App.css";
import axios from "axios";
import { Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Toaster, toast } from "sonner";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

function App() {
  const [formData, setFormData] = useState({
    il: "",
    ilce: "",
    mahalle: "",
    ada: "",
    parsel: ""
  });
  
  const [sessionId, setSessionId] = useState(null);
  const [remainingCredits, setRemainingCredits] = useState(5);
  const [analysis, setAnalysis] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  // Initialize session
  useEffect(() => {
    const storedSessionId = localStorage.getItem('sessionId');
    if (storedSessionId) {
      setSessionId(storedSessionId);
      fetchRemainingCredits(storedSessionId);
    } else {
      const newSessionId = `session-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
      localStorage.setItem('sessionId', newSessionId);
      setSessionId(newSessionId);
    }
  }, []);

  const fetchRemainingCredits = async (sid) => {
    try {
      const response = await axios.get(`${API}/remaining-credits/${sid}`);
      setRemainingCredits(response.data.remaining_credits);
    } catch (err) {
      console.error('Error fetching credits:', err);
    }
  };

  const handleInputChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: value
    }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError(null);
    setAnalysis(null);
    
    if (!formData.il || !formData.ilce || !formData.mahalle || !formData.ada || !formData.parsel) {
      toast.error('Lütfen tüm alanları doldurun');
      return;
    }

    setLoading(true);

    try {
      const response = await axios.post(`${API}/analyze-property`, {
        ...formData,
        session_id: sessionId
      });

      setAnalysis(response.data.analysis);
      setRemainingCredits(response.data.remaining_credits);
      toast.success('Analiz tamamlandı!');
    } catch (err) {
      const errorMsg = err.response?.data?.detail || 'Analiz yapılırken bir hata oluştu';
      setError(errorMsg);
      toast.error(errorMsg);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-white">
      <Toaster position="top-center" />
      
      {/* Header */}
      <header className="border-b border-gray-200">
        <div className="container mx-auto px-4 py-4 flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <div data-testid="logo" className="text-xl font-semibold text-black">
              ArsaEkspertizAI
            </div>
          </div>
          <div data-testid="credits-badge" className="bg-black text-white px-4 py-2 rounded-full text-sm font-medium">
            {remainingCredits}/5 Hak Kaldı
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="container mx-auto px-4 py-8 max-w-4xl">
        <div className="mb-8 text-center">
          <h1 className="text-4xl sm:text-5xl font-bold text-black mb-3">
            Arsa İmar Durumu Analizi
          </h1>
          <p className="text-base sm:text-lg text-gray-600">
            Ada ve parsel bilgilerinizi girin, yapay zeka destekli imar analizi alın
          </p>
        </div>

        {/* Form Card */}
        <Card data-testid="analysis-form-card" className="mb-6 border-2 border-black shadow-lg">
          <CardHeader>
            <CardTitle className="text-2xl">Arsa Bilgileri</CardTitle>
            <CardDescription>
              Analiz yapmak istediğiniz arsanın bilgilerini giriniz
            </CardDescription>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleSubmit} className="space-y-4">
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <Label htmlFor="il" className="text-black font-medium">İl</Label>
                  <Input
                    id="il"
                    name="il"
                    data-testid="input-il"
                    placeholder="Örn: Adana"
                    value={formData.il}
                    onChange={handleInputChange}
                    className="mt-1 border-gray-300"
                  />
                </div>
                <div>
                  <Label htmlFor="ilce" className="text-black font-medium">İlçe</Label>
                  <Input
                    id="ilce"
                    name="ilce"
                    data-testid="input-ilce"
                    placeholder="Örn: Seyhan"
                    value={formData.ilce}
                    onChange={handleInputChange}
                    className="mt-1 border-gray-300"
                  />
                </div>
              </div>

              <div>
                <Label htmlFor="mahalle" className="text-black font-medium">Mahalle</Label>
                <Input
                  id="mahalle"
                  name="mahalle"
                  data-testid="input-mahalle"
                  placeholder="Örn: Köprülü"
                  value={formData.mahalle}
                  onChange={handleInputChange}
                  className="mt-1 border-gray-300"
                />
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <Label htmlFor="ada" className="text-black font-medium">Ada</Label>
                  <Input
                    id="ada"
                    name="ada"
                    data-testid="input-ada"
                    placeholder="Örn: 1234"
                    value={formData.ada}
                    onChange={handleInputChange}
                    className="mt-1 border-gray-300"
                  />
                </div>
                <div>
                  <Label htmlFor="parsel" className="text-black font-medium">Parsel</Label>
                  <Input
                    id="parsel"
                    name="parsel"
                    data-testid="input-parsel"
                    placeholder="Örn: 56"
                    value={formData.parsel}
                    onChange={handleInputChange}
                    className="mt-1 border-gray-300"
                  />
                </div>
              </div>

              <Button
                type="submit"
                data-testid="analyze-button"
                disabled={loading || remainingCredits === 0}
                className="w-full bg-black hover:bg-gray-800 text-white py-6 text-lg font-semibold rounded-md transition-colors"
              >
                {loading ? (
                  <>
                    <Loader2 className="mr-2 h-5 w-5 animate-spin" />
                    Analiz Yapılıyor...
                  </>
                ) : (
                  'Analiz Yap'
                )}
              </Button>
            </form>
          </CardContent>
        </Card>

        {/* Error Alert */}
        {error && (
          <Alert data-testid="error-alert" variant="destructive" className="mb-6">
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        )}

        {/* Analysis Result */}
        {analysis && (
          <Card data-testid="analysis-result-card" className="border-2 border-black shadow-lg">
            <CardHeader>
              <CardTitle className="text-2xl">Analiz Sonucu</CardTitle>
            </CardHeader>
            <CardContent>
              <div data-testid="analysis-content" className="prose prose-sm sm:prose max-w-none text-gray-800 whitespace-pre-wrap">
                {analysis}
              </div>
            </CardContent>
          </Card>
        )}
      </main>

      {/* Footer */}
      <footer className="border-t border-gray-200 mt-12 py-6">
        <div className="container mx-auto px-4 text-center text-gray-600 text-sm">
          © 2025 ArsaEkspertizAI - Yapay Zeka Destekli Arsa Analizi
        </div>
      </footer>
    </div>
  );
}

export default App;