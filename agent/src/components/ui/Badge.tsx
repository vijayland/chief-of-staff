type BadgeVariant = "default" | "blue" | "green" | "yellow" | "red" | "purple";

interface BadgeProps {
  children: React.ReactNode;
  variant?: BadgeVariant;
}

const variants: Record<BadgeVariant, string> = {
  default: "bg-surface-hover text-text-secondary",
  blue: "bg-accent-light text-accent",
  green: "bg-[#f0fdf4] text-success",
  yellow: "bg-[#fffbeb] text-warning",
  red: "bg-danger-light text-danger",
  purple: "bg-[#faf5ff] text-[#7c3aed]",
};

export function Badge({ children, variant = "default" }: BadgeProps) {
  return (
    <span
      className={`inline-flex items-center rounded-sm px-1.5 py-0.5 text-xs font-medium ${variants[variant]}`}
    >
      {children}
    </span>
  );
}
