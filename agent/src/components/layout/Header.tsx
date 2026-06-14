interface HeaderProps {
  title: string;
  description?: string;
  actions?: React.ReactNode;
}

export function Header({ title, description, actions }: HeaderProps) {
  return (
    <div className="flex items-center justify-between px-6 py-4 border-b border-border shrink-0 bg-white">
      <div>
        <h1 className="text-lg font-bold text-text-primary tracking-tight">
          {title}
        </h1>
        {description && (
          <p className="text-xs text-text-muted mt-0.5 font-normal">
            {description}
          </p>
        )}
      </div>
      {actions && <div className="flex items-center gap-2">{actions}</div>}
    </div>
  );
}
