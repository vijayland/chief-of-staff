interface AvatarProps {
  name: string;
  size?: "sm" | "md" | "lg";
}

const sizes = {
  sm: "w-6 h-6 text-[10px]",
  md: "w-8 h-8 text-xs",
  lg: "w-10 h-10 text-sm",
};

const colors = [
  "bg-[#dbeafe] text-[#2563eb]",
  "bg-[#dcfce7] text-[#16a34a]",
  "bg-[#fce7f3] text-[#db2777]",
  "bg-[#fef3c7] text-[#d97706]",
  "bg-[#ede9fe] text-[#7c3aed]",
  "bg-[#ffedd5] text-[#ea580c]",
];

function getColor(name: string) {
  const idx = name.charCodeAt(0) % colors.length;
  return colors[idx];
}

function getInitials(name: string) {
  return name
    .split(" ")
    .slice(0, 2)
    .map((w) => w[0])
    .join("")
    .toUpperCase();
}

export function Avatar({ name, size = "md" }: AvatarProps) {
  return (
    <div
      className={`
        ${sizes[size]} ${getColor(name)}
        rounded-full flex items-center justify-center font-semibold shrink-0
      `}
    >
      {getInitials(name)}
    </div>
  );
}
