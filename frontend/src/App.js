import { useState, useEffect, useRef } from "react";
import { BrowserRouter, Routes, Route, useLocation, useNavigate, Navigate } from "react-router-dom";
import "@/App.css";
import axios from "axios";
import { Loader2, LogOut, CreditCard, ArrowLeft } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Toaster, toast } from "sonner";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

// Shopier product links with user info
const getShopierUrlWithUserInfo = (packageId, user) => {
  const baseUrls = {
    package_20: "https://shopier.com/39003278",
    package_50: "https://shopier.com/42901869",
    package_100: "https://shopier.com/42901899"
  };
  
  const url = baseUrls[packageId];
  if (!url || !user) return url;
  
  // Add user info as query parameters for better tracking
  const params = new URLSearchParams({
    buyer_name: user.name,
    buyer_email: user.email,
    user_id: user.user_id
  });
  
  return `${url}?${params.toString()}`;
};

function AuthCallback() {
  const navigate = useNavigate();
  const location = useLocation();
  const hasProcessed = useRef(false);

  useEffect(() => {
    // REMINDER: DO NOT HARDCODE THE URL, OR ADD ANY FALLBACKS OR REDIRECT URLS, THIS BREAKS THE AUTH
    if (hasProcessed.current) return;
    hasProcessed.current = true;

    const processSession = async () => {
      const hash = location.hash;
      const params = new URLSearchParams(hash.substring(1));
      const sessionId = params.get('session_id');

      if (!sessionId) {
        navigate('/');
        return;
      }

      try {
        const response = await axios.post(`${API}/auth/session`, 
          { session_id: sessionId },
          { withCredentials: true }
        );
        
        toast.success('Giriş başarılı!');
        navigate('/', { state: { user: response.data }, replace: true });
      } catch (error) {
        console.error('Auth error:', error);
        toast.error('Giriş yapılırken hata oluştu');
        navigate('/');
      }
    };

    processSession();
  }, [location, navigate]);

  return (
    <div className="min-h-screen bg-white flex items-center justify-center">
      <div className="text-center">
        <Loader2 className="h-12 w-12 animate-spin mx-auto mb-4 text-black" />
        <p className="text-gray-600">Giriş yapılıyor...</p>
      </div>
    </div>
  );
}

function Header({ user, remainingCredits, onLogin, onLogout }) {
  const navigate = useNavigate();
  
  return (
    <header className="border-b border-gray-200">
      <div className="container mx-auto px-4 py-4 flex items-center justify-between">
        <div className="flex items-center space-x-3 cursor-pointer" onClick={() => navigate('/')}>
          <img 
            src="https://customer-assets.emergentagent.com/job_ed4123bb-8167-4b92-b8f5-23b60fd1109e/artifacts/sedpsqd8_IMG_20260105_212426.jpg"
            alt="ArsaEkspertizAI Logo"
            className="h-8 w-8"
            data-testid="logo-image"
          />
          <div data-testid="logo" className="text-lg font-semibold text-black">
            ArsaEkspertizAI
          </div>
        </div>
        <div className="flex items-center space-x-2 sm:space-x-4">
          <div data-testid="credits-badge" className="bg-white text-black px-3 sm:px-4 py-2 rounded-full text-sm font-medium">
            {remainingCredits} Hak
          </div>
          {user ? (
            <div className="flex items-center space-x-2 sm:space-x-3">
              <span className="text-sm text-gray-600 hidden sm:inline">{user.name}</span>
              <Button
                variant="outline"
                size="sm"
                onClick={() => navigate('/paketler')}
                data-testid="packages-button"
                className="text-xs sm:text-sm"
              >
                <CreditCard className="h-3 w-3 sm:h-4 sm:w-4 mr-1 sm:mr-2" />
                Paketler
              </Button>
              <Button
                variant="outline"
                size="sm"
                onClick={onLogout}
                data-testid="logout-button"
              >
                <LogOut className="h-4 w-4" />
              </Button>
            </div>
          ) : (
            <Button
              onClick={onLogin}
              data-testid="login-button"
              className="bg-black hover:bg-gray-800 text-white"
            >
              Giriş Yap
            </Button>
          )}
        </div>
      </div>
    </header>
  );
}

function MainApp() {
  const location = useLocation();
  const navigate = useNavigate();
  const [user, setUser] = useState(location.state?.user || null);
  const [isAuthenticated, setIsAuthenticated] = useState(location.state?.user ? true : null);
  const [formData, setFormData] = useState({
    il: "",
    ilce: "",
    mahalle: "",
    ada: "",
    parsel: ""
  });
  
  const [remainingCredits, setRemainingCredits] = useState(5);
  const [analysis, setAnalysis] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (location.state?.user) return;

    const checkAuth = async () => {
      try {
        const response = await axios.get(`${API}/auth/me`, {
          withCredentials: true
        });
        setUser(response.data);
        setIsAuthenticated(true);
      } catch (error) {
        setIsAuthenticated(false);
      }
    };

    checkAuth();
  }, [location.state]);

  useEffect(() => {
    fetchCredits();
  }, [user]);

  const fetchCredits = async () => {
    try {
      const response = await axios.get(`${API}/credits`, {
        withCredentials: true
      });
      setRemainingCredits(response.data.remaining_credits);
    } catch (err) {
      console.error('Error fetching credits:', err);
    }
  };

  const handleLogin = () => {
    // REMINDER: DO NOT HARDCODE THE URL, OR ADD ANY FALLBACKS OR REDIRECT URLS, THIS BREAKS THE AUTH
    const redirectUrl = window.location.origin;
    window.location.href = `https://auth.emergentagent.com/?redirect=${encodeURIComponent(redirectUrl)}`;
  };

  const handleLogout = async () => {
    try {
      await axios.post(`${API}/auth/logout`, {}, { withCredentials: true });
      setUser(null);
      setIsAuthenticated(false);
      toast.success('Çıkış yapıldı');
      navigate('/');
    } catch (err) {
      console.error('Logout error:', err);
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
      const response = await axios.post(`${API}/analyze-property`, formData, {
        withCredentials: true
      });

      setAnalysis(response.data.analysis);
      setRemainingCredits(response.data.remaining_credits);
      toast.success('Analiz tamamlandı!');
    } catch (err) {
      const errorMsg = err.response?.data?.detail || 'Analiz yapılırken bir hata oluştu';
      setError(errorMsg);
      toast.error(errorMsg);
      
      if (err.response?.status === 403) {
        if (user) {
          navigate('/paketler');
        } else {
          toast.info('Giriş yaparak +5 hak daha kazanın!');
        }
      }
    } finally {
      setLoading(false);
    }
  };

  if (isAuthenticated === null) {
    return (
      <div className="min-h-screen bg-white flex items-center justify-center">
        <Loader2 className="h-12 w-12 animate-spin text-black" />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-white flex flex-col">
      <Toaster position="top-center" />
      
      <Header 
        user={user} 
        remainingCredits={remainingCredits} 
        onLogin={handleLogin} 
        onLogout={handleLogout} 
      />

      {/* Main Content */}
      <main className="flex-1 container mx-auto px-4 py-8 max-w-4xl">
        {!user && remainingCredits <= 3 && remainingCredits > 0 && (
          <Alert className="mb-6 border-black">
            <AlertDescription>
              <strong>İpucu:</strong> Giriş yaparak +5 hak daha kazanabilirsiniz!
            </AlertDescription>
          </Alert>
        )}

        <div className="mb-8 text-center">
          <h1 className="text-4xl sm:text-5xl font-bold text-black mb-3">
            Yapay Zeka Arsa Analizi
          </h1>
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
                className="w-full bg-black hover:bg-gray-800 text-white py-6 text-lg font-semibold rounded-md"
              >
                {loading ? (
                  <>
                    <Loader2 className="mr-2 h-5 w-5 animate-spin" />
                    Analiz Yapılıyor...
                  </>
                ) : remainingCredits === 0 ? (
                  user ? 'Krediniz Bitti - Paketlere Git' : 'Giriş Yapın'
                ) : (
                  'Analiz Yap'
                )}
              </Button>
              
              {remainingCredits === 0 && user && (
                <Button
                  type="button"
                  variant="outline"
                  onClick={() => navigate('/paketler')}
                  className="w-full border-black text-black hover:bg-gray-100"
                >
                  <CreditCard className="mr-2 h-5 w-5" />
                  Kredi Paketlerini Görüntüle
                </Button>
              )}
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
              <div data-testid="analysis-content" className="text-gray-800 whitespace-pre-wrap leading-relaxed">
                {analysis}
              </div>
            </CardContent>
          </Card>
        )}
      </main>

      {/* Footer */}
      <footer className="border-t border-gray-200 py-6 mt-auto">
        <div className="container mx-auto px-4 text-center text-gray-600 text-sm">
          © 2025 ArsaEkspertizAI - Yapay Zeka Destekli Arsa Analizi
        </div>
      </footer>
    </div>
  );
}

function PackagesPage() {
  const navigate = useNavigate();
  const [user, setUser] = useState(null);
  const [packages, setPackages] = useState([]);
  const [loading, setLoading] = useState(true);
  const [remainingCredits, setRemainingCredits] = useState(0);
  const [showPaymentModal, setShowPaymentModal] = useState(false);
  const [selectedPackage, setSelectedPackage] = useState(null);
  const [checkingPayment, setCheckingPayment] = useState(false);

  useEffect(() => {
    checkAuthAndFetch();
  }, []);

  const checkAuthAndFetch = async () => {
    try {
      const userResponse = await axios.get(`${API}/auth/me`, {
        withCredentials: true
      });
      setUser(userResponse.data);
      
      const [packagesRes, creditsRes] = await Promise.all([
        axios.get(`${API}/payment/packages`),
        axios.get(`${API}/credits`, { withCredentials: true })
      ]);
      
      setPackages(packagesRes.data);
      setRemainingCredits(creditsRes.data.remaining_credits);
    } catch (error) {
      console.error('Auth error:', error);
      toast.error('Lütfen giriş yapın');
      navigate('/');
    } finally {
      setLoading(false);
    }
  };

  const handleLogout = async () => {
    try {
      await axios.post(`${API}/auth/logout`, {}, { withCredentials: true });
      toast.success('Çıkış yapıldı');
      navigate('/');
    } catch (err) {
      console.error('Logout error:', err);
    }
  };

  const handlePurchase = (pkg) => {
    setSelectedPackage(pkg);
    setShowPaymentModal(true);
    // Open Shopier in new tab
    const shopierUrl = getShopierUrlWithUserInfo(pkg.id, user);
    window.open(shopierUrl, '_blank');
  };

  const checkPaymentStatus = async () => {
    setCheckingPayment(true);
    try {
      // Refresh credits
      const response = await axios.get(`${API}/credits`, { withCredentials: true });
      const newCredits = response.data.remaining_credits;
      
      if (newCredits > remainingCredits) {
        toast.success('Ödemeniz alındı! Kredileriniz yüklendi.');
        setRemainingCredits(newCredits);
        setShowPaymentModal(false);
        setSelectedPackage(null);
      } else {
        toast.info('Ödeme henüz işlenmedi. Lütfen bekleyin...');
      }
    } catch (err) {
      toast.error('Kredi kontrol edilirken hata oluştu');
    } finally {
      setCheckingPayment(false);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-white flex items-center justify-center">
        <Loader2 className="h-12 w-12 animate-spin text-black" />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-white flex flex-col">
      <Toaster position="top-center" />
      
      <Header 
        user={user} 
        remainingCredits={remainingCredits} 
        onLogin={() => {}} 
        onLogout={handleLogout} 
      />

      <main className="flex-1 container mx-auto px-4 py-8 max-w-6xl">
        <div className="mb-8">
          <Button
            variant="ghost"
            onClick={() => navigate('/')}
            className="mb-4"
            data-testid="back-button"
          >
            <ArrowLeft className="h-4 w-4 mr-2" />
            Ana Sayfaya Dön
          </Button>
          
          <div className="text-center">
            <h1 className="text-4xl sm:text-5xl font-bold text-black mb-3">
              Kredi Paketleri
            </h1>
            <p className="text-base sm:text-lg text-gray-600">
              Size uygun paketi seçin ve analizlerinize devam edin
            </p>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {packages.map((pkg) => (
            <Card 
              key={pkg.id} 
              className={`border-2 ${pkg.popular ? 'border-black scale-105' : 'border-gray-200'} hover:shadow-xl transition-all`}
              data-testid={`package-${pkg.id}`}
            >
              <CardHeader>
                {pkg.popular && (
                  <div className="text-xs font-semibold bg-black text-white px-3 py-1 rounded-full w-fit mb-2">
                    EN POPÜLER
                  </div>
                )}
                <CardTitle className="text-2xl">{pkg.name}</CardTitle>
                <CardDescription className="text-base">{pkg.description}</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="text-4xl font-bold text-black">
                  {pkg.price} TL
                </div>
                <div className="text-sm text-gray-600">
                  {pkg.credits} analiz hakkı
                </div>
                <Button 
                  onClick={() => handlePurchase(pkg)}
                  className="w-full bg-black hover:bg-gray-800 text-white py-6 text-base"
                  data-testid={`buy-${pkg.id}`}
                >
                  <CreditCard className="mr-2 h-5 w-5" />
                  Satın Al
                </Button>
              </CardContent>
            </Card>
          ))}
        </div>

        {/* Payment Modal */}
        {showPaymentModal && selectedPackage && (
          <div className="fixed inset-0 bg-black bg-opacity-50 z-50 flex items-center justify-center p-4">
            <div className="bg-white rounded-lg max-w-lg w-full p-6">
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-2xl font-bold">Ödeme İşlemi</h2>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => {
                    setShowPaymentModal(false);
                    setSelectedPackage(null);
                  }}
                >
                  ✕
                </Button>
              </div>
              
              <div className="space-y-4 mb-6">
                <div className="bg-gray-50 p-4 rounded-lg">
                  <p className="text-sm text-gray-600 mb-2">Seçilen Paket:</p>
                  <p className="text-xl font-bold">{selectedPackage.name}</p>
                  <p className="text-2xl font-bold text-black mt-2">{selectedPackage.price} TL</p>
                  <p className="text-sm text-gray-600 mt-1">{selectedPackage.credits} analiz hakkı</p>
                </div>
                
                <div className="bg-blue-50 border border-blue-200 p-4 rounded-lg">
                  <p className="text-sm text-blue-800">
                    ✓ Shopier ödeme sayfası yeni sekmede açıldı
                  </p>
                  <p className="text-sm text-blue-800 mt-2">
                    ✓ Ödemenizi tamamladıktan sonra kredileriniz otomatik olarak hesabınıza yüklenecektir
                  </p>
                </div>
              </div>
              
              <div className="space-y-3">
                <Button
                  onClick={checkPaymentStatus}
                  disabled={checkingPayment}
                  className="w-full bg-black hover:bg-gray-800 text-white py-6"
                  data-testid="check-payment-button"
                >
                  {checkingPayment ? (
                    <>
                      <Loader2 className="mr-2 h-5 w-5 animate-spin" />
                      Kontrol Ediliyor...
                    </>
                  ) : (
                    'Ödemeyi Tamamladım - Kredileri Kontrol Et'
                  )}
                </Button>
                
                <Button
                  variant="outline"
                  onClick={() => {
                    const shopierUrl = getShopierUrlWithUserInfo(selectedPackage.id, user);
                    window.open(shopierUrl, '_blank');
                  }}
                  className="w-full"
                >
                  Ödeme Sayfasını Tekrar Aç
                </Button>
              </div>
            </div>
          </div>
        )}

        <div className="mt-12 text-center text-gray-600 text-sm">\n          <p>Ödeme sonrası kredileriniz otomatik olarak hesabınıza yüklenecektir.</p>
        </div>
      </main>

      <footer className="border-t border-gray-200 py-6 mt-auto">
        <div className="container mx-auto px-4 text-center text-gray-600 text-sm">
          © 2025 ArsaEkspertizAI - Yapay Zeka Destekli Arsa Analizi
        </div>
      </footer>
    </div>
  );
}

function AppRouter() {
  const location = useLocation();
  
  // Check for session_id in URL hash (synchronous during render)
  if (location.hash?.includes('session_id=')) {
    return <AuthCallback />;
  }
  
  return (
    <Routes>
      <Route path="/" element={<MainApp />} />
      <Route path="/paketler" element={<PackagesPage />} />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}

function App() {
  return (
    <BrowserRouter>
      <AppRouter />
    </BrowserRouter>
  );
}

export default App;