import clsx from 'clsx';

type Variant =
  | 'threat_intelligence'
  | 'incident_runbook'
  | 'vulnerability_advisory'
  | 'low'
  | 'medium'
  | 'high'
  | 'critical'
  | 'success'
  | 'warning'
  | 'error'
  | 'info'
  | 'admin'
  | 'analyst';

const variantClasses: Record<Variant, string> = {
  threat_intelligence: 'bg-blue-900/40 text-blue-300 border border-blue-700',
  incident_runbook: 'bg-orange-900/40 text-orange-300 border border-orange-700',
  vulnerability_advisory: 'bg-purple-900/40 text-purple-300 border border-purple-700',
  low: 'bg-green-900/40 text-green-300 border border-green-700',
  medium: 'bg-yellow-900/40 text-yellow-300 border border-yellow-700',
  high: 'bg-red-900/40 text-red-300 border border-red-700',
  critical: 'bg-purple-900/40 text-purple-300 border border-purple-700',
  success: 'bg-green-900/40 text-green-300 border border-green-700',
  warning: 'bg-yellow-900/40 text-yellow-300 border border-yellow-700',
  error: 'bg-red-900/40 text-red-300 border border-red-700',
  info: 'bg-sky-900/40 text-sky-300 border border-sky-700',
  admin: 'bg-cyber-900/40 text-cyber-300 border border-cyber-700',
  analyst: 'bg-teal-900/40 text-teal-300 border border-teal-700',
};

const labelMap: Partial<Record<Variant, string>> = {
  threat_intelligence: 'Threat Intel',
  incident_runbook: 'Runbook',
  vulnerability_advisory: 'Vuln Advisory',
};

interface BadgeProps {
  variant: Variant;
  label?: string;
  className?: string;
}

const Badge: React.FC<BadgeProps> = ({ variant, label, className }) => {
  const displayLabel = label ?? labelMap[variant] ?? variant;
  return (
    <span
      className={clsx(
        'inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-semibold capitalize',
        variantClasses[variant],
        className
      )}
    >
      {displayLabel}
    </span>
  );
};

export default Badge;
