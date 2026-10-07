import { Link, NavLink, useNavigate } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import {
  Shield,
  LayoutDashboard,
  ShieldAlert,
  Search,
  FileText,
  Upload,
  LogOut,
  User,
} from 'lucide-react';
import clsx from 'clsx';

const navItems = [
  { to: '/dashboard', label: 'Dashboard', icon: LayoutDashboard },
  { to: '/mitigation', label: 'Mitigation', icon: ShieldAlert },
  { to: '/search', label: 'Semantic Search', icon: Search },
  { to: '/documents', label: 'Documents', icon: FileText },
];

const adminItems = [
  { to: '/documents/upload', label: 'Upload Doc', icon: Upload },
];

const Sidebar: React.FC = () => {
  const { user, isAdmin, logout } = useAuth();
  const navigate = useNavigate();

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  return (
    <aside className="flex h-screen w-64 flex-col border-r border-slate-800 bg-slate-950">
      {/* Logo */}
      <div className="flex items-center gap-3 border-b border-slate-800 px-6 py-5">
        <Shield className="h-8 w-8 text-cyber-400" />
        <div>
          <p className="font-bold text-white leading-none">CyberShield</p>
          <p className="text-xs text-slate-400 mt-0.5">Threat Intelligence</p>
        </div>
      </div>

      {/* Nav */}
      <nav className="flex-1 overflow-y-auto px-3 py-4 space-y-1">
        <p className="mb-2 px-3 text-xs font-semibold uppercase tracking-wider text-slate-500">
          Main
        </p>
        {navItems.map(({ to, label, icon: Icon }) => (
          <NavLink
            key={to}
            to={to}
            className={({ isActive }) =>
              clsx(
                'flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-colors',
                isActive
                  ? 'bg-cyber-600/20 text-cyber-300 border border-cyber-700/50'
                  : 'text-slate-400 hover:bg-slate-800 hover:text-white'
              )
            }
          >
            <Icon className="h-4 w-4 shrink-0" />
            {label}
          </NavLink>
        ))}

        {isAdmin && (
          <>
            <p className="mb-2 mt-6 px-3 text-xs font-semibold uppercase tracking-wider text-slate-500">
              Admin
            </p>
            {adminItems.map(({ to, label, icon: Icon }) => (
              <NavLink
                key={to}
                to={to}
                className={({ isActive }) =>
                  clsx(
                    'flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-colors',
                    isActive
                      ? 'bg-cyber-600/20 text-cyber-300 border border-cyber-700/50'
                      : 'text-slate-400 hover:bg-slate-800 hover:text-white'
                  )
                }
              >
                <Icon className="h-4 w-4 shrink-0" />
                {label}
              </NavLink>
            ))}
          </>
        )}
      </nav>

      {/* User Info */}
      <div className="border-t border-slate-800 px-3 py-3 space-y-1">
        <Link
          to="/profile"
          className="flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm text-slate-400 hover:bg-slate-800 hover:text-white transition-colors"
        >
          <User className="h-4 w-4 shrink-0" />
          <div className="flex-1 min-w-0">
            <p className="truncate font-medium text-slate-300">{user?.name}</p>
            <p className="truncate text-xs text-slate-500 capitalize">{user?.role}</p>
          </div>
        </Link>
        <button
          onClick={handleLogout}
          className="flex w-full items-center gap-3 rounded-lg px-3 py-2.5 text-sm text-slate-400 hover:bg-red-900/30 hover:text-red-300 transition-colors"
        >
          <LogOut className="h-4 w-4 shrink-0" />
          Log out
        </button>
      </div>
    </aside>
  );
};

export default Sidebar;
