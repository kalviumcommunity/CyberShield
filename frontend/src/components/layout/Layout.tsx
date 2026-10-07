import Sidebar from './Sidebar';

interface LayoutProps {
  children: React.ReactNode;
}

const Layout: React.FC<LayoutProps> = ({ children }) => (
  <div className="flex h-screen overflow-hidden bg-slate-900">
    <Sidebar />
    <main className="flex-1 overflow-y-auto">
      <div className="min-h-full p-6 lg:p-8">{children}</div>
    </main>
  </div>
);

export default Layout;
