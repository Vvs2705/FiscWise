import { type ClassValue, clsx } from 'clsx'
import { twMerge } from 'tailwind-merge'

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

/**
 * Formats a string or number into BRL currency format (e.g. 1.500,00) as user types.
 */
export function formatCurrencyBRL(value: string | number | null | undefined): string {
  if (value === undefined || value === null || value === '') return '';
  
  // If it's a number, convert to fixed 2 decimals and clean it
  const cleanValue = typeof value === 'number'
    ? value.toFixed(2).replace(/\D/g, '')
    : value.toString().replace(/\D/g, '');
    
  if (!cleanValue) return '';
  
  const numberValue = parseFloat(cleanValue) / 100;
  return numberValue.toLocaleString('pt-BR', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
}

/**
 * Parses a BRL formatted currency string back into a float number.
 */
export function parseCurrencyBRL(value: string | number | null | undefined): number {
  if (value === undefined || value === null || value === '') return 0;
  if (typeof value === 'number') return value;
  
  // Remove thousand separator dots, then replace decimal separator comma with dot
  const clean = value.replace(/\./g, '').replace(',', '.');
  const parsed = parseFloat(clean);
  return isNaN(parsed) ? 0 : parsed;
}
