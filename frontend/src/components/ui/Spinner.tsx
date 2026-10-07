import clsx from 'clsx';

interface SpinnerProps {
  size?: 'sm' | 'md' | 'lg';
  className?: string;
}

const sizes = {
  sm: 'h-4 w-4 border-2',
  md: 'h-8 w-8 border-4',
  lg: 'h-12 w-12 border-4',
};

const Spinner: React.FC<SpinnerProps> = ({ size = 'md', className }) => (
  <div
    className={clsx(
      'animate-spin rounded-full border-cyber-500 border-t-transparent',
      sizes[size],
      className
    )}
  />
);

export default Spinner;
