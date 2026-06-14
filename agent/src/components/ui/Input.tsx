"use client";

import { type InputHTMLAttributes, forwardRef } from "react";

interface InputProps extends InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  error?: string;
}

export const Input = forwardRef<HTMLInputElement, InputProps>(
  ({ label, error, className = "", ...props }, ref) => {
    return (
      <div className="flex flex-col gap-1">
        {label && (
          <label className="text-xs font-medium text-text-secondary uppercase tracking-wide">
            {label}
          </label>
        )}
        <input
          ref={ref}
          className={`
            h-8 w-full rounded-md border border-border bg-white
            px-3 text-sm text-text-primary placeholder:text-text-muted
            transition-colors duration-100
            hover:border-border-strong
            focus:outline-none focus:border-accent focus:ring-2 focus:ring-accent/20
            disabled:opacity-50 disabled:cursor-not-allowed disabled:bg-surface-sidebar
            ${error ? "border-danger focus:border-danger focus:ring-danger/20" : ""}
            ${className}
          `}
          {...props}
        />
        {error && <p className="text-xs text-danger">{error}</p>}
      </div>
    );
  },
);

Input.displayName = "Input";
