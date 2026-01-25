import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { Toaster } from 'react-hot-toast';

import { MobileCapture } from './pages/MobileCapture';
import { ShareTarget } from './pages/ShareTarget';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30000,
      retry: 1,
    },
  },
});

export function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter basename="/capture">
        <Routes>
          <Route path="/" element={<MobileCapture />} />
          <Route path="/share" element={<ShareTarget />} />
        </Routes>
        <Toaster 
          position="bottom-center"
          toastOptions={{
            style: {
              background: 'var(--color-bg-secondary)',
              color: 'var(--color-text-primary)',
              borderRadius: '12px',
            },
            success: {
              iconTheme: {
                primary: '#10b981',
                secondary: '#fff',
              },
            },
          }}
        />
      </BrowserRouter>
    </QueryClientProvider>
  );
}

export default App;
